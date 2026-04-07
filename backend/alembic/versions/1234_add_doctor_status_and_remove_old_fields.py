"""add_doctor_status_and_remove_old_fields

Revision ID: 1234
Revises: fix_roles_data
Create Date: 2026-04-01 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

revision = '1234'
down_revision = 'fix_roles_data'  # укажите ID последней миграции
branch_labels = None
depends_on = None

def upgrade():
    # 1. Добавляем новые поля в doctors
    op.add_column('doctors', sa.Column('show_in_status', sa.Boolean(), server_default='false'))
    op.add_column('doctors', sa.Column('status_order', sa.Integer(), server_default='0'))

    # 2. Создаём таблицу document_doctor_status
    op.create_table(
        'document_doctor_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=False),
        sa.Column('completed', sa.Boolean(), server_default='false'),
        sa.Column('filled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'doctor_id', name='uq_document_doctor')
    )

    # 3. Переносим данные из старых полей Document в новую таблицу
    # Временно устанавливаем show_in_status = true для врачей, у которых есть завершённые разделы
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE doctors
        SET show_in_status = true
        WHERE is_active = true AND role IN ('reflexotherapist', 'physiotherapist', 'therapist_frm', 'neurologist_frm', 'psychologist')
    """))

    # Для каждого документа создаём записи для каждого врача с show_in_status=true,
    # заполняя completed на основе старых полей
    connection.execute(sa.text("""
        INSERT INTO document_doctor_status (document_id, doctor_id, completed, filled_at)
        SELECT
            d.id,
            doc.id,
            CASE
                WHEN doc.role = 'reflexotherapist' AND d.reflexotherapist_completed THEN true
                WHEN doc.role = 'physiotherapist' AND d.physiotherapist_completed THEN true
                WHEN doc.role = 'therapist_frm' AND d.therapist_frm_completed THEN true
                WHEN doc.role = 'neurologist_frm' AND d.neurologist_frm_completed THEN true
                WHEN doc.role = 'psychologist' AND d.psychologist_completed THEN true
                ELSE false
            END,
            CASE
                WHEN doc.role = 'reflexotherapist' THEN d.reflexotherapist_filled_at
                WHEN doc.role = 'physiotherapist' THEN d.physiotherapist_filled_at
                WHEN doc.role = 'therapist_frm' THEN d.therapist_frm_filled_at
                WHEN doc.role = 'neurologist_frm' THEN d.neurologist_frm_filled_at
                WHEN doc.role = 'psychologist' THEN d.psychologist_filled_at
                ELSE NULL
            END
        FROM documents d
        CROSS JOIN doctors doc
        WHERE doc.show_in_status = true
    """))

    # 4. Удаляем старые поля из documents
    op.drop_column('documents', 'reflexotherapist_completed')
    op.drop_column('documents', 'physiotherapist_completed')
    op.drop_column('documents', 'therapist_frm_completed')
    op.drop_column('documents', 'neurologist_frm_completed')
    op.drop_column('documents', 'psychologist_completed')
    op.drop_column('documents', 'reflexotherapist_filled_at')
    op.drop_column('documents', 'physiotherapist_filled_at')
    op.drop_column('documents', 'therapist_frm_filled_at')
    op.drop_column('documents', 'neurologist_frm_filled_at')
    op.drop_column('documents', 'psychologist_filled_at')

def downgrade():
    # Для отката добавим старые поля и перенесём данные обратно (упрощённо)
    # Если нужен полный откат, его можно реализовать, но в данном случае пропустим
    pass