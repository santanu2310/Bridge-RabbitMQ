from bson import ObjectId


def search_user_by_name(name: str, user_id: ObjectId) -> list:
    return [
        {
            "$lookup": {
                "from": "user_auth",
                "localField": "auth_id",
                "foreignField": "_id",
                "as": "auth_details",
            }
        },
        {"$unwind": "$auth_details"},
        {
            "$match": {
                "$or": [
                    {"full_name": {"$regex": name, "$options": "i"}},
                    {"auth_details.username": {"$regex": name, "$options": "i"}},
                ]
            }
        },
        {
            "$addFields": {
                "username": "$auth_details.username",
                "id": "$auth_details._id",
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
                "auth_details": 0,
            }
        },
    ]
