from .base import Entity, TimestampMixin


class Role(Entity, TimestampMixin):
    name: str
