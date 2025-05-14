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
    
    # Политики и настройки компании
    policy = Column(JSON)  # Хранение политик в JSON
    
    # Связи с другими сущностями
    users = relationship("User", back_populates="company")
    messages = relationship("Message", back_populates="company")
    integrations = relationship("Integration", back_populates="company")
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

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
    is_постоянный_клиент = Column(Boolean, default=False)
    доступные_акции = Column(JSON)
    персональная_скидка = Column(Float, default=0.0)
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    settings = Column(JSON)  

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