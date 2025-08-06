from pydantic import BaseModel


class OnlineStatus(BaseModel):
    user_id: str
    status: str
