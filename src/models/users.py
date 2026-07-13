from sqlalchemy import Column, DateTime, Integer, String, Table, func, text
from sqlalchemy.dialects.postgresql import UUID

from utils.basemodel import metadata

users = Table(
    "users",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("email", String(255), nullable=False, unique=True),
    Column("password", String(255), nullable=False),
    Column("session_version", Integer, nullable=False, server_default=text("1")),
    Column("active_hh_account_id", UUID(as_uuid=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=True, onupdate=func.now()),
)
