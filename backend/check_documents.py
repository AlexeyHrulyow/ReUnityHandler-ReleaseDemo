# check_documents.py в папке backend
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from reunity_app.db.session import AsyncSessionLocal
from reunity_app.db.models import Document, Case
from sqlalchemy import select


async def check_documents():
    async with AsyncSessionLocal() as session:
        # Проверяем все документы
        result = await session.execute(select(Document))
        documents = result.scalars().all()

        print(f"📊 Всего документов в базе: {len(documents)}")

        for doc in documents:
            print(f"\nДокумент ID: {doc.id}")
            print(f"  Case ID: {doc.case_id}")
            print(f"  Содержимое: {doc.content}")

            # Проверяем связанный случай
            case_result = await session.execute(select(Case).where(Case.id == doc.case_id))
            case = case_result.scalar_one_or_none()
            if case:
                print(f"  Случай: #{case.id} (пациент: {case.patient_id})")

        # Проверяем конкретный случай
        print(f"\n🔍 Проверяем случай ID=4:")
        case_result = await session.execute(select(Case).where(Case.id == 4))
        case = case_result.scalar_one_or_none()

        if case:
            print(f"  Случай найден: #{case.id}")
            doc_result = await session.execute(select(Document).where(Document.case_id == 4))
            document = doc_result.scalar_one_or_none()

            if document:
                print(f"  ✅ Документ для случая 4 найден: ID={document.id}")
            else:
                print(f"  ❌ Документ для случая 4 не найден!")
        else:
            print(f"  ❌ Случай 4 не найден в базе")


if __name__ == "__main__":
    asyncio.run(check_documents())