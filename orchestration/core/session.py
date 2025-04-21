import uuid
from typing import Dict, List, Optional, Any, Union, Literal, TypedDict
from datetime import datetime
from enum import Enum, auto
import json
import os
from pydantic import BaseModel, Field
from pathlib import Path
from ..types import (
    TaskStatus, TaskModel, TaskStatusModel, SubtaskStatus,
    TaskID, SubtaskID, SessionID, FeedbackID, ModelName
)

class TaskStatus(str, Enum):
    """タスクの状態"""
    PENDING = "pending"           # 待機中
    PLANNING = "planning"         # 計画中
    AWAITING_FEEDBACK = "awaiting_feedback"  # フィードバック待ち
    EXECUTING = "executing"       # 実行中
    INTEGRATING = "integrating"   # 統合中
    COMPLETED = "completed"       # 完了
    FAILED = "failed"             # 失敗
    CANCELLED = "cancelled"       # キャンセル

class SubtaskStatus(str, Enum):
    """サブタスクの状態"""
    PENDING = "pending"           # 待機中
    BLOCKED = "blocked"           # ブロック中（依存関係）
    IN_PROGRESS = "in_progress"   # 実行中
    REVIEWING = "reviewing"       # レビュー中
    REVISING = "revising"         # 修正中
    COMPLETED = "completed"       # 完了
    FAILED = "failed"             # 失敗

class SessionStatus(str, Enum):
    """セッションの状態を表す列挙型"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# 構造化データ型
class SubtaskDict(TypedDict):
    """サブタスク定義の辞書形式"""
    id: SubtaskID
    title: str
    description: str
    dependencies: List[SubtaskID]
    success_criteria: List[str]
    tools: List[str]

class SubtaskResultDict(TypedDict):
    """サブタスク実行結果の辞書形式"""
    subtask_id: SubtaskID
    status: SubtaskStatus
    result: str
    metadata: Dict[str, Any]

class TaskProgressDict(TypedDict):
    """タスク進捗状態の辞書形式"""
    status: TaskStatus
    progress: float
    current_phase: str
    current_subtask: Optional[SubtaskID]
    completed_subtasks: int
    total_subtasks: int
    started_at: str
    estimated_completion: Optional[str]

@dataclass
class Task:
    """タスクを表すデータクラス"""
    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def update_status(self, status: TaskStatus) -> None:
        """ステータスを更新"""
        self.status = status
        self.updated_at = datetime.now()
        if status == TaskStatus.COMPLETED:
            self.completed_at = datetime.now()

class SubTask(TaskModel):
    """サブタスク"""
    parent_id: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    priority: int = 0
    
    def update_status(self, status: TaskStatus) -> None:
        """ステータスを更新"""
        self.status = status
        self.updated_at = datetime.now()
        if status == TaskStatus.COMPLETED:
            self.completed_at = datetime.now()

class Session:
    """セッション"""
    
    def __init__(self, id: str, mode: Optional[str] = None) -> None:
        self.id = id
        self.mode = mode
        self.subtasks: Dict[str, SubTask] = {}
        self.task_statuses: Dict[str, TaskStatusModel] = {}
    
    def add_subtask(self, task: SubTask) -> None:
        """サブタスクを追加"""
        self.subtasks[task.id] = task
        self.task_statuses[task.id] = TaskStatusModel(
            task_id=task.id,
            status=task.status,
            progress=0.0,
            current_stage="pending"
        )
    
    def get_subtask(self, task_id: str) -> Optional[SubTask]:
        """サブタスクを取得"""
        return self.subtasks.get(task_id)
    
    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: Optional[float] = None,
        current_stage: Optional[str] = None
    ) -> None:
        """タスクの状態を更新"""
        if task_id in self.task_statuses:
            task_status = self.task_statuses[task_id]
            task_status.status = status
            if progress is not None:
                task_status.progress = progress
            if current_stage is not None:
                task_status.current_stage = current_stage
            task_status.last_updated = datetime.now()

class SessionManager:
    """セッションマネージャー"""
    
    _instance: Optional['SessionManager'] = None
    
    @classmethod
    def get_instance(cls, storage_dir: str = "./data/sessions") -> 'SessionManager':
        """シングルトンインスタンスを取得"""
        if cls._instance is None:
            cls._instance = cls(storage_dir)
        return cls._instance
    
    def __init__(self, storage_dir: str = "./data/sessions") -> None:
        """初期化"""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, Session] = {}
        self._load_sessions()
    
    def create_session(self, id: str, mode: Optional[str] = None) -> Session:
        """新規セッションを作成"""
        if id in self.sessions:
            raise ValueError(f"Session {id} already exists")
            
        session = Session(id=id, mode=mode)
        self.sessions[id] = session
        self._save_session(session)
        return session
    
    def get_session(self, id: str) -> Optional[Session]:
        """セッションを取得"""
        if id not in self.sessions:
            session_path = self.storage_dir / f"{id}.json"
            if session_path.exists():
                self._load_session(session_path)
                
        return self.sessions.get(id)
    
    def update_session(self, session: Session) -> None:
        """セッションを更新"""
        self.sessions[session.id] = session
        self._save_session(session)
    
    def delete_session(self, id: str) -> bool:
        """セッションを削除"""
        if id not in self.sessions:
            return False
            
        session_path = self.storage_dir / f"{id}.json"
        if session_path.exists():
            session_path.unlink()
            
        del self.sessions[id]
        return True
    
    def list_sessions(self) -> List[str]:
        """セッションIDのリストを取得"""
        return list(self.sessions.keys())
    
    def _load_sessions(self) -> None:
        """セッションファイルを読み込む"""
        for file_path in self.storage_dir.glob("*.json"):
            self._load_session(file_path)
    
    def _load_session(self, file_path: Path) -> None:
        """セッションファイルを読み込む"""
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                session = Session(id=data["id"], mode=data.get("mode"))
                self.sessions[session.id] = session
        except Exception as e:
            print(f"Error loading session from {file_path}: {e}")
    
    def _save_session(self, session: Session) -> None:
        """セッションを保存"""
        try:
            file_path = self.storage_dir / f"{session.id}.json"
            data = {
                "id": session.id,
                "mode": session.mode
            }
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving session to {file_path}: {e}") 