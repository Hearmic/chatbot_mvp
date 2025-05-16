import os
import click
import json
import asyncio
from dotenv import load_dotenv
from telegram import Bot
from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import Company

# Initialize database
init_db()

# Load environment variables
load_dotenv()

@click.group()
def cli():
    """Утилита управления компаниями в мультитенантной системе."""
    pass

@cli.command()
@click.option('--name', prompt='Название компании', help='Название компании')
@click.option('--description', prompt='Описание (необязательно)', default='', help='Описание компании')
@click.option('--website', prompt='Сайт (необязательно)', default='', help='Веб-сайт компании')
@click.option('--policy-file', prompt='Путь к файлу политики', help='Путь к JSON-файлу с политикой')
@click.option('--telegram-token', prompt='Токен Telegram бота', help='Токен Telegram бота')
@click.option('--force', is_flag=True, help='Принудительное создание компании')
def create(name, description, website, policy_file, telegram_token, force=False):
    """Создать новую компанию."""
    async def async_create():
        try:
            # Проверка токена Telegram
            try:
                bot = Bot(token=telegram_token)
                bot_info = await bot.get_me()
                bot_username = bot_info.username
                bot_id = bot_info.id
            except Exception as e:
                click.echo(f"Ошибка при проверке токена Telegram: {e}")
                return

            # Инициализация сессии базы данных
            db = SessionLocal()

            try:
                # Проверка существования компании
                existing_company = db.query(Company).filter(Company.name == name).first()
                if existing_company:
                    if force:
                        # Удаляем существующую компанию
                        db.delete(existing_company)
                        db.commit()
                    else:
                        click.echo(f"Компания с именем '{name}' уже существует.")
                        return

                # Чтение политики из файла
                with open(policy_file, 'r') as f:
                    policy = json.load(f)

                # Создание новой компании
                company = Company(
                    name=name,
                    telegram_token=telegram_token,
                    telegram_username=bot_username,
                    telegram_bot_id=bot_id,
                    description=description or '',
                    website=website or '',
                    policy=policy,
                    is_active=True
                )

                db.add(company)
                db.commit()
                db.refresh(company)

                click.echo(f"Компания '{name}' успешно создана.")
                click.echo(f"Telegram бот: @{bot_username}")
                click.echo(f"ID бота: {bot_id}")

            except Exception as e:
                click.echo(f"Ошибка при создании компании: {e}")
            finally:
                db.close()

        except Exception as e:
            click.echo(f"Общая ошибка: {e}")

    # Запуск асинхронной функции
    asyncio.run(async_create())

@cli.command()
def list():
    """Список всех компаний."""
    db = SessionLocal()
    try:
        companies = db.query(Company).all()
        if not companies:
            click.echo("Компании не найдены.")
        else:
            for company in companies:
                click.echo(f"ID: {company.id}, Название: {company.name}, Telegram: @{company.telegram_username or 'Не указан'}")
    except Exception as e:
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
    
    except Exception as e:
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
    
    except Exception as e:
        db.rollback()
        click.echo(f"Ошибка при обновлении компании: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    cli()
