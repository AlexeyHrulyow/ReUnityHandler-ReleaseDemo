"""fix_roles_data

Revision ID: fix_roles_data
Revises: fix_roles_2
Create Date: 2026-02-27 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'fix_roles_data'
down_revision = 'fix_roles_2'  # ⚠️ Укажите сюда ID предыдущей миграции, если он другой
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    # 1. Удаляем кардиолога (username = 'cardio')
    connection.execute(
        sa.text("DELETE FROM doctors WHERE username = 'cardio'")
    )

    # 2. Исправляем роли для остальных врачей по username
    #    Используем UPDATE с CASE по username
    connection.execute(
        sa.text("""
            UPDATE doctors
            SET role = CASE username
                WHEN 'admin'        THEN 'admin'::doctorrole
                WHEN 'head'         THEN 'therapist_frm'::doctorrole
                WHEN 'neuro'        THEN 'neurologist_frm'::doctorrole
                WHEN 'physic'       THEN 'physiotherapist'::doctorrole
                WHEN 'psychologist' THEN 'psychologist'::doctorrole
                WHEN 'reflex'       THEN 'reflexotherapist'::doctorrole
                WHEN 'therapist'    THEN 'therapist_frm'::doctorrole
                ELSE role  -- на всякий случай оставляем текущее значение
            END
        """)
    )


def downgrade():
    # Откат этой миграции сложен и обычно не требуется.
    # При необходимости можно вернуть данные в исходное состояние,
    # но для этого нужно знать предыдущие роли.
    pass