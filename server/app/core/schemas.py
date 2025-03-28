from typing import Optional, List, Any, Callable, Literal, Union
from datetime import datetime
from bson import ObjectId
from typing_extensions import Annotated
from enum import Enum, unique
from pydantic import BaseModel, Field, EmailStr, FileUrl
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


class UserAuth(BaseModel):
    id: Optional[PyObjectId] = Field(validation_alias="_id", default=None)
    username: str
    email: EmailStr
    password: str
    hashing_salt: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserAuthOut(BaseModel):
    id: PyObjectId = Field(validation_alias="_id")
    username: str
    email: EmailStr
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserProfile(BaseModel):
    id: Optional[PyObjectId] = Field(validation_alias="_id", default=None)
    auth_id: PyObjectId
    full_name: str
    bio: str | None = None
    profile_picture: str | None = None
    banner_picture: Optional[FileUrl] = None
    location: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserRegistration(BaseModel):
    username: str
    full_name: str
    email: EmailStr
    password: str


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
    banner_picture: Optional[FileUrl] = None
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
    update_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FriendRequestIn(BaseModel):
    username: str
    message: str | None = None


class FriendRequestDB(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    sender_id: PyObjectId
    receiver_id: PyObjectId
    message: str | None = None
    status: Friends_Status = Friends_Status.pending
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


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
    start_date: datetime = Field(default_factory=datetime.utcnow)
    last_message_date: datetime = Field(default_factory=datetime.utcnow)


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
    sending_time: datetime = Field(default_factory=datetime.utcnow)
    received_time: Optional[datetime] = None
    seen_time: Optional[datetime] = None
    status: Message_Status = Message_Status.send


class MessageNoAlias(Message):
    id: Optional[PyObjectId] = Field(default=None, serialization_alias="_id")


class ConversationResponse(Conversation):
    messages: List[Message] | None = None


class FileData(BaseModel):
    temp_file_id: Optional[str] = None
    name: Optional[str] = None


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
    full_name: Optional[str]
    bio: Optional[str]
    profile_picture: Optional[str]


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


# Combined Message Model for Websocket Handeling
SyncSocketMessage = Union[
    OnlineStatusMessage,
    FriendUpdateMessage,
    FriendRequestMessage,
    MessageStatusUpdate,
    AddFriendMessage,
    ProfileMediaUpdate,
]


class SyncPacket(BaseModel):
    type: PacketType
    data: Optional[SyncSocketMessage] = Field(default=None, discriminator="type")
