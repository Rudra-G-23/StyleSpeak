"""FastAPI application for the local StyleSpeak shopping experience."""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from . import conversation, repository
from .config import get_settings
from .database import SessionLocal, get_session
from .models import Product
from .retrieval import search as run_search
from .schemas import (
    CartAddRequest,
    CartLineOut,
    CartOut,
    CartUpdateRequest,
    ChatRequest,
    ChatResponse,
    ProductOut,
    SearchFilters,
    SearchRequest,
    SearchResponse,
)
from .voice import TranscriptionUnavailable, transcribe

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    session = SessionLocal()
    try:
        repository.create_schema(session)
    finally:
        session.close()
    yield


app = FastAPI(title="StyleSpeak API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-StyleSpeak-Session"],
)


def session_id(x_stylespeak_session: str | None = Header(default=None)) -> str:
    if x_stylespeak_session and len(x_stylespeak_session) <= 80:
        return x_stylespeak_session
    return uuid.uuid4().hex


def serialize(product: Product) -> ProductOut:
    return ProductOut(
        sku=product.sku,
        name=product.name,
        brand=product.brand,
        category=product.category,
        subcategory=product.subcategory,
        gender=product.gender,
        color=product.color,
        sizes=json.loads(product.sizes_json),
        price=product.price,
        original_price=product.original_price,
        currency=product.currency,
        image_url=f"/api/products/{product.sku}/image",
    )


def serialize_cart(session: Session, sid: str) -> CartOut:
    items = repository.cart_items(session, sid)
    lines = [
        CartLineOut(
            sku=item.sku,
            size=item.size,
            quantity=item.quantity,
            product=serialize(item.product),
            line_total=round(item.product.price * item.quantity, 2),
        )
        for item in items
    ]
    return CartOut(
        items=lines,
        item_count=sum(line.quantity for line in lines),
        subtotal=round(sum(line.line_total for line in lines), 2),
    )


@app.get("/api/health")
def health(session: Session = Depends(get_session)) -> dict:
    return {"status": "ok", "products": repository.count_filtered(session, SearchFilters())}


@app.get("/api/products", response_model=list[ProductOut])
def products(limit: int = 24, session: Session = Depends(get_session)) -> list[ProductOut]:
    return [
        serialize(product) for product in repository.list_products(session, min(max(limit, 1), 48))
    ]


@app.get("/api/products/{sku}", response_model=ProductOut)
def product(sku: str, session: Session = Depends(get_session)) -> ProductOut:
    item = repository.get_product(session, sku)
    if item is None:
        raise HTTPException(404, "Product not found")
    return serialize(item)


@app.get("/api/products/{sku}/image")
def image(sku: str, session: Session = Depends(get_session)) -> FileResponse:
    item = repository.get_product(session, sku)
    path = Path(item.image_path) if item else None
    if item is None or path is None or not path.is_file():
        raise HTTPException(404, "Product image not found")
    return FileResponse(path)


@app.get("/api/products/{sku}/variants", response_model=list[ProductOut])
def variants(sku: str, session: Session = Depends(get_session)) -> list[ProductOut]:
    item = repository.get_product(session, sku)
    if item is None:
        raise HTTPException(404, "Product not found")
    related = (
        session.query(Product)
        .filter(Product.family_key == item.family_key)
        .order_by(Product.price)
        .all()
    )
    return [serialize(product) for product in related]


@app.get("/api/categories")
def categories() -> list[dict[str, str]]:
    return [{"id": "pants", "name": "Men's pants"}]


@app.get("/api/filters")
def filters(session: Session = Depends(get_session)) -> dict:
    products = repository.list_products(session, 10000)
    return {
        "colors": sorted({product.color for product in products if product.color}),
        "subcategories": sorted(
            {product.subcategory for product in products if product.subcategory}
        ),
        "sizes": sorted({size for product in products for size in json.loads(product.sizes_json)}),
    }


@app.post("/api/search", response_model=SearchResponse)
def search(payload: SearchRequest, session: Session = Depends(get_session)) -> SearchResponse:
    interpreted, products = run_search(session, payload)
    return SearchResponse(
        interpreted_filters=interpreted,
        products=[serialize(product) for product in products],
        total=repository.count_filtered(session, interpreted),
        message=None if products else "No products match those filters.",
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest, sid: str = Depends(session_id), session: Session = Depends(get_session)
) -> ChatResponse:
    action, message, products, selected = conversation.handle_message(session, sid, payload.message)
    cart = serialize_cart(session, sid)
    return ChatResponse(
        action=action,
        message=message,
        products=[serialize(product) for product in products],
        selected_sku=selected,
        cart_count=cart.item_count,
    )


@app.post("/api/voice/transcribe")
async def voice(audio: UploadFile = File(...)) -> dict[str, str]:
    try:
        return {"transcript": transcribe(await audio.read())}
    except (ValueError, TranscriptionUnavailable) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/cart", response_model=CartOut)
def get_cart(sid: str = Depends(session_id), session: Session = Depends(get_session)) -> CartOut:
    return serialize_cart(session, sid)


@app.post("/api/cart/items", response_model=CartOut, status_code=201)
def add_cart(
    payload: CartAddRequest, sid: str = Depends(session_id), session: Session = Depends(get_session)
) -> CartOut:
    try:
        repository.add_cart_item(session, sid, payload.sku, payload.size, payload.quantity)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return serialize_cart(session, sid)


@app.patch("/api/cart/items/{sku}", response_model=CartOut)
def update_cart(
    sku: str,
    payload: CartUpdateRequest,
    sid: str = Depends(session_id),
    session: Session = Depends(get_session),
) -> CartOut:
    if not repository.update_cart_item(session, sid, sku, payload.quantity):
        raise HTTPException(404, "Cart item not found")
    return serialize_cart(session, sid)


@app.delete("/api/cart/items/{sku}", response_model=CartOut)
def remove_cart(
    sku: str, sid: str = Depends(session_id), session: Session = Depends(get_session)
) -> CartOut:
    if not repository.delete_cart_item(session, sid, sku):
        raise HTTPException(404, "Cart item not found")
    return serialize_cart(session, sid)
