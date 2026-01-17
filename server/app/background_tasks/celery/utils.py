from bson import ObjectId
from app.core.db import SyncDatabase


def list_friends_id(user_id: ObjectId, db: SyncDatabase) -> list[ObjectId]:
    friends = db.friends.find(
        {"user_id": user_id},
        projection={"friend_id": 1, "_id": 0},
    )
    friend_ids = [friend["friend_id"] for friend in friends]
    return friend_ids
