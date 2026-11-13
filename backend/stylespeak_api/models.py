"""SQLAlchemy catalog and cart storage models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(120), primary_key=True)
    family_key: Mapped[str] = mapped_column(String(300), index=True)
    name: Mapped[str] = mapped_column(String(500), index=True)
    brand: Mapped[str] = mapped_column(String(200), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    subcategory: Mapped[str | None] = mapped_column(String(80), index=True)
    gender: Mapped[str] = mapped_column(String(20), index=True)
    color: Mapped[str | None] = mapped_column(String(40), index=True)
    sizes_json: Mapped[str] = mapped_column(Text, default="[]")
    price: Mapped[float] = mapped_column(Float, index=True)
    original_price: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="EUR")
    image_path: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str] = mapped_column(Text)
    searchable_text: Mapped[str] = mapped_column(Text)


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    items: Mapped[list[CartItem]] = relationship(
        back_populates="cart", cascade="all, delete-orphan"
    )


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "sku", "size", name="uq_cart_item_variant"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), index=True)
    sku: Mapped[str] = mapped_column(ForeignKey("products.sku"), index=True)
    size: Mapped[str | None] = mapped_column(String(30))
    quantity: Mapped[int] = mapped_column(Integer)
    cart: Mapped[Cart] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()
