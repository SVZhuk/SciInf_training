"""create samples table

Revision ID: 527032f6d738
Revises:
Create Date: 2026-09-30 14:38:19.851119

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.schemas import Organism

# revision identifiers, used by Alembic.
revision: str = "527032f6d738"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "organism",
            sa.Enum(
                Organism,
                native_enum=False,
                length=50,
                values_callable=lambda enum_cls: [member.value for member in enum_cls],
            ),
            nullable=False,
        ),
        sa.Column("sequence", sa.String(length=10_000), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_samples")),
        sa.UniqueConstraint("name", name=op.f("uq_samples_name")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("samples")
