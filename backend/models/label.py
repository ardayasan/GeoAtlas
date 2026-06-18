from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CustomLabel(BaseModel):
    id: Optional[int] = None
    name: str
    latitude: float
    longitude: float
    color: str = "#FF5733"
    description: Optional[str] = None
    icon_type: str = "pin"
    source: str = "manuel"
    created_at: Optional[datetime] = None
