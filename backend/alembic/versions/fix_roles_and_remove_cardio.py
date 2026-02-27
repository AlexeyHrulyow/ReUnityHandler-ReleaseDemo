"""fix_roles_and_remove_cardio

Revision ID: fix_roles_2
Revises: xxxx
Create Date: 2026-02-27 15:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision = 'fix_roles_2'
down_revision = 'xxxx'          # ⚠️ Убедитесь, что это правильный ID предыдущей миграции
branch_labels = None
depends_on = None

# Новые значения ролей (в правильном порядке)
NEW_ROLES = [
    'reflexotherapist',
    'physiotherapist',
    'therapist_frm',
    'neurologist_frm',
    'psychologist',
    'admin'
]

def upgrade():
    connection = op.get_bind()

    # 1. Удаляем кардиологические поля из таблицы documents (если они есть)
    inspector = sa.inspect(connection)
    columns_in_documents = [col['name'] for col in inspector.get_columns('documents')]

    if 'cardiologist_completed' in columns_in_documents:
        op.drop_column('documents', 'cardiologist_completed')
    if 'cardiologist_filled_at' in columns_in_documents:
        op.drop_column('documents', 'cardiologist_filled_at')

    # 2. Удаляем врачей с неправильными ролями 'cardio' или 'cardiologist'
    op.execute("DELETE FROM doctors WHERE role::text IN ('cardio', 'cardiologist')")

    # 3. Создаём новый enum с правильными значениями (если не существует)
    new_enum = ENUM(*NEW_ROLES, name='doctorrole_new')
    new_enum.create(connection, checkfirst=True)

    # 4. Преобразуем тип колонки role, сопоставляя старые значения новым
    op.execute("""
        ALTER TABLE doctors ALTER COLUMN role TYPE doctorrole_new
        USING CASE role::text
            WHEN 'therapist'        THEN 'therapist_frm'::doctorrole_new
            WHEN 'neurologist'      THEN 'neurologist_frm'::doctorrole_new
            WHEN 'head'             THEN 'therapist_frm'::doctorrole_new   -- head больше не используется
            WHEN 'cardiologist'     THEN 'therapist_frm'::doctorrole_new   -- запасной вариант
            WHEN 'cardio'           THEN 'therapist_frm'::doctorrole_new
            WHEN 'admin'            THEN 'admin'::doctorrole_new
            WHEN 'psychologist'     THEN 'psychologist'::doctorrole_new
            WHEN 'reflexotherapist' THEN 'reflexotherapist'::doctorrole_new
            WHEN 'physiotherapist'  THEN 'physiotherapist'::doctorrole_new
            ELSE 'therapist_frm'::doctorrole_new
        END
    """)

    # 5. Удаляем старые enum'ы, если они существуют (IF EXISTS предотвращает ошибку)
    op.execute("DROP TYPE IF EXISTS doctorrole")
    op.execute("DROP TYPE IF EXISTS doctorrole_old")

    # 6. Переименовываем новый enum в окончательное имя
    op.execute("ALTER TYPE doctorrole_new RENAME TO doctorrole")

def downgrade():
    # Откат этой миграции сложен и обычно не требуется.
    # При необходимости можно восстановить старую структуру, но это выходит за рамки задачи.
    pass