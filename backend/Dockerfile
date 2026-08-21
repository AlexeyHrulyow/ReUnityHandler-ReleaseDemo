FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Запускаем только uvicorn
CMD ["uvicorn", "reunity_app.main:app", "--host", "0.0.0.0", "--port", "8000"]