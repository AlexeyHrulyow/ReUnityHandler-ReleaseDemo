# update_db_fix_encoding.py
import asyncio
import asyncpg
import os
import sys
from pathlib import Path
import chardet  # Для определения кодировки


# Устанавливаем chardet если нет
# pip install chardet

def get_database_url():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        # Определяем кодировку файла
        with open(env_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            print(f"Определена кодировка .env: {encoding}")

        # Читаем файл в правильной кодировке
        with open(env_path, 'r', encoding=encoding) as f:
            for line in f:
                line = line.strip()
                if line.startswith('DATABASE_URL='):
                    return line.split('=', 1)[1]
    return None

# ... остальной код остается таким же