from fastapi import FastAPI, Request, Depends, HTTPException
import os
import httpx
from dotenv import load_dotenv
import json
from openai import OpenAI
from sqlalchemy.exc import SQLAlchemyError
from database import engine, Base, SessionLocal
from sqlalchemy.orm import Session
from models import User, Message
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("uvicorn")

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY")
HANDOFF_PHRASE = os.getenv("HANDOFF_PHRASE", "Позвольте мне передать ваш вопрос нашему специалисту. Ожидайте, пожалуйста.")

# OpenAI Client
openai_client = OpenAI(api_key=OPENAI_API_KEY)
nebius_client = OpenAI(
    base_url="https://api.studio.nebius.com/v1/",
    api_key=NEBIUS_API_KEY
)

# FastAPI App
app = FastAPI()
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

def load_company_policy(company_id: str = "test"):
    """Загрузка политики компании из JSON файла."""
    policy_path = f"policies/{company_id}_policy.json"
    try:
        with open(policy_path, "r", encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.info(f"Ошибка: Файл политики для '{company_id}' не найден.")
        return {
            "company": "Default",
            "allowed_topics": [],
            "restricted_topics": [],
            "handoff_trigger": []
        }

def build_prompt(script_profile: dict, user_message: str, history: list = None, user_settings: dict = None, user_data: User = None):
    """Создание промпта для ChatGPT с учетом истории и настроек пользователя."""
    preferred_language = user_settings.get("preferred_language", "ru")
    company_info = script_profile.get('company_info', {})

    system_prompt = f"""
Ты — виртуальный помощник компании {script_profile.get('company', 'неизвестно')}.
Твой текущий язык общения: {preferred_language}.

ВАЖНАЯ ИНФОРМАЦИЯ О КОМПАНИИ:
- Название: {script_profile.get('company')}
- Адрес: {company_info.get('адрес')}
- Телефон: {company_info.get('телефон')}
- Сайт: {company_info.get('сайт')}
- Описание: {company_info.get('описание')}

При вопросах о местоположении или контактах ВСЕГДА используй ТОЛЬКО эту информацию.

Отвечай строго в рамках следующих политик:
- Разрешённые темы: {script_profile.get('allowed_topics', [])}
- Запрещённые темы: {script_profile.get('restricted_topics', [])}

{f'Информация о клиенте:\n- Постоянный клиент: {user_data.is_постоянный_клиент}\n- Доступные акции: {user_data.доступные_акции}\n- Персональная скидка: {user_data.персональная_скидка}%' if user_data else ''}

Учитывай историю предыдущего общения с пользователем для поддержания контекста.

Если вопрос клиента выходит за рамки или тебе не хватает данных — отвечай на языке {preferred_language}:
{HANDOFF_PHRASE}

Всегда отвечай уважительно, коротко и полезно на языке {preferred_language}.
"""
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for msg in history:
            role = "user" if msg.user_id == history[0].user_id else "assistant"
            messages.append({"role": role, "content": msg.text})
    messages.append({"role": "user", "content": user_message})
    return messages


def should_handoff(reply: str, handoff_triggers: list = None):
    """Проверка, нужно ли передавать оператору."""
    if handoff_triggers is None:
        handoff_triggers = [
            "не уверена", 
            "не знаю", 
            "не могу ответить",
            HANDOFF_PHRASE.lower()
        ]
    reply_lower = reply.lower()
    for trigger in handoff_triggers:
        if trigger.lower() in reply_lower:
            logger.info(f"Найден триггер для передачи оператору: {trigger}")
            return True
    return False

async def send_telegram_message(chat_id: int, text: str):
    """Отправка сообщения в Telegram."""
    async with httpx.AsyncClient() as client:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            response = await client.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"
            })
            response.raise_for_status()
            logger.info(f"Сообщение отправлено в чат {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки в Telegram: {e}")
            raise

async def notify_admin(admin_id: str, user_info: dict, user_message: str, script_profile: dict):
    """Отправка уведомления администратору о проблеме пользователя."""
    try:
        user_username = user_info.get('username', 'Нет username')
        user_id = user_info['id']
        first_name = user_info.get('first_name', 'Нет имени')
        
        admin_message = (
            f"❗️ Требуется ваше внимание!\n\n"
            f"Пользователь: {first_name}\n"
            f"Username: @{user_username}\n"
            f"ID: {user_id}\n\n"
            f"Сообщение: {user_message}"
        )
        
        logger.info(f"Попытка отправки уведомления админу {admin_id}")
        await send_telegram_message(int(admin_id), admin_message)
        logger.info(f"Уведомление успешно отправлено админу {admin_id}")
    except ValueError as e:
        logger.error(f"Неверный формат ID администратора: {admin_id}")
        raise
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления админу: {str(e)}")
        raise

async def generate_ai_response(prompt: list, client: OpenAI = openai_client) -> tuple[str, str]:
    """Генерация ответа с использованием AI API с указанием использованного сервиса."""
    try:
        if client == nebius_client:
            # Специальная обработка для Nebius
            response = client.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-70B-Instruct",
                messages=prompt,
                max_tokens=150,
                temperature=0.7,
            )
        else:
            # Стандартная обработка для OpenAI
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=prompt,
                max_tokens=150,
                temperature=0.7
            )
        return response.choices[0].message.content, "OpenAI" if client == openai_client else "Nebius"
    except Exception as e:
        logger.info(f"Ошибка AI API ({client.base_url}): {str(e)}")
        raise

