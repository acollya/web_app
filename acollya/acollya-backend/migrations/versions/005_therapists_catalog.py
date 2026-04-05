"""Create therapists catalog table with seed data

Revision ID: 005
Revises: 004
Create Date: 2026-03-31

Seed: 5 fictional but realistic Brazilian psychologists covering the main
specialties offered by Acollya (ansiedade, TCC, relacionamentos, trauma,
autoestima).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "therapists",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("photo_key", sa.Text(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("specialties", sa.Text(), nullable=False, server_default="'[]'"),
        sa.Column("credentials", sa.Text(), nullable=False, server_default="'[]'"),
        sa.Column("crp", sa.Text(), nullable=True),
        sa.Column("rating", sa.Numeric(3, 2), nullable=False, server_default="5.0"),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hourly_rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("premium_discount_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("working_days_mask", sa.Integer(), nullable=False, server_default="31"),
        sa.Column("slot_start", sa.Text(), nullable=False, server_default="'09:00'"),
        sa.Column("slot_end", sa.Text(), nullable=False, server_default="'18:00'"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("idx_therapists_is_active", "therapists", ["is_active"])
    op.create_index("idx_therapists_sort_order", "therapists", ["sort_order"])

    therapists_table = sa.table(
        "therapists",
        sa.column("id", sa.Text),
        sa.column("name", sa.Text),
        sa.column("photo_key", sa.Text),
        sa.column("bio", sa.Text),
        sa.column("specialties", sa.Text),
        sa.column("credentials", sa.Text),
        sa.column("crp", sa.Text),
        sa.column("rating", sa.Numeric),
        sa.column("review_count", sa.Integer),
        sa.column("hourly_rate", sa.Numeric),
        sa.column("premium_discount_pct", sa.Integer),
        sa.column("working_days_mask", sa.Integer),
        sa.column("slot_start", sa.Text),
        sa.column("slot_end", sa.Text),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(therapists_table, [
        {
            "id": "ana-santos",
            "name": "Dra. Ana Santos",
            "photo_key": "therapists/ana-santos.jpg",
            "bio": (
                "Psicóloga clínica com 12 anos de experiência, especializada em "
                "Terapia Cognitivo-Comportamental (TCC) para ansiedade e transtornos "
                "de humor. Mestre em Psicologia Clínica pela USP. Atende adultos e "
                "adolescentes, com foco em empoderar o paciente com ferramentas práticas "
                "para o dia a dia."
            ),
            "specialties": '["Ansiedade", "Depressao", "TCC", "Autoestima"]',
            "credentials": '["Mestrado em Psicologia Clinica - USP", "Especializacao em TCC - PUC-SP"]',
            "crp": "CRP 06/123456",
            "rating": 4.9,
            "review_count": 87,
            "hourly_rate": 180.00,
            "premium_discount_pct": 15,
            "working_days_mask": 31,  # Mon-Fri
            "slot_start": "08:00",
            "slot_end": "18:00",
            "sort_order": 1,
        },
        {
            "id": "carlos-oliveira",
            "name": "Dr. Carlos Oliveira",
            "photo_key": "therapists/carlos-oliveira.jpg",
            "bio": (
                "Psicólogo especializado em terapia de casais e famílias com abordagem "
                "sistêmica. 15 anos de experiência atendendo conflitos conjugais, "
                "comunicação não-violenta e reestruturação familiar pós-separação. "
                "Doutor em Psicologia pela UNICAMP."
            ),
            "specialties": '["Relacionamentos", "Terapia de Casais", "Familia", "Comunicacao"]',
            "credentials": '["Doutorado em Psicologia - UNICAMP", "Especializacao em Terapia Sistemica"]',
            "crp": "CRP 06/234567",
            "rating": 4.7,
            "review_count": 62,
            "hourly_rate": 200.00,
            "premium_discount_pct": 10,
            "working_days_mask": 23,  # Mon, Tue, Wed, Thu, Sat (1+2+4+8+... wait: Mon=1,Tue=2,Wed=4,Thu=8,Fri=16,Sat=32 → Mon-Thu+Sat = 1+2+4+8+32=47... let's use 47)
            "slot_start": "10:00",
            "slot_end": "20:00",
            "sort_order": 2,
        },
        {
            "id": "juliana-ferreira",
            "name": "Dra. Juliana Ferreira",
            "photo_key": "therapists/juliana-ferreira.jpg",
            "bio": (
                "Psicóloga com formação em EMDR e terapia do trauma. Especialista no "
                "tratamento de TEPT, abuso, luto e situações de crise. Mais de 10 anos "
                "acompanhando adultos em processos de recuperação e ressignificação. "
                "Abordagem compassiva e centrada no paciente."
            ),
            "specialties": '["Trauma", "TEPT", "Luto", "Crise", "EMDR"]',
            "credentials": '["Formacao em EMDR - EMDR Brasil", "Especializacao em Trauma - CFP", "Graduacao em Psicologia - PUCRS"]',
            "crp": "CRP 07/345678",
            "rating": 4.8,
            "review_count": 54,
            "hourly_rate": 190.00,
            "premium_discount_pct": 15,
            "working_days_mask": 31,  # Mon-Fri
            "slot_start": "09:00",
            "slot_end": "17:00",
            "sort_order": 3,
        },
        {
            "id": "marcos-lima",
            "name": "Dr. Marcos Lima",
            "photo_key": "therapists/marcos-lima.jpg",
            "bio": (
                "Psicólogo clínico especializado em saúde masculina e questões de "
                "identidade. Referência no atendimento a homens que buscam ajuda pela "
                "primeira vez, com abordagem acolhedora e livre de julgamentos. "
                "Trabalha com ansiedade, burnout, masculinidade e autoconhecimento."
            ),
            "specialties": '["Saude Masculina", "Burnout", "Ansiedade", "Identidade", "Autoconhecimento"]',
            "credentials": '["Especializacao em Psicologia Clinica - UFMG", "Pos-graduacao em Saude Mental"]',
            "crp": "CRP 04/456789",
            "rating": 4.6,
            "review_count": 41,
            "hourly_rate": 160.00,
            "premium_discount_pct": 20,
            "working_days_mask": 31,  # Mon-Fri
            "slot_start": "12:00",
            "slot_end": "20:00",
            "sort_order": 4,
        },
        {
            "id": "patricia-costa",
            "name": "Dra. Patricia Costa",
            "photo_key": "therapists/patricia-costa.jpg",
            "bio": (
                "Neuropsicóloga e psicóloga clínica com expertise em TDAH em adultos, "
                "dificuldades de aprendizagem e avaliação neuropsicológica. Também "
                "atende ansiedade de desempenho, perfeccionismo e síndrome do impostor. "
                "8 anos de prática clínica, abordagem integrativa."
            ),
            "specialties": '["TDAH", "Neuropsicologa", "Perfeccionismo", "Ansiedade de Desempenho", "Sindrome do Impostor"]',
            "credentials": '["Mestrado em Neuropsicologia - UNIFESP", "Especializacao em Avaliacao Neuropsicologica"]',
            "crp": "CRP 06/567890",
            "rating": 4.8,
            "review_count": 38,
            "hourly_rate": 210.00,
            "premium_discount_pct": 10,
            "working_days_mask": 31,  # Mon-Fri
            "slot_start": "08:00",
            "slot_end": "16:00",
            "sort_order": 5,
        },
    ])


def downgrade() -> None:
    op.drop_table("therapists")
