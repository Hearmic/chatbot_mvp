from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, Float
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    text = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    service_used = Column(String, nullable=True)  

    user = relationship("User", back_populates="messages")

class User(Base):
    __tablename__ = "users"
    is_постоянный_клиент = Column(Boolean, default=False)
    доступные_акции = Column(JSON)
    персональная_скидка = Column(Float, default=0.0)
    id = Column(Integer, primary_key=True, index=True)
    settings = Column(JSON)  

    messages = relationship("Message", back_populates="user")