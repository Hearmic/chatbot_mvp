import click
import json
import uuid
from database import SessionLocal
from models import Company
from sqlalchemy.exc import SQLAlchemyError

@click.group()
def cli():
    """Утилита управления компаниями в мультитенантной системе."""
    pass

@cli.command()
@click.option('--name', prompt='Название компании', help='Название компании')
@click.option('--description', prompt='Описание', help='Описание компании')
@click.option('--website', prompt='Веб-сайт', help='Веб-сайт компании')
@click.option('--policy-file', type=click.Path(exists=True), help='Путь к файлу политики')
def create(name, description, website, policy_file):
    """Создать новую компанию."""
    db = SessionLocal()
    
    try:
        # Генерируем уникальный токен
        telegram_token = str(uuid.uuid4())
        
        # Загружаем политику из файла, если указан
        policy = {}
        if policy_file:
            with open(policy_file, 'r') as f:
                policy = json.load(f)
        
        company = Company(
            name=name, 
            telegram_token=telegram_token,
            description=description or '',
            website=website or '',
            policy=policy,
            is_active=True
        )
        
        db.add(company)
        db.commit()
        db.refresh(company)
        
        click.echo(f"Компания '{name}' создана.")
        click.echo(f"ID компании: {company.id}")
        click.echo(f"Telegram Token: {telegram_token}")
        
    except SQLAlchemyError as e:
        db.rollback()
        click.echo(f"Ошибка при создании компании: {e}")
    finally:
        db.close()

@cli.command()
def list():
    """Список всех компаний."""
    db = SessionLocal()
    
    try:
        companies = db.query(Company).all()
        
        if not companies:
            click.echo("Компании не найдены.")
            return
        
        click.echo("Список компаний:")
        for company in companies:
            click.echo(f"ID: {company.id}")
            click.echo(f"Название: {company.name}")
            click.echo(f"Telegram Token: {company.telegram_token}")
            click.echo(f"Описание: {company.description or 'Не указано'}")
            click.echo(f"Веб-сайт: {company.website or 'Не указан'}")
            click.echo(f"Активна: {'Да' if company.is_active else 'Нет'}")
            click.echo("---")
    
    except SQLAlchemyError as e:
        click.echo(f"Ошибка при получении списка компаний: {e}")
    finally:
        db.close()

@cli.command()
@click.argument('company_id', type=int)
def delete(company_id):
    """Удалить компанию по ID."""
    db = SessionLocal()
    
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        
        if not company:
            click.echo(f"Компания с ID {company_id} не найдена.")
            return
        
        db.delete(company)
        db.commit()
        click.echo(f"Компания '{company.name}' удалена.")
    
    except SQLAlchemyError as e:
        db.rollback()
        click.echo(f"Ошибка при удалении компании: {e}")
    finally:
        db.close()

@cli.command()
@click.argument('company_id', type=int)
@click.option('--name', help='Новое название компании')
@click.option('--description', help='Новое описание')
@click.option('--website', help='Новый веб-сайт')
@click.option('--policy-file', type=click.Path(exists=True), help='Путь к новому файлу политики')
@click.option('--active/--inactive', help='Активировать или деактивировать компанию')
def update(company_id, name, description, website, policy_file, active):
    """Обновить информацию о компании."""
    db = SessionLocal()
    
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        
        if not company:
            click.echo(f"Компания с ID {company_id} не найдена.")
            return
        
        if name:
            company.name = name
        if description is not None:
            company.description = description
        if website is not None:
            company.website = website
        if policy_file:
            with open(policy_file, 'r') as f:
                company.policy = json.load(f)
        if active is not None:
            company.is_active = active
        
        db.commit()
        click.echo(f"Информация о компании {company_id} обновлена.")
    
    except SQLAlchemyError as e:
        db.rollback()
        click.echo(f"Ошибка при обновлении компании: {e}")
    except Exception as e:
        db.rollback()
        click.echo(f"Ошибка при чтении файла политики: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    cli()
