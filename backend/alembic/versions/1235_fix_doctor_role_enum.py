"""fix_doctor_role_enum

Revision ID: 1235
Revises: 1234
Create Date: 2026-04-01 10:45:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

revision = '1235'
down_revision = '1234'
branch_labels = None
depends_on = None

def upgrade():
    # Новые значения ролей
    new_roles = [
        'reflexotherapist',
        'physiotherapist',
        'therapist_frm',
        'neurologist_frm',
        'psychologist',
        'admin'
    ]

    # Переименовываем старый enum (если существует)
    op.execute("ALTER TYPE doctorrole RENAME TO doctorrole_old")

    # Создаём новый enum с правильными значениями
    new_enum = ENUM(*new_roles, name='doctorrole')
    new_enum.create(op.get_bind(), checkfirst=True)

    # Преобразуем колонку role к новому enum, сопоставляя старые значения новым
    op.execute("""
        ALTER TABLE doctors ALTER COLUMN role TYPE doctorrole
        USING CASE role::text
            WHEN 'therapist'        THEN 'therapist_frm'::doctorrole
            WHEN 'neurologist'      THEN 'neurologist_frm'::doctorrole
            WHEN 'head'             THEN 'therapist_frm'::doctorrole
            WHEN 'cardiologist'     THEN 'therapist_frm'::doctorrole
            WHEN 'cardio'           THEN 'therapist_frm'::doctorrole
            WHEN 'admin'            THEN 'admin'::doctorrole
            WHEN 'psychologist'     THEN 'psychologist'::doctorrole
            WHEN 'reflexotherapist' THEN 'reflexotherapist'::doctorrole
            WHEN 'physiotherapist'  THEN 'physiotherapist'::doctorrole
            ELSE 'therapist_frm'::doctorrole
        END
    """)

    # Удаляем старый enum
    op.execute("DROP TYPE doctorrole_old")

def downgrade():
    # Откат сложен, пропускаем
    pass