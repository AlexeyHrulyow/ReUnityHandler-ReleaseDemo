FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Автоматически применяем миграции -> создаем админа -> запускаем сервер
CMD ["sh", "-c", "alembic upgrade head && python seed.py && uvicorn reunity_app.main:app --host 0.0.0.0 --port 8000"]