"""add ownership to library records

Revision ID: a5c6188ba1cf
Revises: 9e28b168f42d
Create Date: 2026-09-10 14:35:30.712783

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a5c6188ba1cf"
down_revision: Union[str, Sequence[str], None] = "9e28b168f42d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Add ownership columns temporarily as nullable
    op.add_column(
        "books",
        sa.Column("owner_id", sa.Integer(), nullable=True),
    )

    op.add_column(
        "members",
        sa.Column("owner_id", sa.Integer(), nullable=True),
    )

    op.add_column(
        "lendings",
        sa.Column("owner_id", sa.Integer(), nullable=True),
    )

    # Get an existing user to own existing records.
    connection = op.get_bind()

    user_id = connection.execute(
        sa.text("SELECT id FROM users ORDER BY id LIMIT 1")
    ).scalar()

    if user_id is None:
        raise RuntimeError(
            "No users exist. Please register at least one user "
            "before running this migration."
        )

    # Assign existing records to the first registered user.
    connection.execute(
        sa.text("UPDATE books SET owner_id = :user_id"),
        {"user_id": user_id},
    )

    connection.execute(
        sa.text("UPDATE members SET owner_id = :user_id"),
        {"user_id": user_id},
    )

    connection.execute(
        sa.text("UPDATE lendings SET owner_id = :user_id"),
        {"user_id": user_id},
    )

    # Now make ownership mandatory.
    op.alter_column(
        "books",
        "owner_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.alter_column(
        "members",
        "owner_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.alter_column(
        "lendings",
        "owner_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # Add indexes.
    op.create_index(
        op.f("ix_books_owner_id"),
        "books",
        ["owner_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_members_owner_id"),
        "members",
        ["owner_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_lendings_owner_id"),
        "lendings",
        ["owner_id"],
        unique=False,
    )

    # Add foreign keys to users.id.
    op.create_foreign_key(
        "fk_books_owner_id_users",
        "books",
        "users",
        ["owner_id"],
        ["id"],
    )

    op.create_foreign_key(
        "fk_members_owner_id_users",
        "members",
        "users",
        ["owner_id"],
        ["id"],
    )

    op.create_foreign_key(
        "fk_lendings_owner_id_users",
        "lendings",
        "users",
        ["owner_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint(
        "fk_lendings_owner_id_users",
        "lendings",
        type_="foreignkey",
    )

    op.drop_constraint(
        "fk_members_owner_id_users",
        "members",
        type_="foreignkey",
    )

    op.drop_constraint(
        "fk_books_owner_id_users",
        "books",
        type_="foreignkey",
    )

    op.drop_index(
        op.f("ix_lendings_owner_id"),
        table_name="lendings",
    )

    op.drop_index(
        op.f("ix_members_owner_id"),
        table_name="members",
    )

    op.drop_index(
        op.f("ix_books_owner_id"),
        table_name="books",
    )

    op.drop_column("lendings", "owner_id")
    op.drop_column("members", "owner_id")
    op.drop_column("books", "owner_id")