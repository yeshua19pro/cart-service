from fastapi import APIRouter, HTTPException, Depends, Request, status # Constructor for router, request for ip directions
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession # Engine for postgress async
from services.cart_service import retrive_cart_from_user, create_access_token, validate_book_exists, get_book_data, recalc_cart_total # Auxiliar functions for routers
from core.security import validate_token, validate_internal_action_token

from db.session import get_session # Get async session for bd
from db.models.models import Cart # Structure of the table
from core.limiter import limiter
from sqlalchemy.future import select # Select for queries
from uuid import UUID , uuid4 # UUID for tables ids
from datetime import datetime, timedelta, timezone # Time management
import random 
from utils.time import utc_now, utc_return_time_cast # Router functions for lesser verbouse text


router = APIRouter(prefix="/cart", tags=["Cart"]) # All endpoints will start with /catalog and tagged as Catalogs


def parse_book_data(book_data: dict) -> dict:
    book = book_data.get("book", {})
    return {
        "book_name": book.get("book_name"),
        "author": book.get("author"),
        "price": book.get("price", 0),
        "stock": book.get("stock", 0),
    }


@router.get("/cart", status_code = status.HTTP_200_OK, include_in_schema=True) 
@limiter.limit("100/minute")
async def retrieve_cart_router (
    request: Request,
    token_data: dict = Depends(validate_token),
    db: AsyncSession = Depends(get_session) # Async session for bd
    ):
    """Endpoint to retrieve the whole cart of the user."""
 
    cart = await retrive_cart_from_user(db, UUID(token_data.get("sub")))
    
    
    
    if not cart:
        return JSONResponse(
            status_code = status.HTTP_404_NOT_FOUND,
            content={"detail":"Cart not found."}
        )
        
   

    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content={
            "cart_info": {
            "cart_items": cart.cart_items,
            "total_price": cart.total_price
            }}
    )
    
@router.post("/items/{book_id}", status_code = status.HTTP_200_OK, include_in_schema=True) 
@limiter.limit("100/minute")
async def add_item_router (
    book_id: str,
    request: Request,
    token_data: dict = Depends(validate_token),
    db: AsyncSession = Depends(get_session) # Async session for bd
    ):
    """Endpoint to add an item to the cart of the user."""

        
    cart = await retrive_cart_from_user(db, UUID(token_data.get("sub")))
    

    if not cart:
        return JSONResponse(
            status_code = status.HTTP_404_NOT_FOUND,
            content={"detail":"Cart not found."}
        )
    
    book_exist = await validate_book_exists(book_id)   
    
    
    
    if not book_exist:
        return JSONResponse(
            status_code = status.HTTP_404_NOT_FOUND,
            content={"detail":"Book not found."}
        )
    
    info  = parse_book_data(await get_book_data(book_id))
    
    if not info:
        return JSONResponse(
            status_code = status.HTTP_404_NOT_FOUND,
            content={"detail":"Book data could not be retrieved."}
        )
    
    price_per_unit = info.get("price")
    book_name = info.get("book_name")
    author = info.get("author")
    
    
    memory_cart = cart.cart_items or {}
    print(memory_cart, "INICIO")
    if book_id in memory_cart.keys():
        
        if info.get("stock", 0) < (memory_cart[book_id]["quantity"] + 1):
            return JSONResponse(
                status_code = status.HTTP_400_BAD_REQUEST,
                content={"detail":"Not enough stock available."}
            )
        memory_cart[book_id]["quantity"] = memory_cart[book_id]["quantity"] + 1
        memory_cart[book_id]["total_price"] = int(memory_cart[book_id]["quantity"]) * price_per_unit
    else:
        print( book_id, book_name, author, price_per_unit)
        memory_cart[str(book_id)] = {
            "book_name": book_name,
            "author": author,
            "quantity": 1,
            "price_per_unit": price_per_unit,
            "total_price": price_per_unit
        }
    print(memory_cart)
    await recalc_cart_total(cart, memory_cart)

    await db.commit()

    

    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content={
                 "cart_info": {
                    "cart_items": memory_cart,
                    "total_price": cart.total_price
                 }}
    )
    
