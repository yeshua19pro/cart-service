"""
Inventory Service for handling Stock operations such as restock and out of stock.
"""
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from passlib.context import CryptContext # Library for hashing passwords
from jose import jwt # jose. (web tokens)
from datetime import datetime, timezone, timedelta, date # Time management
from sqlalchemy import update, and_ , func # For update queries
from sqlalchemy.ext.asyncio import AsyncSession # Async session for postgress
from sqlalchemy.future import select # Select for queries
from typing import Optional # Similar to 'Option T' in rust
from core.config import settings
from db.models.models import Cart # User table structure
from uuid import UUID, uuid4 # UUID for tables ids
from utils.time import utc_now, utc_return_time_cast
from dateutil import parser
import random
import httpx
from decimal import Decimal
from sqlalchemy.orm.attributes import flag_modified
# Context for hashing passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") # bycrypt algorithm based in SHA 256

async def validate_book_exists(book_id: str):
    response = ""
    params = {
        "x_internal_action_token": settings.INTERNAL_ACTION_TOKEN
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.CATALOG_SERVICE_URL}/catalog/book-exists/{book_id}",
            params=params
        )

    return response.status_code == 200

async def recalc_cart_total(cart, memory_cart):
    cart.total_price = sum(
        (item.get("price_per_unit", 0) * item.get("quantity", 0)) for item in memory_cart.values()
    )
    cart.cart_items = memory_cart
    flag_modified(cart, "cart_items")


async def get_book_data(book_id: str):
    response = ""
    params = {
        "x_internal_action_token": settings.INTERNAL_ACTION_TOKEN
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.INVENTORY_SERVICE_URL}/inventory/check-book-coms/{book_id}",
            params=params
        )

    return response.json() or None


def create_access_token(data: dict, expires_minutes: int = 60) -> str: # JWT creation, dictionaries, hashmaps
    """Create a JWT access token for a user."""
    to_encode = data.copy() # deep copy of data to encode
    now = utc_now()
    expires = now + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expires, "iat": now}) # expiration and issued at
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM) # token creation
    return encoded_jwt # token return

async def retrive_cart_from_user(db: AsyncSession, user_id: UUID):
    """Register a new user in the database."""
    existence_check = await db.execute(select(Cart).where(Cart.user_id == user_id)) # SELECT * FROM Book WHERE id =: book_id
    cart = existence_check.scalar_one_or_none() # Check if a Book with this id exists and return None
    
    if not cart:
        cart = Cart(
            user_id = user_id,
            cart_items = {},
            total_price = 0
        )
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
        return cart
    
    return cart
