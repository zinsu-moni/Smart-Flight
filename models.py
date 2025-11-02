"""Minimal models used by the scaffold.# models/a2a.py

from pydantic import BaseModel, Field

This file intentionally avoids third-party dependencies so `import main` worksfrom typing import Literal, Optional, List, Dict, Any

without installing packages.from datetime import datetime

"""from uuid import uuid4

from dataclasses import dataclass

from typing import Any, Dict, List, Optionalclass MessagePart(BaseModel):

    kind: Literal["text", "data", "file"]

    text: Optional[str] = None

@dataclass    data: Optional[Dict[str, Any]] = None

class FlightQuery:    file_url: Optional[str] = None

    origin: str

    destination: strclass A2AMessage(BaseModel):

    date: str    kind: Literal["message"] = "message"

    adults: int = 1    role: Literal["user", "agent", "system"]

    parts: List[MessagePart]

    messageId: str = Field(default_factory=lambda: str(uuid4()))

@dataclass    taskId: Optional[str] = None

class FlightCandidate:    metadata: Optional[Dict[str, Any]] = None

    price: float

    currency: strclass PushNotificationConfig(BaseModel):

    airline: str    url: str

    booking_link: str    token: Optional[str] = None

    authentication: Optional[Dict[str, Any]] = None



# helper typed aliasclass MessageConfiguration(BaseModel):

JSONDict = Dict[str, Any]    blocking: bool = True

    acceptedOutputModes: List[str] = ["text/plain", "image/png", "image/svg+xml"]
    pushNotificationConfig: Optional[PushNotificationConfig] = None

class MessageParams(BaseModel):
    message: A2AMessage
    configuration: MessageConfiguration = Field(default_factory=MessageConfiguration)

class ExecuteParams(BaseModel):
    contextId: Optional[str] = None
    taskId: Optional[str] = None
    messages: List[A2AMessage]

class JSONRPCRequest(BaseModel):
    jsonrpc: Literal["2.0"]
    id: str
    method: Literal["message/send", "execute"]
    params: MessageParams | ExecuteParams

class TaskStatus(BaseModel):
    state: Literal["working", "completed", "input-required", "failed"]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    message: Optional[A2AMessage] = None

class Artifact(BaseModel):
    artifactId: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    parts: List[MessagePart]

class TaskResult(BaseModel):
    id: str
    contextId: str
    status: TaskStatus
    artifacts: List[Artifact] = []
    history: List[A2AMessage] = []
    kind: Literal["task"] = "task"

class JSONRPCResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: str
    result: Optional[TaskResult] = None
    error: Optional[Dict[str, Any]] = None
