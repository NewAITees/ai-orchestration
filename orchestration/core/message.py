from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
from pydantic import BaseModel, Field, ConfigDict
from ..types import MessageType, Component, MessageModel

class OrchestrationMessage(MessageModel):
    """オーケストレーションメッセージ"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    def __init__(
        self,
        type: MessageType,
        sender: Component,
        receiver: Component,
        content: Dict[str, Any],
        session_id: str,
        action: Optional[str] = None
    ):
        super().__init__(
            type=type,
            sender=sender,
            receiver=receiver,
            content=content,
            session_id=session_id,
            action=action
        )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "type": "command",
                "sender": "director",
                "receiver": "planner",
                "content": {
                    "action": "analyze_task",
                    "task": "短い物語を書いて"
                },
                "timestamp": "2025-04-22T12:00:00",
                "session_id": "session-123"
            }
        }
    ) 