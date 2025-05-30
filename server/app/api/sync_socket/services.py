from typing import Optional, List
from bson import ObjectId
import logging
from datetime import datetime
from pymongo import ReturnDocument
from app.core.db import AsyncDatabase
from app.core.schemas import (
    CallRecord,
    CallType,
    CallStatus,
    Call,
    CallParticipant,
    WebRTCOffer,
    WebRTCAnswer,
    CallEndedPayLoad,
    CallStatusUpdate,
)

logger = logging.getLogger()


async def create_call(
    call_offer: WebRTCOffer, call_status: CallStatus, db: AsyncDatabase
) -> CallStatusUpdate:
    """
    Creates a new call document and associated call participants in the database.

    This function handles:
    - Creating a new call with the provided offer and status.
    - Inserting the caller and callee as participants in the call.
    - Returning a CallStatusUpdate object indicating the newly created call.

    Args:
    call_offer (WebRTCOffer): Contains sender ID, receiver ID, and video/audio preference.
    call_status (CallStatus): The initial status of the call (e.g., "initiated").
    db (AsyncDatabase): Asynchronous database client instance (e.g., Motor).

    Returns:
    CallStatusUpdate: Object containing the call ID, timestamp, status, and update type.
    """

    call = Call(
        initiator_id=ObjectId(call_offer.sender_id),
        call_type=CallType.VIDEO if call_offer.video else CallType.AUDIO,
        participants=[ObjectId(call_offer.sender_id), ObjectId(call_offer.receiver_id)],
        status=call_status,
    )
    # Insert the Call document into the database
    call_response = await db.call.insert_one(call.model_dump(exclude={"id"}))

    participant_callee = CallParticipant(
        call_id=call_response.inserted_id,
        user_id=ObjectId(call_offer.receiver_id),
        invited_by=ObjectId(call_offer.sender_id),
        joined_at=None,
        left_at=None,
        status="invited",
    )
    participant_caller = CallParticipant(
        call_id=call_response.inserted_id,
        user_id=ObjectId(call_offer.sender_id),
        invited_by=ObjectId(call_offer.sender_id),
        joined_at=None,
        left_at=None,
        status="joined",
    )

    # Insert both CallParticipant documents into the database
    await db.call_participant.insert_one(participant_callee.model_dump(exclude={"id"}))
    await db.call_participant.insert_one(participant_caller.model_dump(exclude={"id"}))

    return CallStatusUpdate(
        type="status_update",
        call_id=call_response.inserted_id,
        timestamp=call.initiated_at,
        status=call_status,
    )


async def process_call_reception(
    payload: WebRTCAnswer, db: AsyncDatabase
) -> CallStatusUpdate:
    """
    Handles the reception of a WebRTC call answer and updates the call status.

    This function:
    - Updates the call status to 'ACCEPTED' in the call collection.
    - Marks the responding user (callee) as 'joined' in the call participants.

    Args:
    payload (WebRTCAnswer): Contains the call ID, sender (callee) ID, and timestamp of joining.
    db (AsyncDatabase): Asynchronous database instance for updating call and participant records.

    Returns:
    CallStatusUpdate: Object reflecting the new status of the call (ACCEPTED) and a timestamp.
    """

    # Update the call document's status to 'ACCEPTED'
    await db.call.find_one_and_update(
        {"_id": payload.call_id},
        {
            "$set": {
                "status": CallStatus.ACCEPTED.value,
                "started_at": payload.timestamp,
            }
        },
    )

    # Update the participant document for the sender (callee) to mark them as joined
    await db.call_participant.find_one_and_update(
        {"call_id": payload.call_id, "user_id": payload.sender_id},
        {"$set": {"status": "joined", "joined_at": payload.timestamp}},
    )

    return CallStatusUpdate(
        type="status_update",
        call_id=payload.call_id,
        status=CallStatus.ACCEPTED,
        timestamp=payload.timestamp,
    )


async def process_call_end(
    user_id: ObjectId, payload: CallEndedPayLoad, db: AsyncDatabase
) -> Optional[ObjectId]:
    """
    Ends an ongoing call and updates call and participant records accordingly.

    This function:
    - Sets the `ended_at` and `ended_by` fields in the call document.
    - Updates all participants to set their `left_at` timestamp.

    Args:
    user_id (ObjectId): The ID of the user who ended the call.
    payload (CallEndedPayLoad): Contains the call ID and the timestamp of when the call ended.
    db (AsyncDatabase): Asynchronous database instance for interacting with call data.

    Returns:
    Optional[ObjectId]: The user ID of the other participant, or `None` if the call was already ended.
    """

    update_dict = {
        "$set": {
            "ended_at": payload.ended_at,
            "ended_by": user_id,
        }
    }
    if payload.reason == "rejected":
        update_dict["$set"]["status"] = CallStatus.REJECTED.value
    if payload.reason in ["busy", "missed", "timeout"]:
        update_dict["$set"]["status"] = CallStatus.MISSED.value

    # Try to mark the call as ended (only if it hasn't been ended yet)
    call_response = await db.call.find_one_and_update(
        {"_id": payload.call_id, "ended_at": None},
        update_dict,
        return_document=ReturnDocument.AFTER,
    )

    if not call_response:
        return None

    # Update all participants to set their `left_at` timestamp
    await db.call_participant.update_many(
        {
            "call_id": payload.call_id,
        },
        {"$set": {"left_at": payload.ended_at}},
    )

    # Find the other participant (not the one who ended the call)
    participant = await db.call_participant.find_one(
        {"call_id": payload.call_id, "user_id": {"$ne": user_id}}
    )

    if participant is None:
        raise ValueError("No other participant found in the call.")

    return participant["user_id"]


