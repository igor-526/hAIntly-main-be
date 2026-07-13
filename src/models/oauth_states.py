from sqlalchemy import Column, DateTime, String, Table

from utils.basemodel import metadata

oauth_state_nonces = Table(
    "oauth_state_nonces",
    metadata,
    Column("nonce", String(36), primary_key=True),
    Column("expires_at", DateTime(timezone=True), nullable=False, index=True),
)
