from fastapi import FastAPI, Request, Depends, HTTPException
import os
import httpx
from dotenv import load_dotenv
import json
from openai import OpenAI
from database import engine, Base, SessionLocal
from sqlalchemy.orm import Session
from models import User, Message
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# OpenAI Client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

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
        print(f"Ошибка: Файл политики для '{company_id}' не найден.")
        return {
            "company": "Default",
            "allowed_topics": [],
            "restricted_topics": [],
            "handoff_trigger": []
        }

def build_prompt(script_profile: dict, user_message: str, history: list = None, user_settings: dict = None, user_data: User = None):
    """Создание промпта для ChatGPT с учетом истории и настроек пользователя."""
    preferred_language = user_settings.get("preferred_language", "ru")

    system_prompt = f"""
Ты — виртуальный помощник компании {script_profile.get('company', 'неизвестно')}.
Твой текущий язык общения: {preferred_language}.
Отвечай строго в рамках следующих политик:
- Разрешённые темы: {script_profile.get('allowed_topics', [])}
- Запрещённые темы: {script_profile.get('restricted_topics', [])}

{f'Информация о клиенте:\n- Постоянный клиент: {user_data.is_постоянный_клиент}\n- Доступные акции: {user_data.доступные_акции}\n- Персональная скидка: {user_data.персональная_скидка}%' if user_data else ''}

Учитывай историю предыдущего общения с пользователем для поддержания контекста.

Если вопрос клиента выходит за рамки или тебе не хватает данных — отвечай на языке {preferred_language}:
"Позвольте мне передать ваш вопрос нашему специалисту. Ожидайте, пожалуйста."

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
        handoff_triggers = ["не уверена", "не знаю", "не могу ответить"]
    reply_lower = reply.lower()
    for trigger in handoff_triggers:
        if trigger.lower() in reply.lower():
            return True
    return False

@app.post("/users/{user_id}/settings")
async def set_user_settings(user_id: int, settings: dict, db: Session = Depends(get_db)):
    """Установка настроек пользователя."""
    updated_settings = update_user_settings(db, user_id, settings)
    if updated_settings:
        return {"user_id": user_id, "settings": updated_settings}
    else:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")

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

async def send_telegram_message(chat_id: int, text: str):
    """Отправка сообщения в Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json={
                "chat_id": chat_id,
                "text": text
            })
            response.raise_for_status()
        except Exception as e:
            print(f"Ошибка отправки в Telegram: {e}")

@app.post(f"/webhook/{TELEGRAM_BOT_TOKEN}")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Webhook endpoint для обработки обновлений от Telegram с расширенной обработкой."""
    try:
        update_data = await request.json()
        if 'message' in update_data:
            user_message = update_data['message']['text']
            chat_id = update_data['message']['chat']['id']

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

            # Загрузка политики компании
            script_profile = load_company_policy()

            try:
                # Построение промпта
                prompt = build_prompt(script_profile, user_message, history, user_settings, user)
                
                # Вызов OpenAI API с обработкой ошибок
                try:
                    response = openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=prompt,
                        max_tokens=150,  # Ограничение длины ответа
                        temperature=0.7  # Управление креативностью
                    )
                    reply = response.choices[0].message.content
                except Exception as api_error:
                    print(f"Ошибка OpenAI API: {api_error}")
                    reply = "Извините, возникла проблема при генерации ответа. Попробуйте позже."

                # Проверка необходимости передачи оператору
                if should_handoff(reply, script_profile.get("handoff_trigger", [])):
                    # Логика передачи оператору
                    await send_telegram_message(chat_id, "Требуется помощь оператора.")
                    return {"status": "handoff_required"}

                # Отправка ответа пользователю
                await send_telegram_message(chat_id, reply)
                return {"status": "ok"}

            except Exception as processing_error:
                print(f"Ошибка обработки сообщения: {processing_error}")
                await send_telegram_message(chat_id, "Произошла ошибка при обработке вашего сообщения.")
                return {"status": "error"}

    except Exception as e:
        print(f"Критическая ошибка в webhook: {e}")
        return {"status": "critical_error"}