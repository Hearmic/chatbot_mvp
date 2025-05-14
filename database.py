from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import uuid

DATABASE_URL = "sqlite:///./chatbot.db"  # Путь к файлу базы данных
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    """
    Создание всех таблиц в базе данных.
    При каждом запуске проверяет наличие таблиц и создает их, если они отсутствуют.
    """
    from models import Base, Company  # Импортируем здесь, чтобы избежать циклического импорта
    Base.metadata.create_all(bind=engine)
    
    # Создаем первую компанию, если она еще не существует
    db = SessionLocal()
    existing_company = db.query(Company).first()
    
    if not existing_company:
        default_company = Company(
            name="Default Company",
            telegram_token=str(uuid.uuid4()),
            description="Первая компания в системе",
            policy={},
            is_active=True
        )
        db.add(default_company)
        db.commit()
        print("Создана первая компания: Default Company")
    
    db.close()

def drop_db():
    """
    Удаление всех таблиц из базы данных.
    Используется для полного сброса базы данных.
    """
    from models import Base
    Base.metadata.drop_all(bind=engine)

def reset_db():
    """
    Полный сброс и пересоздание базы данных.
    """
    drop_db()
    init_db()