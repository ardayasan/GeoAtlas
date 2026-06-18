from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class GroupRegion(BaseModel):
    id: Optional[int] = None
    group_id: int
    region_type: str
    region_code: str
    region_name: Optional[str] = None


class Group(BaseModel):
    id: Optional[int] = None
    name: str
    color: str
    created_at: Optional[datetime] = None
    regions: List[GroupRegion] = []
    total_population: Optional[int] = None
