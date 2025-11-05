from sqlalchemy.orm import Mapped, mapped_column, relationship # object relational mapping, relationships between tables, tracking, consistency
from sqlalchemy import String, Integer, Float,  TIMESTAMP, func, ForeignKey,Index, CheckConstraint, Enum, Boolean  
from sqlalchemy.dialects.postgresql import UUID # specialized types for postgresql
import uuid 
from .base import Base # to know that all models inherit from base
from datetime import datetime 
from typing import Optional # Option 'T' in rust
from sqlalchemy.dialects.postgresql import JSONB # special type for amongodb like json
import enum
from typing import Dict, Any # dictionaries and any data type
from sqlalchemy.ext.mutable import MutableDict # to track changes in jsonb columns
from datetime import datetime, timedelta 

class Cart(Base):
    __tablename__ = "carts" # Table name in the database
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) # Primary key with UUID
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False) # Foreign key to users table
    cart_items: Mapped[Dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSONB), nullable=False) # Additional metadata in JSONB format
    total_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0) # Total price of items in the cart