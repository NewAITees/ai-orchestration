from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class BaseModelWithTimestamps(BaseModel):
    """タイムスタンプを持つ基底モデル"""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra='forbid'  # 余分なフィールドを禁止
    )

class BaseTaskModel(BaseModelWithTimestamps):
    """タスク関連の基底モデル"""
    id: str
    status: str

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra='forbid'
    ) 