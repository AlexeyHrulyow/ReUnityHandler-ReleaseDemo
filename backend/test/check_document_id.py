# check_document_id.py
import asyncio
import sys
from pathlib import Path

from db.models import Document

sys.path.insert(0, str(Path(__file__).parent))

from reunity_app.db.session import AsyncSessionLocal
from sqlalchemy import select


async def check_document_id():
    async with AsyncSessionLocal() as session:
        print("🔍 Проверяем документ для случая 4...")

        # Находим документ по case_id=4
        result = await session.execute(
            select(Document).where(Document.case_id == 4)
        )
        document = result.scalar_one_or_none()

        if document:
            print(f"✅ Документ найден:")
            print(f"   ID документа: {document.id}")
            print(f"   ID случая: {document.case_id}")
            print(f"   Контент: {document.content}")
        else:
            print("❌ Документ не найден")

            # Проверяем сам случай
            from reunity_app.db.models import Case
            case_result = await session.execute(
                select(Case).where(Case.id == 4)
            )
            case = case_result.scalar_one_or_none()
            print(f"   Случай 4 существует: {'Да' if case else 'Нет'}")


if __name__ == "__main__":
    asyncio.run(check_document_id())