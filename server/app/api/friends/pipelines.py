from bson import ObjectId


def search_user_by_full_name(name: str, user_id: ObjectId) -> list:
    return [
        {
            "$match": {"full_name": {"$regex": name, "$options": "i"}},
        },
        {
            "$lookup": {
                "from": "user_auth",
                "localField": "auth_id",
                "foreignField": "_id",
                "as": "user",
            }
        },
        {
            "$addFields": {
                "username": {"$arrayElemAt": ["$user.username", 0]},
                "id": {"$arrayElemAt": ["$user._id", 0]},
            }
        },
        {
            "$lookup": {
                "from": "friend_request",
                "let": {"userId": "$auth_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$or": [
                                    {
                                        "$and": [
                                            {"$eq": ["$sender_id", "$$userId"]},
                                            {
                                                "$eq": [
                                                    "$receiver_id",
                                                    user_id,
                                                ]
                                            },
                                        ]
                                    },
                                    {
                                        "$and": [
                                            {"$eq": ["$receiver_id", "$$userId"]},
                                            {
                                                "$eq": [
                                                    "$sender_id",
                                                    user_id,
                                                ]
                                            },
                                        ]
                                    },
                                ]
                            }
                        }
                    },
                    {"$limit": 1},
                ],
                "as": "friendship",
            }
        },
        {
            "$addFields": {
                "friend_status": {
                    "$ifNull": [{"$arrayElemAt": ["$friendship.status", 0]}, None]
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "auth_id": 0,
                "friendship": 0,
                "user": 0,
                "created_at": 0,
            }
        },
    ]
