from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = "viewer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CameraCreate(BaseModel):
    name: str
    location: str
    stream_url: str
    status: str = "online"


class CameraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    stream_url: str
    status: str
    created_at: datetime


class EventCreate(BaseModel):
    camera_id: int
    event_type: str
    severity: str = "low"
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    camera_id: int
    event_type: str
    severity: str
    confidence: float | None
    metadata: dict[str, Any] = Field(alias="metadata_json")
    timestamp: datetime


class AlertCreate(BaseModel):
    camera_id: int
    alert_type: str
    severity: str = "medium"
    message: str
    image_url: str | None = None
    track_id: int | None = None
    dwell_time: float | None = None
    in_danger_zone: bool | None = None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    alert_type: str
    severity: str
    message: str
    image_url: str | None
    track_id: int | None
    dwell_time: float | None
    in_danger_zone: bool | None
    timestamp: datetime


class RecordingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    file_path: str
    start_time: datetime
    end_time: datetime | None = None
