import os
import sys
import pytest
import asyncio

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set testing environment variable
os.environ['TESTING'] = 'true'

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app, get_db
from database import Base
from models import User, Company, Message

# Create a test database
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="function")
def test_db():
    """Create and drop test database for each test."""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    
    # Create a default test company with a consistent name
    default_company = Company(
        name="Default Company",
        telegram_token="test_token_default",
        is_active=True,
        description="Default test company",
        policy={
            "company": "Default Company",
            "allowed_topics": ["support"],
            "restricted_topics": ["confidential"]
        }
    )
    db.add(default_company)
    db.commit()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(bind=test_engine)

def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_load_company_policy(test_db):
    """Test loading company policy."""
    from main import load_company_policy
    
    policy = load_company_policy(company_id=1)
    
    assert isinstance(policy, dict)
    assert "company" in policy
    assert "allowed_topics" in policy
    assert "restricted_topics" in policy
    assert policy["company"] == "CLI Test Company"
    
def test_build_prompt(test_db):
    """Test building a prompt for AI response."""
    from main import build_prompt
    
    script_profile = {
        "company": "CLI Test Company",
        "allowed_topics": ["support"],
        "restricted_topics": ["confidential"],
        "company_info": {}
    }
    
    user_settings = {"preferred_language": "ru"}
    user_message = "Hello, how are you?"
    
    prompt = build_prompt(script_profile, user_message, user_settings=user_settings)
    
    assert isinstance(prompt, list)
    assert len(prompt) > 0
    assert prompt[0]["role"] == "system"
    assert "CLI Test Company" in prompt[0]["content"]

def test_should_handoff():
    """Test handoff trigger detection."""
    from main import should_handoff
    
    assert should_handoff("Я не уверен, могу ли помочь") == True
    assert should_handoff("Всё хорошо, я могу помочь") == False

@pytest.mark.asyncio
async def test_generate_ai_response(mocker):
    """Test AI response generation with mocking."""
    from main import generate_ai_response
    import openai
    
    prompt = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"}
    ]
    
    # Call the function directly
    response, service_used = await generate_ai_response(prompt)
    
    assert isinstance(response, str)
    assert isinstance(service_used, str)
    assert len(response) > 0

def test_company_cli_create(test_db):
    """Test company CLI create command."""
    from company_cli import create
    from click.testing import CliRunner
    
    runner = CliRunner()
    result = runner.invoke(create, [
        '--name', 'New Test Company', 
        '--description', 'A test company', 
        '--website', 'https://test.com',
        '--policy-file', '/Users/a_grish/Desktop/chatbot_mvp/tests/test_policy.json',
        '--force'
    ])
    
    assert result.exit_code == 0
    assert "Компания 'New Test Company' создана" in result.output

def test_database_init(test_db):
    """Test database initialization."""
    from database import init_db
    
    init_db(test_db)
    
    # Check default company exists
    companies = test_db.query(Company).all()
    assert len(companies) > 0
    assert any(company.name == "Default Company" for company in companies)
