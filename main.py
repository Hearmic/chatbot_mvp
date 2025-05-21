from fastapi import FastAPI, Request, Depends
import os
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv
from openai import OpenAI
from database import SessionLocal
from sqlalchemy.orm import Session
import django
import logging
import pytz
from django.conf import settings

logger = logging.getLogger("uvicorn")

# Load environment variables
load_dotenv()
settings.configure()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.web.settings")
django.setup()

from web.admin_panel.models import Message
from users.models import Company, Client
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



def get_company_settings(company_id: int, db: Session) -> Dict[str, Any]:
    """Get company settings from database."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        return None
    
    return {
        "company": company.name,
        "language": company.language,
        "timezone": company.timezone,
        "working_hours": {
            "monday": company.monday_hours,
            "tuesday": company.tuesday_hours,
            "wednesday": company.wednesday_hours,
            "thursday": company.thursday_hours,
            "friday": company.friday_hours,
            "saturday": company.saturday_hours,
            "sunday": company.sunday_hours
        },
        "messages": {
            "welcome": company.welcome_message,
            "unavailable": company.unavailable_message,
            "fallback": company.fallback_message,
            "handoff": company.handoff_message,
            "off_hours": company.off_hours_message,
            "thanks": company.thanks_message
        },
        "allowed_topics": company.allowed_topics.split(','),
        "restricted_topics": company.restricted_topics.split(','),
        "handoff_trigger": company.handoff_trigger.split(','),
        "admin_settings": {
            "admin_id": company.admin_id,
            "notifications_enabled": company.notifications_enabled,
            "notification_hours": company.notification_hours,
            "email_notifications": company.email_notifications,
            "email_address": company.admin_email
        },
        "company_info": {
            "description": company.description,
            "address": company.address,
            "phone": company.phone,
            "email": company.email,
            "website": company.website
        },
        "policies": {
            "cancellation": company.cancellation_policy,
            "privacy": company.privacy_policy,
            "refund": company.refund_policy,
            "late_arrival": company.late_arrival_policy,
            "no_show": company.no_show_policy
        },
        "bot_settings": {
            "response_delay": company.response_delay,
            "typing_duration": company.typing_duration,
            "max_retries": company.max_retries,
            "enable_analytics": company.enable_analytics,
            "collect_feedback": company.collect_feedback,
            "available_languages": company.available_languages.split(',')
        }
    }  

def is_working_hours(working_hours: Dict[str, str], timezone_str: str = "Asia/Almaty") -> bool:
    """Check if current time is within working hours.
    
    Args:
        working_hours: Dictionary mapping weekdays to time ranges (e.g., {"monday": "9:00-18:00"})
        timezone_str: Timezone string (default: "Asia/Almaty")
        
    Returns:
        bool: True if current time is within working hours, False otherwise
    """
    try:
        # Get current time in the specified timezone
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        current_weekday = now.strftime("%A").lower()
        
        # Get working hours for current day (case-insensitive)
        day_hours = working_hours.get(current_weekday)
        if not day_hours:
            return False
            
        # Parse working hours (format: "HH:MM-HH:MM")
        try:
            start_time_str, end_time_str = day_hours.strip().split("-")
            start_time = datetime.strptime(start_time_str.strip(), "%H:%M").time()
            end_time = datetime.strptime(end_time_str.strip(), "%H:%M").time()
        except (ValueError, AttributeError) as e:
            logger.error(f"Invalid time format in working hours: {day_hours}. Error: {e}")
            return False
            
        current_time = now.time()
        
        # Handle overnight working hours (e.g., 22:00-06:00)
        if end_time < start_time:
            return current_time >= start_time or current_time <= end_time
        return start_time <= current_time <= end_time
        
    except pytz.exceptions.UnknownTimeZoneError as e:
        logger.error(f"Unknown timezone: {timezone_str}. Error: {e}")
        return True  # Default to True to avoid blocking messages due to timezone issues
    except Exception as e:
        logger.error(f"Error checking working hours: {e}", exc_info=True)
        return True  # Default to True to avoid blocking messages on error  # Default to available if there's an error

def build_prompt(script_profile: dict, user_message: str, history: list = None, 
                user_settings: dict = None, user_data: Client = None) -> str:
    """Create a prompt for the AI model using the script profile.
    
    Args:
        script_profile: Bot's script profile configuration
        user_message: Current user message
        history: List of previous messages in the conversation
        user_settings: User-specific settings
        user_data: Client model instance with additional user info
        
    Returns:
        str: Formatted prompt for the AI model
    """
    if history is None:
        history = []
    if user_settings is None:
        user_settings = {}

    # Build context sections
    sections = []
    
    # 1. Bot Identity and Role
    company_name = script_profile.get('company', 'компания')
    sections.append(f"""Ты - {company_name} чат-бот. 
