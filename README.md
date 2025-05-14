# Корпоративный Чат-Бот 🤖

## 🌟 Обзор проекта

Многофункциональный корпоративный чат-бот с поддержкой мультитенантности, интеграций и AI-ассистента.

### 🚀 Ключевые возможности

- **Мультитенантность**: Единая платформа для нескольких компаний
- **AI-ассистент**: Интеллектуальные ответы на основе LLM
- **Интеграции**: Подключение к CRM, ERP, CMS системам
- **Гибкие политики**: Настройка поведения для каждой компании

## 🛠 Архитектура системы

### Компоненты
- `main.py`: Основной webhook и логика бота
- `models.py`: ORM модели данных
- `database.py`: Управление базой данных
- `integrations_cli.py`: CLI для работы с интеграциями
- `company_cli.py`: Управление компаниями

### 📦 Модели данных
- `Company`: Информация о компании
- `User`: Пользователи компании
- `Message`: История сообщений
- `Integration`: Внешние интеграции

## 🔧 Установка и настройка

### Prerequisites
- Python 3.10+
- SQLite
- Telegram Bot Token
- OpenAI API Key

### Шаги установки
```bash
# Клонирование репозитория
git clone https://github.com/yourusername/chatbot_mvp.git
cd chatbot_mvp

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Инициализация базы данных
python -c "from database import init_db; init_db()"
```

## 🤝 Управление компаниями

### CLI для работы с компаниями

#### Создание компании
```bash
# Создание новой компании с интерактивным вводом
python company_cli.py create

# С предустановленными параметрами
python company_cli.py create \
    --name "Example" \
    --description "Some description" \
    --website "https://example.com \
    --policy-file path/to/example_policy.json
```

#### Список компаний
```bash
# Показать все компании
python company_cli.py list
```

#### Обновление компании
```bash
# Обновить название и статус компании
python company_cli.py update 1 \
    --name "New Company Name" \
    --active
```

#### Удаление компании
```bash
# Удалить компанию по ID
python company_cli.py delete 1
```

## 🔗 Интеграции

### Поддерживаемые сервисы
- Google Sheets
- Notion
- AmoCRM
- Bitrix24

### Работа с интеграциями
```bash
# Добавление интеграции
python integrations_cli.py add \
    --company-id 1 \
    --service google_sheets \
    --config-file configs/google_sheets_config.json

# Тестирование интеграции
python integrations_cli.py test 1
```

## 🔐 Безопасность
- Токены и ключи хранятся в `.env`
- Изоляция данных между компаниями
- Поддержка ролевого доступа

## 📈 Мониторинг и аналитика
- Логирование всех взаимодействий
- Статистика использования
- Обратная связь от пользователей

## 🛣 Roadmap
- [ ] Веб-интерфейс управления
- [ ] Расширение списка интеграций
- [ ] Машинное обучение для улучшения ответов
- [ ] Мультиязычность

## 🤔 Как помочь проекту
1. Fork репозитория
2. Создайте feature-branch
3. Commit изменений
4. Push и создайте Pull Request

## 📄 Лицензия
MIT License

## 📧 Контакты
[Ваши контактные данные]
