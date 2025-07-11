from enum import Enum
from pydantic import BaseModel
from app.core.schemas import PyObjectId


class Friends_Status(str, Enum):
    pending = "pending"
    rejected = "rejected"


class UserBrief(BaseModel):
    id: PyObjectId
    username: str
    full_name: str
    bio: str | None = None
    profile_picture: str | None = None
    friend_status: Friends_Status | None
