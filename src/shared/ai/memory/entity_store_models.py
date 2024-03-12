from __future__ import annotations

from typing import List
from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import Table
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship

from pgvector.sqlalchemy import Vector



class Base(DeclarativeBase):
    pass


association_table = Table(
    "entity_mappings",
    Base.metadata,
    Column("entity_id", ForeignKey("entity.id"), primary_key=True),
    Column("entity_details_id", ForeignKey("entity_details.id"), primary_key=True),
)


class Entity(Base):
    __tablename__ = "entity"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_key: Mapped[str] = mapped_column(unique=True)
    date_created: Mapped[datetime] = mapped_column(default=datetime.now())
    embedding = Column(Vector(), nullable=True)

    details: Mapped[List[EntityDetails]] = relationship(
        secondary=association_table, back_populates="entities"
    )


class EntityDetails(Base):
    __tablename__ = "entity_details"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_value: Mapped[str] = mapped_column()
    date_created: Mapped[datetime] = mapped_column(default=datetime.now())
    date_updated: Mapped[datetime] = mapped_column(default=datetime.now())
    embedding = Column(Vector(), nullable=True)

    entities: Mapped[List[Entity]] = relationship(
        secondary=association_table, back_populates="details", viewonly=True
    )