Ты вежливый и профессиональный ассистент, который помогает клиентам с их вопросами.""")
    
    # 2. Working Hours
    working_hours = script_profile.get('working_hours', {})
    if working_hours:
        working_hours_list = [
            f"- {day.capitalize()}: {hours if hours else 'Выходной'}" 
            for day, hours in working_hours.items()
        ]
        sections.append("\n\nЧасы работы:\n" + "\n".join(working_hours_list))
    
    # 3. Company Information
    company_info = script_profile.get('company_info', {})
    if company_info:
        info_lines = []
        if desc := company_info.get('description'):
            info_lines.append(desc)
        if address := company_info.get('address'):
            info_lines.append(f"Адрес: {address}")
        if phone := company_info.get('phone'):
            info_lines.append(f"Телефон: {phone}")
        if email := company_info.get('email'):
            info_lines.append(f"Email: {email}")
        if website := company_info.get('website'):
            info_lines.append(f"Сайт: {website}")
            
        if info_lines:
            sections.append("\n\nО компании:\n" + "\n".join(info_lines))
    
    # 6. User Context
    if user_data:
        user_info = []
        if full_name := getattr(user_data, 'full_name', ''):
            user_info.append(f"Имя: {full_name}")
        if phone := getattr(user_data, 'phone_number', ''):
            user_info.append(f"Телефон: {phone}")
            
        if user_info:
            sections.append("\n\nИнформация о пользователе:\n" + "\n".join(user_info))
    
    # 7. Conversation History
    if history:
        history_lines = ["\n\nИстория переписки:"]
        for msg in history[-5:]:  # Last 5 messages for context
            role = "Пользователь" if msg.get("role") == "user" else "Ассистент"
            history_lines.append(f"{role}: {msg.get('content', '')}")
        sections.append("\n".join(history_lines))
    
    # 8. Current Message
    sections.append(f"\n\nПользователь: {user_message}")
    
    # 9. Instructions
    tone = script_profile.get('bot_settings', {}).get('tone', 'вежливым и профессиональным')
    off_topic = script_profile.get('messages', {}).get('off_topic', 'вежливо укажи на это')
    unknown = script_profile.get('messages', {}).get('unknown', 'предложи связаться с оператором')
    
    instructions = f"""
    Инструкции:
    1. Отвечай на том же языке, на котором был задан вопрос.
    2. Будь {tone}.
    3. Если вопрос не по теме, {off_topic}.
    4. Если не знаешь ответа, {unknown}.
    """
    
    sections.append(instructions)
    
    # Combine all sections
    system_prompt = "".join(sections)
    
    # Prepare messages for the chat model
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history
    for msg in history[-10:]:  # Last 10 messages for context
        role = "user" if msg.get("role") == "user" else "assistant"
        messages.append({"role": role, "content": msg.get("content", "")})
    
    # Add current user message
    messages.append({"role": "user", "content": user_message})
    
    return messages


def should_handoff(reply: str, handoff_triggers: list = None):
    """Check if the conversation should be handed off to a human operator."""
    if not reply:
        return False
        
    handoff_triggers = handoff_triggers or ["help"]
    reply_lower = reply.lower()
    
    # Check for handoff trigger phrases
    for trigger in handoff_triggers:
        if isinstance(trigger, str) and trigger.lower() in reply_lower:
            return True
    
    # Check for uncertainty in the response
    uncertainty_phrases = [
        "не знаю", "не уверен", "не могу ответить", 
        "не располагаю информацией", "не могу помочь",
        "извините, но я не могу", "к сожалению, я не могу"
    ]
    
    for phrase in uncertainty_phrases:
        if phrase in reply_lower:
            return True
    
    # Check if the response is too short or seems like a fallback
    if len(reply.strip()) < 10 and any(word in reply_lower for word in ["извините", "понимаю", "попробуйте"]):
        return True
            
    return False


@app.post("/webhook/{company_token}")
async def webhook(request: Request, company_token: str, db: Session = Depends(get_db)):
    try:
        # Get company by token
        company = db.query(Company).filter(Company.telegram_token == company_token).first()
        if not company:
            logger.error(f"Company not found with token: {company_token}")
            return {"status": "error", "message": "Company not found"}
            
        # Load company policy
        script_profile = load_company_policy(company.id)
        
        # Process webhook data
        data = await request.json()
        logger.info(f"Received webhook data: {data}")
        
        # Handle different update types
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            telegram_user_id = message["from"]["id"]
            
            # Get or create client
            client = db.query(Client).filter(Client.telegram_id == telegram_user_id, Client.company == company).first()
            if not client:
                # Create new client
                client = Client(
                    telegram_id=telegram_user_id,
                    company=company,
                    username=message["from"].get("username"),
                    settings={"preferred_language": "ru"}  # Default language
                )
                db.add(client)
                db.commit()
                db.refresh(client)
            
            # Update client data if available
            if "first_name" in message["from"]:
                client.username = message["from"].get("username", "")
                db.commit()
                db.refresh(client)
            
            # Get text message
            text = message.get("text", "").strip()
            # Get conversation history for this client
            history = db.query(Message).filter(
                Message.company == company,
                Message.user == client
            ).order_by(Message.timestamp.desc()).limit(10).all()  # Last 10 messages
            
            # Get user settings
            user_settings = client.settings or {}
            
            # Detect language of incoming message
            detected_language = detect_language(text)
    
            # Build the prompt with detected language
            messages = build_prompt(script_profile, text, history, user_settings, client, detected_language)
            reply = None
            service_used = None
            
            try:
                reply, service_used = await generate_ai_response(messages)
            except Exception as e:
                logger.error(f"Error generating AI response: {e}")
                reply = script_profile.get('messages', {}).get('error', 'Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.')
                
            # If reply is in English but detected language was Russian, translate it
            if detected_language == 'ru' and is_english(reply):
                reply = translate_to_russian(reply)
                
            # Save the user message
            user_message = Message.create_with_response_time(
                content=text,
                company=company,
                user=client,
                is_bot_response=False
            )

            # Save the bot response
            bot_response = Message.create_with_response_time(
                content=reply,
                company=company,
                user=client,
                is_bot_response=True
            )

            # Update daily analytics
            Analytics.update_daily_analytics(company)

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

    except Exception as e:
        logger.error(f"Unexpected error in webhook: {e}")
        return {"status": "error", "error": "Internal server error"}