@router.patch("/items/{book_id}", status_code = status.HTTP_200_OK, include_in_schema=True) 
@limiter.limit("100/minute")
async def reduce_item_router (
    book_id: str,
    request: Request,
    token_data: dict = Depends(validate_token),
    db: AsyncSession = Depends(get_session) # Async session for bd
    ):
    """Endpoint to add an item to the cart of the user."""

        
    cart = await retrive_cart_from_user(db, UUID(token_data.get("sub")))

        
    if not cart:
        return JSONResponse(
            status_code = status.HTTP_404_NOT_FOUND,
            content={"detail":"Cart not found."}
        )
    
    book_exist = await validate_book_exists(book_id)   
    
    
    
    if not book_exist:
        return JSONResponse(
            status_code = status.HTTP_404_NOT_FOUND,
            content={"detail":"Book not found."}
        )
    
    info  = parse_book_data( await get_book_data(book_id))
    
    if not info:
        return JSONResponse(
            status_code = status.HTTP_404_NOT_FOUND,
            content={"detail":"Book data could not be retrieved."}
        )
    
    price_per_unit = info.get("price")

    
    memory_cart = cart.cart_items or {}
    
    if book_id in memory_cart.keys():
        if memory_cart[book_id]["quantity"] <= 1:
            del memory_cart[book_id]
        else:
            memory_cart[book_id]["quantity"] -= 1
            memory_cart[book_id]["total_price"] = int(memory_cart[book_id]["quantity"]) * price_per_unit

    await recalc_cart_total(cart, memory_cart)

    await db.commit()

    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content={
                 "cart_info": {
                    "cart_items": memory_cart,
                    "total_price": cart.total_price
                 }}
    )
    
    
    
@router.delete("/items/{book_id}", status_code = status.HTTP_200_OK, include_in_schema=True) 
@limiter.limit("100/minute")
async def remove_item_router (
    book_id: str,
    request: Request,
    token_data: dict = Depends(validate_token),
    db: AsyncSession = Depends(get_session) # Async session for bd
    ):
    """Endpoint to remove an item to the cart of the user."""

        
    cart = await retrive_cart_from_user(db, UUID(token_data.get("sub")))
    

        
    if not cart:
        return JSONResponse(
            status_code = status.HTTP_404_NOT_FOUND,
            content={"detail":"Cart not found."}
        )
    
    book_exist = await validate_book_exists(book_id)   
    
    if not book_exist:
        return JSONResponse(
            status_code = status.HTTP_404_NOT_FOUND,
            content={"detail":"Book not found."}
        )
    
    memory_cart = cart.cart_items or {}
    
    if book_id in memory_cart.keys():
        del memory_cart[book_id]
    
    await recalc_cart_total(cart, memory_cart)

    await db.commit()

    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content={
                 "cart_info": {
                    "cart_items": memory_cart,
                    "total_price": cart.total_price
                 }}
    )
    
    
@router.post("/validate-checkout", status_code = status.HTTP_200_OK, include_in_schema=True) 
@limiter.limit("10/minute")
async def validate_checkout_router (
    request: Request,
    token_data: dict = Depends(validate_token),
    db: AsyncSession = Depends(get_session) # Async session for bd
    ):
    """Endpoint to remove an item to the cart of the user."""

        
    cart = await retrive_cart_from_user(db, UUID(token_data.get("sub")))
    
    token = create_access_token({
        "sub": token_data.get("sub"),
        "name": token_data.get("name"),
        "last_name": token_data.get("last_name", None),
        "role": token_data.get("role"), 
    })
        
    if not cart:
        return JSONResponse(
            status_code = status.HTTP_404_NOT_FOUND,
            content={"detail":"Cart not found."}
        )
    

    memory_cart = cart.cart_items or {}
    errors = []
    cart.total_price = 0
    for key in list(memory_cart.keys()):
        value = memory_cart[key]
        book_exists = await validate_book_exists(key)
        if not book_exists:
            errors.append(f"Book with id {key} does not exist.")
            del memory_cart[key]
            continue
        info = parse_book_data( await get_book_data(key))
        available_quantity = info.get("stock", 0)
        if available_quantity < 1:
            errors.append(f"Book with id {key} is out of stock.")
            del memory_cart[key]
            continue
        
        if value.get("quantity", 0) > available_quantity:
            errors.append(f"Book with id {key} has only {available_quantity} items available.")
            memory_cart[key]["quantity"] = available_quantity
            memory_cart[key]["total_price"] = available_quantity * info.get("price", 0)
            
    
    await recalc_cart_total(cart, memory_cart)


    await db.commit()

    if not memory_cart:
        return JSONResponse(
            status_code = status.HTTP_400_BAD_REQUEST,
            content={"detail":"No items available in cart for checkout.", "errors": errors}
        )

    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content={"access_token": token,
                 "token_type": "bearer", 
                 "cart_info": {
                    "cart_items": memory_cart,
                    "total_price": cart.total_price
                 },
                 "errors": errors}
    )