import click
import json
import requests
from typing import Dict, Any
from dotenv import load_dotenv
from database import SessionLocal
from models import Integration, Company
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

class IntegrationManager:
    def __init__(self):
        self.integrations = {
            'google_sheets': self._google_sheets_integration,
            'notion': self._notion_integration,
            'amocrm': self._amocrm_integration,
            'bitrix': self._bitrix_integration
        }

    def _google_sheets_integration(self, config: Dict[str, Any]):
        """Интеграция с Google Sheets."""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = Credentials.from_authorized_user_file(config['credentials_path'])
            service = build('sheets', 'v4', credentials=creds)
            
            # Пример: чтение данных из листа
            sheet = service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=config['spreadsheet_id'], 
                range=config.get('range', 'A1:Z')
            ).execute()
            
            return result.get('values', [])
        except Exception as e:
            click.echo(f"Ошибка интеграции с Google Sheets: {e}")
            return None

    def _notion_integration(self, config: Dict[str, Any]):
        """Интеграция с Notion."""
        try:
            from notion_client import Client

            notion = Client(auth=config['token'])
            page_id = config['page_id']
            
            # Получение содержимого страницы
            page = notion.pages.retrieve(page_id)
            return page
        except Exception as e:
            click.echo(f"Ошибка интеграции с Notion: {e}")
            return None

    def _amocrm_integration(self, config: Dict[str, Any]):
        """Интеграция с AmoCRM."""
        try:
            headers = {
                'Authorization': f'Bearer {config["access_token"]}',
                'Content-Type': 'application/json'
            }
            
            # Получение списка сделок
            response = requests.get(
                f'{config["base_url"]}/api/v4/leads', 
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            click.echo(f"Ошибка интеграции с AmoCRM: {e}")
            return None

    def _bitrix_integration(self, config: Dict[str, Any]):
        """Интеграция с Bitrix."""
        try:
            # Пример запроса к Bitrix24 API
            response = requests.get(
                f'{config["webhook_url"]}/crm.deal.list', 
                params={'select': ['*']}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            click.echo(f"Ошибка интеграции с Bitrix: {e}")
            return None

    def add_integration(self, company_id: int, service: str, config: Dict[str, Any]):
        """Добавление интеграции в базу данных."""
        db = SessionLocal()
        try:
            # Проверяем существование компании
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                click.echo(f"Компания с ID {company_id} не найдена.")
                return False

            # Создаем новую интеграцию
            integration = Integration(
                company_id=company_id,
                service_name=service,
                config=config,
                is_active=True
            )
            
            db.add(integration)
            db.commit()
            db.refresh(integration)
            
            click.echo(f"Интеграция с {service} добавлена для компании {company.name}")
            return True
        except SQLAlchemyError as e:
            db.rollback()
            click.echo(f"Ошибка при добавлении интеграции: {e}")
            return False
        finally:
            db.close()

    def list_integrations(self, company_id: int = None):
        """Список интеграций."""
        db = SessionLocal()
        try:
            query = db.query(Integration)
            if company_id:
                query = query.filter(Integration.company_id == company_id)
            
            integrations = query.all()
            
            if not integrations:
                click.echo("Интеграции не найдены.")
                return []
            
            for integration in integrations:
                click.echo(f"ID: {integration.id}")
                click.echo(f"Сервис: {integration.service_name}")
                click.echo(f"Компания ID: {integration.company_id}")
                click.echo(f"Активна: {'Да' if integration.is_active else 'Нет'}")
                click.echo("---")
            
            return integrations
        except SQLAlchemyError as e:
            click.echo(f"Ошибка при получении списка интеграций: {e}")
            return []
        finally:
            db.close()

    def test_integration(self, integration_id: int):
        """Тестирование интеграции по ID."""
        db = SessionLocal()
        try:
            integration = db.query(Integration).filter(Integration.id == integration_id).first()
            
            if not integration:
                click.echo(f"Интеграция с ID {integration_id} не найдена.")
                return False
            
            service = integration.service_name
            config = integration.config
            
            if service not in self.integrations:
                click.echo(f"Неподдерживаемый сервис: {service}")
                return False
            
            result = self.integrations[service](config)
            
            if result:
                click.echo(f"Успешная интеграция с {service}")
                click.echo(json.dumps(result, indent=2))
                return True
            else:
                click.echo(f"Не удалось получить данные от {service}")
                return False
        except Exception as e:
            click.echo(f"Ошибка при тестировании интеграции: {e}")
            return False
        finally:
            db.close()

@click.group()
def cli():
    """Утилита интеграции с внешними системами."""
    pass

@cli.command()
@click.option('--company-id', required=True, type=int, help='ID компании')
@click.option('--service', required=True, type=click.Choice(['google_sheets', 'notion', 'amocrm', 'bitrix']))
@click.option('--config-file', required=True, type=click.Path(exists=True), help='Путь к файлу конфигурации')
def add(company_id, service, config_file):
    """Добавить интеграцию для компании."""
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    manager = IntegrationManager()
    manager.add_integration(company_id, service, config)

@cli.command()
@click.option('--company-id', type=int, help='ID компании для фильтрации')
def list(company_id):
    """Список интеграций."""
    manager = IntegrationManager()
    manager.list_integrations(company_id)

@cli.command()
@click.argument('integration-id', type=int)
def test(integration_id):
    """Тестирование интеграции по ID."""
    manager = IntegrationManager()
    manager.test_integration(integration_id)

if __name__ == '__main__':
    cli()
