from fastapi import FastAPI, Request, Depends, HTTPException
import os
import httpx
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy.exc import SQLAlchemyError
from database import SessionLocal
from sqlalchemy.orm import Session
from models import User, Message, Company
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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

def load_company_policy(company_id: int = 1):
    """Загрузка политики компании с валидацией и дефолтными значениями."""
    try:
        db = SessionLocal()
        company = db.query(Company).filter(Company.id == company_id).first()
        
        if not company:
            logger.warning(f"Компания с ID {company_id} не найдена.")
            default_policy = _get_default_policy()
            return default_policy
        
        policy = company.policy or {}
        
        # Валидация и дополнение политики значениями по умолчанию
        validated_policy = {
            "company": company.name,
            "allowed_topics": policy.get("allowed_topics", ["support"]),
            "restricted_topics": policy.get("restricted_topics", ["confidential"]),
            "handoff_trigger": policy.get("handoff_trigger", ["help"]),
            "admin_settings": {**{
                "admin_id": None,
                "notifications_enabled": False
            }, **policy.get("admin_settings", {})},
            "company_info": {
                "описание": company.description or "",
                "адрес": "",
                "телефон": "",
                "сайт": company.website or ""
            }
        }
        
        return validated_policy
    
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при загрузке политики: {e}")
        return (f"Ошибка при загрузке политики: {e}")
    finally:
        db.close()

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
            "не уверен", 
            "помощь",
            "оператор",
            "специалист",
            "не могу помочь",
            "консультация",
            "помощь оператора",
            HANDOFF_PHRASE.lower()
        ]
    
    reply_lower = reply.lower()
    
    # Проверка точных вхождений
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

async def generate_ai_response(
    prompt: list, 
    script_profile: dict = None, 
    user_message: str = None, 
    client: OpenAI = openai_client
) -> tuple[str, str]:
    """
    Генерация ответа с использованием AI API с указанием использованного сервиса.
    
    Args:
        prompt (list): Список сообщений для генерации ответа
        script_profile (dict, optional): Профиль компании
        user_message (str, optional): Исходное сообщение пользователя
        client (OpenAI, optional): Клиент для генерации ответа. По умолчанию OpenAI.
    
    Returns:
        tuple[str, str]: Кортеж с ответом и использованным сервисом
    """
    # Проверка на тестовый режим
    if os.getenv('TESTING', 'false').lower() == 'true':
        return "Mocked AI Response", "OpenAI"

    try:
        # Попытка использования указанного клиента
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=prompt,
                max_tokens=150,
                temperature=0.7
            )
            service_used = "OpenAI"
        except Exception as openai_error:
            logger.info(f"OpenAI недоступен: {openai_error}")
            
            # Fallback на Nebius
            response = nebius_client.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-70B-Instruct",
                messages=prompt,
                max_tokens=150,
                temperature=0.7,
            )
            service_used = "Nebius"
        
        # Извлекаем текст ответа
        reply = response.choices[0].message.content.strip()
        
        return reply, service_used
    
    except Exception as e:
        logger.error(f"Ошибка при генерации ответа: {e}")
        return "Извините, сервис временно недоступен. Попробуйте позже.", "None"

@app.post("/webhook/{company_token}")
async def webhook(request: Request, company_token: str, db: Session = Depends(get_db)):
    try:
        # Находим компанию по токену
        company = db.query(Company).filter(Company.telegram_token == company_token).first()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Проверяем, что компания активна
        if not company.is_active:
            raise HTTPException(status_code=403, detail="Company is not active")
        
        # Получаем данные от Telegram
        user_data = await request.json()
        user_info = user_data.get('message', {}).get('from', {})
        chat_id = user_info.get('id')
        user_message = user_data.get('message', {}).get('text', '')
        
        # Находим или создаем пользователя для этой компании
        user = db.query(User).filter(
            User.telegram_id == chat_id, 
            User.company_id == company.id
        ).first()
        
        if not user:
            user = User(
                telegram_id=chat_id, 
                company_id=company.id, 
                username=user_info.get('username'),
                settings={},
                is_постоянный_клиент=False,
                доступные_акции=[],
                персональная_скидка=0.0
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Используем политику компании
        script_profile = load_company_policy(company.id)
        
        if user_message.startswith('/my_id'):
            user_info_message = (
                f"Ваш Telegram ID: {chat_id}\n"
                f"Имя: {user_info.get('first_name', 'Не указано')}\n"
                f"Username: @{user_info.get('username', 'Не указан')}"
            )
            await send_telegram_message(chat_id, user_info_message)
            return {"status": "ok"}

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
            reply = None
            service_used = None

            reply, service_used = await generate_ai_response(prompt)

            # Добавляем информацию об использованном сервисе
            reply_with_service = f"{reply}\n\n[Использован: {service_used}]"

            # Проверка необходимости передачи оператору
            handoff_phrase = os.getenv("HANDOFF_PHRASE", "Позвольте мне передать ваш вопрос нашему специалисту")
            logger.info(f"Проверка необходимости передачи оператору. Ответ: {reply}")
            logger.info(f"Handoff phrase: {handoff_phrase}")
            
            if should_handoff(reply, script_profile.get("handoff_trigger", [])):
                logger.info("Обнаружена необходимость передачи оператору")
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