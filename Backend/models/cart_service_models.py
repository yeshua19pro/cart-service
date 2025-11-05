"""
Models for cart service operations such as adding and removing or total price before checkout.
Is the way to update the cart
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime




class BookStockUpdateModel(BaseModel):
    """Model for updating book stock."""
    stock: int
    modify_type: str  # 'increment' or 'decrement'