"""Initial schema - document, pack, chunk, collection, configuration, etc.

Revision ID: 001
Revises:
Create Date: 2025-02-19

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "role",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
    )
    op.create_index("ix_role_name", "role", ["name"], unique=True)

    # Seed roles - get IDs first
    op.create_table(
        "role_permission",
        sa.Column("role_id", sa.UUID(), sa.ForeignKey("role.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("action", sa.String(50), primary_key=True),
    )

    op.create_table(
        "configuration",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("chunking_strategy", sa.String(50), nullable=False),
        sa.Column("embedding_model", sa.String(255), nullable=False),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False),
        sa.Column("chunk_size", sa.Integer(), nullable=False),
        sa.Column("chunk_overlap", sa.Integer(), nullable=False),
    )

    op.create_table(
        "document",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_document_source_hash", "document", ["source_hash"])

    op.create_table(
        "collection",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("configuration_id", sa.UUID(), sa.ForeignKey("configuration.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "pack",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("document_id", sa.UUID(), sa.ForeignKey("document.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "chunk",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("pack_id", sa.UUID(), sa.ForeignKey("pack.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
    )

    op.create_table(
        "property",
        sa.Column("document_id", sa.UUID(), sa.ForeignKey("document.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("key", sa.String(255), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("property_type", sa.String(50), nullable=False),
    )

    op.create_table(
        "permission",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("collection_id", sa.UUID(), sa.ForeignKey("collection.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("role_id", sa.UUID(), sa.ForeignKey("role.id"), nullable=False),
        sa.Column("actions_override", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=True),
    )
    op.create_index("ix_permission_collection_subject", "permission", ["collection_id", "subject"], unique=True)

    op.create_table(
        "pack_collection",
        sa.Column("pack_id", sa.UUID(), sa.ForeignKey("pack.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("collection_id", sa.UUID(), sa.ForeignKey("collection.id", ondelete="CASCADE"), primary_key=True),
    )

    op.execute("""
        INSERT INTO role (id, name, description) VALUES
        (gen_random_uuid(), 'viewer', 'Read-only access'),
        (gen_random_uuid(), 'editor', 'Read and write access'),
        (gen_random_uuid(), 'admin', 'Full access including migrate')
    """)
    op.execute("""
        INSERT INTO role_permission (role_id, action)
        SELECT id, 'read' FROM role WHERE name = 'viewer'
    """)
    op.execute("""
        INSERT INTO role_permission (role_id, action)
        SELECT id, unnest(ARRAY['read','write']) FROM role WHERE name = 'editor'
    """)
    op.execute("""
        INSERT INTO role_permission (role_id, action)
        SELECT id, unnest(ARRAY['read','write','delete','admin','migrate']) FROM role WHERE name = 'admin'
    """)


def downgrade() -> None:
    op.drop_table("pack_collection")
    op.drop_table("permission")
    op.drop_table("property")
    op.drop_table("chunk")
    op.drop_table("pack")
    op.drop_table("collection")
    op.drop_table("document")
    op.drop_table("configuration")
    op.drop_table("role_permission")
    op.drop_table("role")
    op.execute("DROP EXTENSION IF EXISTS vector")
