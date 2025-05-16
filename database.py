import os
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

# Determine the path for the SQLite database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'chatbot.db')}"

# Create engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for declarative models
Base = declarative_base()

def init_db():
    """
    Initialize the database by creating all tables defined in the models.
    This function should be called when the application starts.
    """
    try:
        # Import models here to avoid circular imports
        from models import Company, Message, User, Integration
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully.")
        
        # Проверяем, есть ли уже компании
        existing_companies = SessionLocal().query(Company).count()
        if existing_companies == 0:
            default_company = Company(
                name="Default Company", 
                telegram_token=str(uuid.uuid4()),
                description="Первая компания в системе",
                is_active=True,
                policy={
                    "company": "Default Company",
                    "allowed_topics": ["support"],
                    "restricted_topics": ["confidential"]
                }
            )
            session = SessionLocal()
            session.add(default_company)
            session.commit()
            session.close()
    except OperationalError as e:
        print(f"Error creating database tables: {e}")
    except Exception as e:
        print(f"Unexpected error initializing database: {e}")

# Optional: Function to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def drop_db():
    """
    Удаление всех таблиц из базы данных.
    Используется для полного сброса базы данных.
    """
    Base.metadata.drop_all(bind=engine)

def reset_db():
    """
    Полный сброс и пересоздание базы данных.
    """
    drop_db()
    init_db()