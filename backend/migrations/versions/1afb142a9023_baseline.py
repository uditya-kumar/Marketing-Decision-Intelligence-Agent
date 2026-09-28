"""baseline

Revision ID: 1afb142a9023
Revises:
Create Date: 2026-09-28 13:53:08.150312

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "1afb142a9023"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
