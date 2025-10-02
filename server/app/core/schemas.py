from typing import Optional, List, Any, Callable, Literal, Union
from datetime import datetime, timezone
from bson import ObjectId
from typing_extensions import Annotated
from enum import Enum, unique
from typing_extensions import Self
from pydantic import BaseModel, Field, EmailStr, model_validator
from pydantic_core import core_schema


class _ObjectIdPydanticAnnotation:
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Callable[[Any], core_schema.CoreSchema],
    ) -> core_schema.CoreSchema:
        def validate_from_str(input_value: str) -> ObjectId:
            try:
                return ObjectId(input_value)
            except Exception as e:
                raise ValueError(f"Invalid ObjectId: {input_value}") from e

        return core_schema.union_schema(
            [
                # check if it's an instance first before doing any further work
                core_schema.is_instance_schema(ObjectId),
                core_schema.no_info_plain_validator_function(validate_from_str),
            ],
            serialization=core_schema.to_string_ser_schema(),
        )


PyObjectId = Annotated[ObjectId, _ObjectIdPydanticAnnotation]


@unique
class Friends_Status(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class Message_Status(str, Enum):
    send = "send"
    recieved = "received"
    seen = "seen"


class PacketType(str, Enum):
    ping = "ping"
    pong = "pong"
    message = "message"


class SyncMessageType(str, Enum):
    message_status = "message_status"
    online_status = "online_status"
    friend_update = "friend_update"
    friend_request = "friend_request"
    add_friend = "add_friend"
    profile_media = "profile_media"


class FileType(str, Enum):
    video = "video"
    image = "image"
    audio = "audio"
    document = "document"
    attachment = "attachment"


class MediaType(str, Enum):
    profile_picture = "profile_picture"
    banner_picture = "banner_picture"


class CallType(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"


class CallStatus(str, Enum):
    CALLING = "calling"
    RINGING = "ringing"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MISSED = "missed"


class UserAuth(BaseModel):
    id: Optional[PyObjectId] = Field(
        validation_alias="_id", default=None, serialization_alias="_id"
    )
    username: str
    email: EmailStr
    password: str
    hashing_salt: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserAuthOut(BaseModel):
    id: PyObjectId = Field(validation_alias="_id")
    username: str
    email: EmailStr
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserProfile(BaseModel):
    id: Optional[PyObjectId] = Field(
        validation_alias="_id", default=None, serialization_alias="_id"
    )
    auth_id: PyObjectId
    full_name: str
    bio: str | None = None
    profile_picture: str | None = None
    banner_picture: Optional[str] = None
    location: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserRegistration(BaseModel):
    username: str
    full_name: str
    email: EmailStr
    password: str

    @model_validator(mode="before")
    @classmethod
    def username_to_lower(cls, data: Any) -> Any:
        if isinstance(data, dict):
            username = data.get("username")
            if isinstance(username, str):
                data["username"] = username.lower()


class UserBrief(BaseModel):
    id: PyObjectId
    username: str
    full_name: str
    bio: str | None = None
    profile_picture: str | None = None


class UserOut(BaseModel):
    id: PyObjectId = Field(alias="_id", serialization_alias="id")
    username: str
    full_name: str | None = None
    email: EmailStr
    bio: str | None = None
    profile_picture: str | None = None
    banner_picture: Optional[str] = None
    location: str | None = None
    created_at: datetime | None = None


class UpdatableUserText(BaseModel):
    full_name: str | None = None
    bio: str | None = Field(max_length=100, default=None)
    location: str | None = None


class UpdatableUserImages(BaseModel):
    profile_picture_id: Optional[str] = None
    banner_picture_id: Optional[str] = None


class Friends(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: PyObjectId
    friend_id: PyObjectId
    update_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FriendRequestIn(BaseModel):
    username: str
    message: str | None = None


class FriendRequestDB(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    sender_id: PyObjectId
    receiver_id: PyObjectId
    message: str | None = None
    status: Friends_Status = Friends_Status.pending
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FriendRequestOut(BaseModel):
    id: str
    user: UserBrief
    message: str | None
    status: Friends_Status
    created_time: datetime


class Conversation(BaseModel):
    id: Optional[PyObjectId] = Field(
        alias="_id", default=None, serialization_alias="id"
    )
    participants: List[PyObjectId]
    start_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_message_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class FileInfo(BaseModel):
    type: FileType
    name: str
    key: Optional[str] = None
    temp_file_id: Optional[str] = None
    size: Optional[int] = None


class Message(BaseModel):
    id: Optional[PyObjectId] = Field(validation_alias="_id", default=None)
    temp_id: str | None = None  # exclued this while inserting to database
    conversation_id: PyObjectId
    sender_id: PyObjectId
    receiver_id: Optional[PyObjectId] = None
    message: str
    attachment: Optional[FileInfo] = None
    sending_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    received_time: Optional[datetime] = None
    seen_time: Optional[datetime] = None
    status: Message_Status = Message_Status.send


class MessageNoAlias(Message):
    id: Optional[PyObjectId] = Field(default=None, serialization_alias="_id")


class ConversationResponse(Conversation):
    messages: List[Message] | None = None


class FileData(BaseModel):
    temp_file_id: Optional[str] = None
    name: str


class MessageData(BaseModel):
    message: str
    receiver_id: str | None
    conversation_id: str | None
    temp_id: str | None
    attachment: Optional[FileData] = None


class MessagePacket(BaseModel):
    type: PacketType
    data: Optional[Union[Message, MessageData]] = None


class MessageEvent(BaseModel):
    message_id: str
    timestamp: datetime


class OnlineStatusMessage(BaseModel):
    type: Literal[SyncMessageType.online_status] = SyncMessageType.online_status
    user_id: str
    status: Literal["online", "offline"]


class MessageStatusUpdate(BaseModel):
    type: Literal[SyncMessageType.message_status] = SyncMessageType.message_status
    data: List[MessageEvent]
    status: Message_Status


class FriendUpdateMessage(BaseModel):
    type: Literal[SyncMessageType.friend_update] = SyncMessageType.friend_update
    id: PyObjectId
    full_name: Optional[str] = None
    bio: Optional[str] = None
    location: str | None = None
    profile_picture: Optional[str] = None
    banner_picture: Optional[str] = None


class FriendRequestMessage(BaseModel):
    type: Literal[SyncMessageType.friend_request] = SyncMessageType.friend_request
    id: str
    user: UserBrief
    message: Optional[str]
    status: Friends_Status
    created_time: datetime


class AddFriendMessage(BaseModel):
    type: Literal[SyncMessageType.add_friend] = SyncMessageType.add_friend
    freind_doc_id: PyObjectId


class ProfileMediaUpdate(BaseModel):
    type: Literal[SyncMessageType.profile_media] = SyncMessageType.profile_media
    user_id: PyObjectId
    media_type: MediaType
    media_id: str


class Call(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    initiator_id: PyObjectId
    participants: List[PyObjectId]  # List of participant's user ID
    call_type: CallType
    status: CallStatus
    initiated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    ended_by: Optional[PyObjectId] = None  # Should be a CallParticipant's ID


class CallParticipant(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    call_id: PyObjectId
    user_id: PyObjectId
    invited_by: PyObjectId
    joined_at: Optional[datetime]
    left_at: Optional[datetime]
    status: Literal["invited", "joined", "rejected"]


class CallRecord(BaseModel):
    call_id: PyObjectId
    caller_id: PyObjectId
    callee_id: PyObjectId
    call_type: CallType
    status: CallStatus
    initiated_at: datetime
    started_at: Optional[datetime]
    ended_at: datetime


class CallStatusUpdate(BaseModel):
    type: Literal["status_update"]
    call_id: PyObjectId
    status: CallStatus
    timestamp: datetime


class CallEndedPayLoad(BaseModel):
    type: Literal["user_hangup"]
    call_id: PyObjectId
    ended_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: Literal["hang_up", "rejected", "missed", "network_error", "busy", "timeout"]
    ended_by: PyObjectId


class BaseWebRTCMessage(BaseModel):
    sender_id: PyObjectId
    receiver_id: PyObjectId
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def overwrite_timestamp(self) -> Self:
        self.timestamp = datetime.now(timezone.utc)
        return self


class WebRTCOffer(BaseWebRTCMessage):
    call_id: Optional[PyObjectId]
    type: Literal["offer"]
    audio: bool
    video: bool
    description: dict  # Represents RTCSessionDescriptionInit (JSON serializable)


class WebRTCAnswer(BaseWebRTCMessage):
    call_id: PyObjectId
    type: Literal["answer"]
    audio: bool
    video: bool
    description: dict  # Represents RTCSessionDescriptionInit


class WebRTCIceCandidate(BaseWebRTCMessage):
    type: Literal["ice-candidate"]
    candidate: dict  # Represents RTCIceCandidateInit

    # Remove audio and video fields by overriding with None and exclude from schema
    audio: Optional[bool] = None
    video: Optional[bool] = None

    class Config:
        fields = {
            "audio": {"exclude": True},
            "video": {"exclude": True},
        }


# Union for all messages
WebRTCMessage = Union[
    WebRTCOffer, WebRTCAnswer, WebRTCIceCandidate, CallEndedPayLoad, CallStatusUpdate
]

# Combined Message Model for Websocket Handeling
SyncSocketMessage = Union[
    OnlineStatusMessage,
    FriendUpdateMessage,
    FriendRequestMessage,
    MessageStatusUpdate,
    AddFriendMessage,
    ProfileMediaUpdate,
    WebRTCOffer,
    WebRTCMessage,
]


class SyncPacket(BaseModel):
    type: PacketType
    data: Optional[SyncSocketMessage] = Field(default=None, discriminator="type")


class UserProfileMedia(BaseModel):
    avatar: Optional[str] = None
    banner: Optional[str] = None
