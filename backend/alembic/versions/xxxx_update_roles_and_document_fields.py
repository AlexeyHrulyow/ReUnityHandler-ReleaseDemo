"""update_roles_and_document_fields

Revision ID: xxxx
Revises: 666b92a789e4
Create Date: 2026-02-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision = 'xxxx'  # оставьте тот же ID
down_revision = '666b92a789e4'
branch_labels = None
depends_on = None

# Старый и новый enum для ролей
old_enum = ENUM('therapist', 'neurologist', 'head', 'admin', 'psychologist', 'cardiologist', name='doctorrole')
new_enum = ENUM('reflexotherapist', 'physiotherapist', 'therapist_frm', 'neurologist_frm', 'psychologist', 'admin', name='doctorrole')

def upgrade():
    # ### Удаляем cardiologist из documents
    op.drop_column('documents', 'cardiologist_completed')
    op.drop_column('documents', 'cardiologist_filled_at')

    # ### Добавляем новые поля для рефлексотерапевта и физиотерапевта
    op.add_column('documents', sa.Column('reflexotherapist_completed', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('documents', sa.Column('physiotherapist_completed', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('documents', sa.Column('reflexotherapist_filled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('documents', sa.Column('physiotherapist_filled_at', sa.DateTime(timezone=True), nullable=True))

    # ### Переименовываем старые поля
    op.alter_column('documents', 'neurologist_completed', new_column_name='neurologist_frm_completed')
    op.alter_column('documents', 'neurologist_filled_at', new_column_name='neurologist_frm_filled_at')
    op.alter_column('documents', 'therapist_completed', new_column_name='therapist_frm_completed')
    op.alter_column('documents', 'therapist_filled_at', new_column_name='therapist_frm_filled_at')
    op.drop_column('documents', 'head_completed')
    op.drop_column('documents', 'head_filled_at')

    # ### Удаляем кардиологов (используем текстовое сравнение, чтобы избежать проблем с enum)
    op.execute("DELETE FROM doctors WHERE role::text = 'cardiologist'")

    # ### Создаём новый enum
    op.execute("ALTER TYPE doctorrole RENAME TO doctorrole_old")
    new_enum.create(op.get_bind(), checkfirst=False)

    # ### Изменяем тип колонки с явным сопоставлением старых значений новым
    op.execute("""
        ALTER TABLE doctors ALTER COLUMN role TYPE doctorrole
        USING CASE role::text
            WHEN 'therapist' THEN 'therapist_frm'::doctorrole
            WHEN 'neurologist' THEN 'neurologist_frm'::doctorrole
            WHEN 'head' THEN 'therapist_frm'::doctorrole
            WHEN 'psychologist' THEN 'psychologist'::doctorrole
            WHEN 'admin' THEN 'admin'::doctorrole
            ELSE 'therapist_frm'::doctorrole
        END
    """)

    # ### Удаляем старый enum
    op.execute("DROP TYPE doctorrole_old")

def downgrade():
    # Сложный downgrade, можно пропустить или реализовать при необходимости
    pass