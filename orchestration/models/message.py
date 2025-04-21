from typing import Dict, Any
from pydantic import BaseModel

class Message(BaseModel):
    """メッセージモデル"""
    type: str
    action: str
    content: Dict[str, Any] 