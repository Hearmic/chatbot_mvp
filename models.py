from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, Float, Text
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    telegram_token = Column(String, unique=True, nullable=False)
    description = Column(Text)
    website = Column(String)
    policy = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Optional new columns
    telegram_username = Column(String, nullable=True)
    telegram_bot_id = Column(Integer, nullable=True)

    # Связи с другими сущностями
    users = relationship("User", back_populates="company")
    messages = relationship("Message", back_populates="company")
    integrations = relationship("Integration", back_populates="company")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    text = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    service_used = Column(String, nullable=True)  

    user = relationship("User", back_populates="messages")
    company = relationship("Company", back_populates="messages")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=True)  # telegram username
    email = Column(String, unique=True, index=True, nullable=True)
    telegram_id = Column(Integer, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    hashed_password = Column(String, nullable=True)
    
    # Новые поля для клиентского профиля
    is_постоянный_клиент = Column(Boolean, default=False)
    доступные_акции = Column(JSON, default=list)
    персональная_скидка = Column(Float, default=0.0)
    
    # Настройки пользователя
    settings = Column(JSON, default=dict)

    # Связь с компанией
    company = relationship("Company", back_populates="users")
    messages = relationship("Message", back_populates="user")

class Integration(Base):
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    service_name = Column(String, nullable=False)  # google_sheets, notion, amocrm и т.д.
    config = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Связь с компанией
    company = relationship("Company", back_populates="integrations")

    # Метаданные
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)