@app.post(f"/webhook/{TELEGRAM_BOT_TOKEN}")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Webhook endpoint для обработки обновлений от Telegram."""
    try:
        update_data = await request.json()
        logger.info(f"Получены данные webhook: {update_data}")
        
        if 'message' in update_data:
            user_message = update_data['message']['text']
            chat_id = update_data['message']['chat']['id']
            user_info = update_data['message']['chat']
            
            # Загрузка политики компании
            script_profile = load_company_policy("test")
            logger.info(f"Загружена политика компании: {script_profile}")

        try:
            # Создание или получение пользователя
            user = db.query(User).filter(User.id == chat_id).first()
            if not user:
                user = User(id=chat_id, settings={})
                db.add(user)
                db.commit()
                db.refresh(user)

            # Сохранение сообщения пользователя
            db_message = Message(user_id=user.id, text=user_message)
            db.add(db_message)
            db.commit()
            db.refresh(db_message)
        except SQLAlchemyError as e:
            logger.error(f"Database error: {str(e)}")
            db.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            db.rollback()
            raise

        if user_message.startswith('/my_id'):
            user_info_message = (
                f"Ваш Telegram ID: {chat_id}\n"
                f"Имя: {user_info.get('first_name', 'Не указано')}\n"
                f"Username: @{user_info.get('username', 'Не указан')}"
            )
            await send_telegram_message(chat_id, user_info_message)
            return {"status": "ok"}

        # Создание или получение пользователя
        user = db.query(User).filter(User.id == chat_id).first()
        # Обработка команды /setlang
        if user_message.startswith("/setlang"):
            parts = user_message.split()
            if len(parts) == 2:
                lang_code = parts[1].lower()
                update_user_settings(db, user.id, {"preferred_language": lang_code})
                await send_telegram_message(chat_id, f"Язык общения изменен на {lang_code}.")
                return {"status": "ok"}

        # Получение истории сообщений
        history = db.query(Message).filter(
            Message.user_id == user.id
        ).order_by(Message.timestamp).all()

        # Получение настроек пользователя
        user_settings = get_user_settings(db, user.id)

        try:
            # Построение промпта
            prompt = build_prompt(script_profile, user_message, history, user_settings, user)
            
            # Попытка использовать OpenAI, затем Nebius как fallback
            reply = None
            service_used = None

            try:
                # Сначала пробуем OpenAI
                reply, service_used = await generate_ai_response(prompt)
            except Exception as openai_error:
                logger.info(f"OpenAI недоступен, переключаемся на Nebius: {openai_error}")
                try:
                    # Пробуем Nebius как fallback
                    reply, service_used = await generate_ai_response(prompt, nebius_client)
                except Exception as nebius_error:
                    logger.info(f"Nebius тоже недоступен: {nebius_error}")
                    reply = "Извините, сервис временно недоступен. Попробуйте позже."
                    service_used = "None"

            # Добавляем информацию об использованном сервисе
            reply_with_service = f"{reply}\n\n[Использован: {service_used}]"

            # Проверка необходимости передачи оператору
            handoff_phrase = os.getenv("HANDOFF_PHRASE", "Позвольте мне передать ваш вопрос нашему специалисту")
            logger.info(f"Проверка необходимости передачи оператору. Ответ: {reply}")
            logger.info(f"Handoff phrase: {handoff_phrase}")
            
            if handoff_phrase.lower() in reply.lower():
                logger.info("Обнаружена фраза для передачи оператору")
                admin_settings = script_profile.get("admin_settings", {})
                admin_id = admin_settings.get("admin_id")
                notifications_enabled = admin_settings.get("notifications_enabled", False)
                
                logger.info(f"Настройки админа: ID={admin_id}, notifications_enabled={notifications_enabled}")
                
                if not admin_id or not notifications_enabled:
                    logger.error(f"Неверные настройки админа: {admin_settings}")
                    await send_telegram_message(chat_id, "Извините, не удалось связаться с оператором. Попробуйте позже.")
                    return {"status": "handoff_failed", "reason": "invalid_admin_settings"}

                try:
                    # Отправляем уведомление админу до ответа пользователю
                    await notify_admin(admin_id, user_info, user_message, script_profile)
                    logger.info("Уведомление админу отправлено успешно")
                    
                    # Отправляем ответ пользователю
                    await send_telegram_message(chat_id, reply_with_service)
                    return {"status": "handoff_required"}
                except Exception as notify_error:
                    logger.error(f"Ошибка при уведомлении админа: {notify_error}")
                    # Даже если не удалось уведомить админа, отправляем ответ пользователю
                    await send_telegram_message(chat_id, reply_with_service)
                    return {"status": "handoff_failed", "reason": "notification_error"}
            else:
                # Если не требуется передача оператору, просто отправляем ответ
                await send_telegram_message(chat_id, reply_with_service)
                return {"status": "ok", "service_used": service_used}

        except Exception as processing_error:
            logger.error(f"Ошибка обработки сообщения: {processing_error}")
            await send_telegram_message(chat_id, "Произошла ошибка при обработке вашего сообщения.")
            return {"status": "error", "error": str(processing_error)}

    except Exception as e:
        logger.error(f"Критическая ошибка в webhook: {e}")
        return {"status": "critical_error", "error": str(e)}

def get_user_settings(db: Session, user_id: int) -> dict:
    """Получение настроек пользователя из базы данных."""
    user = db.query(User).filter(User.id == user_id).first()
    return user.settings if user and user.settings else {}

def update_user_settings(db: Session, user_id: int, settings: dict):
    """Обновление настроек пользователя в базе данных."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.settings = settings
        db.commit()
        db.refresh(user)
    return user.settings if user else {}