"""Remove the redundant username user identifier.

Downgrade recreates only a nullable compatibility column. Original username
values are data lost by upgrade and can be recovered only from a backup.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260711_0002"
down_revision = "20260710_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    duplicate = connection.execute(
        sa.text(
            """
            SELECT lower(btrim(email)) AS normalized_email
            FROM users
            GROUP BY lower(btrim(email))
            HAVING count(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError("Невозможно перейти на email-only: обнаружены дубликаты нормализованного email")

    op.drop_constraint("users_username_key", "users", type_="unique")
    op.drop_column("users", "username")


def downgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=32), nullable=True))
    op.create_unique_constraint("users_username_key", "users", ["username"])
