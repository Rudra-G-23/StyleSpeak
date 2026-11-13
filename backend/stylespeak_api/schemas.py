"""Pydantic request and response contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ProductOut(BaseModel):
    sku: str
    name: str
    brand: str
    category: str
    subcategory: str | None
    gender: str
    color: str | None
    sizes: list[str]
    price: float
    original_price: float | None
    currency: str
    image_url: str


class SearchFilters(BaseModel):
    gender: Literal["men", "women", "unisex"] | None = None
    category: str | None = None
    subcategory: str | None = None
    color: str | None = None
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    size: str | None = None
    brand: str | None = None

    @field_validator("category", "subcategory", "color", "brand", "size", mode="before")
    @classmethod
    def clean_strings(cls, value: str | None) -> str | None:
        return value.strip().lower() if isinstance(value, str) and value.strip() else None


class SearchRequest(BaseModel):
    query: str = Field(default="", max_length=300)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    limit: int = Field(default=12, ge=1, le=30)


class SearchResponse(BaseModel):
    interpreted_filters: SearchFilters
    products: list[ProductOut]
    total: int
    message: str | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=300)


class ChatResponse(BaseModel):
    message: str
    action: Literal["search", "select", "cart", "info"]
    products: list[ProductOut] = Field(default_factory=list)
    selected_sku: str | None = None
    cart_count: int | None = None


class CartAddRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=120)
    size: str | None = Field(default=None, max_length=30)
    quantity: int = Field(default=1, ge=1, le=10)


class CartUpdateRequest(BaseModel):
    quantity: int = Field(ge=0, le=10)


class CartLineOut(BaseModel):
    sku: str
    size: str | None
    quantity: int
    product: ProductOut
    line_total: float


class CartOut(BaseModel):
    items: list[CartLineOut]
    item_count: int
    subtotal: float
