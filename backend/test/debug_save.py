# backend/debug_save.py
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from reunity_app.db.session import AsyncSessionLocal
from reunity_app.db.models import Document
from sqlalchemy import select


async def debug_document_save():
    async with AsyncSessionLocal() as session:
        print("🔍 Проверка сохранения документа...")

        # Получаем документ с ID=4
        result = await session.execute(
            select(Document).where(Document.id == 4)
        )
        document = result.scalar_one_or_none()

        if document:
            print(f"✅ Документ найден: ID={document.id}")
            print(f"📊 Содержимое документа:")
            for key, value in document.content.items():
                print(f"   {key}: {value}")

            print(f"📊 Статусы заполнения:")
            print(f"   Невролог: {document.neurologist_completed}")
            print(f"   Терапевт: {document.therapist_completed}")
            print(f"   Заведующий: {document.head_completed}")

            # Проверяем, что данные действительно сохраняются
            print(f"📊 Последнее обновление: {document.updated_at}")

            # Сохраняем тестовые изменения
            old_content = document.content.copy()
            document.content["pain_syndrome"] = ["Болевой синдром", "10", "5"]

            await session.commit()

            # Перезагружаем документ
            await session.refresh(document)

            print(f"✅ Изменения сохранены:")
            print(f"   Было: {old_content.get('pain_syndrome')}")
            print(f"   Стало: {document.content.get('pain_syndrome')}")

        else:
            print("❌ Документ не найден")


if __name__ == "__main__":
    asyncio.run(debug_document_save())