# db.call.aggregate([{$match: {"_id": ObjectId('683158a427ac4b47fae57e3d')}},{$lookup:{from:"call_participant",localField:"_id",foreignField:"call_id",as:"call_participants"}},{$addFields: {call_participants: {$filter: {input: "$call_participants",as: "participant",cond: {$ne: ["$$participant.user_id", "$initiator_id"]}}}}},{$project: {call_id: "$_id", initiated_at: 1, caller_id:{ $arrayElemAt: ["$call_participants.user_id",0]}}}])
# async def get_call_record(call_id: ObjectId, db: AsyncDatabase) -> Optional[CallRecord]:
#     """
#     Fetch a call record by its ID along with caller and callee info.
#
#     Args:
#         call_id (ObjectId): The MongoDB ObjectId of the call to fetch.
#         db (AsyncDatabase): Motor async database instance.
#
#     Returns:
#         Optional[CallRecord]: Parsed CallRecord model instance if found, else None.
#     """
#
#     pipeline = [
#         {"$match": {"_id": call_id}},
#         {
#             "$lookup": {
#                 "from": "call_participant",
#                 "localField": "_id",
#                 "foreignField": "call_id",
#                 "as": "call_participants",
#             }
#         },
#         {
#             "$addFields": {
#                 "call_participants": {
#                     "$filter": {
#                         "input": "$call_participants",
#                         "as": "participant",
#                         "cond": {"$ne": ["$$participant.user_id", "$initiator_id"]},
#                     }
#                 }
#             }
#         },
#         {
#             "$project": {
#                 "call_id": "$_id",
#                 "initiated_at": 1,
#                 "callee_id": {"$arrayElemAt": ["$call_participants.user_id", 0]},
#                 "caller_id": "$initiator_id",
#                 "ended_at": 1,
#                 "status": 1,
#             }
#         },
#     ]
#
#     cursor = db.call.aggregate(pipeline)
#     result_list = await cursor.to_list(length=1)
#
#     return CallRecord.model_validate(result_list[0]) if result_list else None


async def get_call_record(call_id: ObjectId, db: AsyncDatabase) -> Optional[CallRecord]:
    """
    Fetch a call record by its ID along with caller and callee info.

    Args:
        call_id (ObjectId): The MongoDB ObjectId of the call to fetch.
        db (AsyncDatabase): Motor async database instance.

    Returns:
        Optional[CallRecord]: Parsed CallRecord model instance if found, else None.
    """

    # Attempt to find the call record in the database
    record_response = await db.call.find_one({"_id": call_id})

    # Return None if no reocrd found.
    if not record_response:
        return None

    # Format the record to CallRecord
    call_record = CallRecord(
        call_id=record_response["_id"],
        caller_id=record_response["initiator_id"],
        callee_id=next(
            val
            for val in record_response["participants"]
            if val != record_response["initiator_id"]
        ),
        call_type=record_response["call_type"],
        status=record_response["status"],
        initiated_at=record_response["initiated_at"],
        started_at=record_response["started_at"],
        ended_at=record_response["ended_at"],
    )
    return call_record


async def list_call_record(
    date_after: Optional[datetime], user_id: ObjectId, db: AsyncDatabase
) -> List[CallRecord]:
    """
    Fetch a call record by its after given 'date_after' else it will return last 50 call records.

    Args:
        date_after(Optional[datetime]): The timestamp after which it will return call records.
        user_id (ObjectId): User Id for whom the call record will be fetched.
        db (AsyncDatabase): Motor async database instance.

    Returns:
        List[CallRecord]]: List of CallRecord.
    """

    # Define an aggregation pipeline to fetch and format call records
    pipeline = [
        {
            "$match": {
                "participants": {"$all": [user_id]},
            }
        },
        {"$sort": {"ended_at": -1}},
        {
            "$project": {
                "call_id": "$_id",
                "initiated_at": 1,
                "started_at": 1,
                "callee_id": {
                    "$first": {
                        "$filter": {
                            "input": "$participants",
                            "as": "p",
                            "cond": {"$ne": ["$$p", "$initiator_id"]},
                        }
                    }
                },
                "caller_id": "$initiator_id",
                "call_type": 1,
                "ended_at": 1,
                "status": 1,
            }
        },
    ]

    # If a date filter is provided, only include calls ended after that date
    if date_after:
        pipeline[0]["$match"]["ended_at"] = {"$gt": date_after}

    # Execute the aggregation and retrieve up to 50 call records
    cursor = db.call.aggregate(pipeline)
    raw_record = await cursor.to_list(length=50)

    # Validate and convert raw DB documents into Pydantic CallRecord objects
    call_records = [CallRecord.model_validate(data) for data in raw_record]

    return call_records
