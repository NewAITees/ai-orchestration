import uuid
from typing import Dict, List, Optional, Any, Union, Literal, TypedDict, TYPE_CHECKING
from datetime import datetime
from enum import Enum, auto
import json
import os
from pydantic import BaseModel, Field, ValidationError
from pathlib import Path
from ..types import (
    TaskStatus, TaskModel, TaskStatusModel, SubtaskStatus,
    TaskID, SubtaskID, SessionID, FeedbackID, ModelName,
    SubTask
)

# --- 共通ユーティリティと型定義のインポート ---
from ..utils.common import generate_id, json_serialize, json_deserialize

# --- 循環参照回避のためのインポート ---
if TYPE_CHECKING:
    from ..components.base import BaseAIComponent
    from ..llm.llm_manager import BaseLLMManager
    from ..factory import AIComponentFactory
    from ..commands import CommandDispatcher

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

class SubTask:
    """サブタスク"""
    def __init__(self, id: str, title: str, description: str, **kwargs):
        self.id = id
        self.title = title
        self.description = description
        self.status = kwargs.get("status", TaskStatus.PENDING)
        self.result = kwargs.get("result")
        self.requirements = kwargs.get("requirements", [])
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def update_status(self, status: TaskStatus) -> None:
        """状態更新"""
        self.status = status
        self.updated_at = datetime.now()

class Session:
    """セッション管理"""
    def __init__(self, id: Optional[str] = None, **kwargs):
        self.id = id or f"session_{uuid.uuid4().hex}"
        self.title = kwargs.get("title", "")
        self.mode = kwargs.get("mode")
        self.requirements = kwargs.get("requirements", [])
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.subtasks: Dict[str, SubTask] = {}
        self.components = {}
    
    def add_subtask(self, task: SubTask) -> None:
        """サブタスク追加"""
        self.subtasks[task.id] = task
        self.updated_at = datetime.now()
    
    def get_subtask(self, task_id: str) -> Optional[SubTask]:
        """サブタスク取得"""
        return self.subtasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """タスク状態更新"""
        task = self.get_subtask(task_id)
        if task:
            task.update_status(status)
            self.updated_at = datetime.now()
    
    def get_component(self, component_type: str):
        """コンポーネント取得"""
        return self.components.get(component_type)

class SessionManager:
    """セッションの永続化と管理を行うクラス（シングルトン）"""
    _instance: Optional['SessionManager'] = None

    @classmethod
    def get_instance(
        cls,
        storage_dir: Optional[str] = None, # オプショナルに変更
        llm_manager: Optional['BaseLLMManager'] = None,
        factory: Optional['AIComponentFactory'] = None
    ) -> 'SessionManager':
        """シングルトンインスタンスを取得。初回のみ引数が必要。"""
        if cls._instance is None:
            if storage_dir is None or llm_manager is None or factory is None:
                raise ValueError("SessionManager の初回初期化には storage_dir, llm_manager, factory が必要です")
            cls._instance = cls(storage_dir, llm_manager, factory)
        # 2回目以降は引数不要だが、設定を変えたい場合は再初期化が必要（非推奨）
        elif storage_dir is not None:
             print("警告: SessionManager は既に初期化されています。storage_dir の変更は無視されます。")
        return cls._instance

    def __init__(
        self,
        storage_dir: str,
        llm_manager: 'BaseLLMManager',
        factory: 'AIComponentFactory'
    ) -> None:
        """初期化（直接呼び出し非推奨）"""
        if SessionManager._instance is not None:
             # raise Exception("SessionManager はシングルトンです。get_instance() を使用してください。")
             # 既にインスタンスがある場合は何もしないか、警告を出す
             print("警告: SessionManager は既にインスタンスが存在します。初期化をスキップします。")
             return

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[SessionID, Session] = {} # 型エイリアス使用
        self.llm_manager = llm_manager
        self.factory = factory
        self._load_sessions()
        SessionManager._instance = self # シングルトンインスタンスを設定
        print(f"SessionManager を初期化しました。ストレージ: {self.storage_dir}")


    def create_session(
        self,
        session_id: Optional[SessionID] = None,
        mode: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        initial_tasks: Optional[List[SubTask]] = None
    ) -> Session:
        """新規セッションを作成"""
        # generate_id を使用
        sid = session_id if session_id else generate_id(prefix="session")
        if sid in self.sessions:
            raise ValueError(f"セッションID {sid} は既に存在します")

        session = Session(
            session_id=sid,
            llm_manager=self.llm_manager,
            factory=self.factory,
            config=config,
            mode=mode,
            initial_tasks=initial_tasks
        )
        self.sessions[sid] = session
        self._save_session(session) # 作成時にも保存
        print(f"新規セッション {sid} を作成し、保存しました。")
        return session

    def get_session(self, session_id: SessionID) -> Optional[Session]:
        """セッションを取得 (メモリ -> ファイルの順で検索)"""
        if session_id in self.sessions:
            return self.sessions[session_id]

        # メモリになければファイルからロード試行
        session_path = self.storage_dir / f"{session_id}.json"
        if session_path.exists():
            print(f"セッション {session_id} がメモリにないため、ファイルからロードします。")
            return self._load_session(session_path) # ロードして返す
        else:
            print(f"セッション {session_id} はメモリにもファイルにも存在しません。")
            return None

    def update_session(self, session: Session) -> None:
        """セッションを更新して保存"""
        if session.id not in self.sessions:
             print(f"警告: 更新対象のセッション {session.id} がマネージャーに登録されていません。新規登録します。")
        self.sessions[session.id] = session
        self._save_session(session)
        # print(f"セッション {session.id} を更新し、保存しました。") # save_session内でログが出るので不要かも

    def delete_session(self, session_id: SessionID) -> bool:
        """セッションをメモリとファイルから削除"""
        session_path = self.storage_dir / f"{session_id}.json"
        deleted = False
        if session_id in self.sessions:
            del self.sessions[session_id]
            deleted = True
            print(f"メモリからセッション {session_id} を削除しました。")

        if session_path.exists():
            try:
                session_path.unlink()
                # 既にメモリから消えていてもファイル削除が成功すれば True
                deleted = True
                print(f"ファイル {session_path} を削除しました。")
            except OSError as e:
                print(f"エラー: セッションファイル {session_path} の削除に失敗しました: {e}")
                # ファイル削除失敗でもメモリから消えていれば True のままにするか？ -> Falseにする方が安全か
                deleted = False
        elif not deleted:
             print(f"削除対象のセッション {session_id} は見つかりませんでした。")

        return deleted

    def list_sessions(self) -> List[SessionID]:
        """存在するセッションIDのリストを取得 (メモリ + ファイル)"""
        memory_ids = set(self.sessions.keys())
        try:
             file_ids = {p.stem for p in self.storage_dir.glob("*.json")}
        except FileNotFoundError:
             print(f"警告: ストレージディレクトリ {self.storage_dir} が見つかりません。")
             file_ids = set()

        all_ids = sorted(list(memory_ids.union(file_ids)))
        # print(f"利用可能なセッションIDリスト: {all_ids}") # ログは get で十分かも
        return all_ids

    def _load_sessions(self) -> None:
        """ストレージディレクトリから全セッションをロード試行（メモリにないもののみ）"""
        print(f"{self.storage_dir} から未ロードのセッションを読み込みます...")
        loaded_count = 0
        failed_count = 0
        try:
            for file_path in self.storage_dir.glob("*.json"):
                session_id = file_path.stem
                if session_id not in self.sessions:
                    loaded_session = self._load_session(file_path)
                    if loaded_session:
                        loaded_count += 1
                    else:
                        failed_count +=1
        except FileNotFoundError:
             print(f"警告: ストレージディレクトリ {self.storage_dir} が見つかりません。ロードをスキップします。")
             return
        print(f"{loaded_count} 件のセッションをロードしました。{failed_count} 件は失敗。")


    def _load_session(self, file_path: Path) -> Optional[Session]:
        """JSONファイルからセッションを読み込む"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                session_data = json.load(f)
            
            # セッションを復元
            session = Session.from_dict(
                data=session_data,
                llm_manager=self.llm_manager,
                factory=self.factory
            )
            
            # メモリ上のセッション辞書に追加
            self.sessions[session.id] = session
            print(f"セッション {session.id} をファイル {file_path} から読み込みました。")
            return session
            
        except ValidationError as e:
            print(f"エラー: セッションデータのバリデーションに失敗しました ({file_path}): {e}")
            return None
        except Exception as e:
            print(f"エラー: セッションの読み込みに失敗しました ({file_path}): {e}")
            return None


    def _save_session(self, session: Session) -> None:
        """セッションの状態をJSONファイルに保存"""
        file_path = self.storage_dir / f"{session.id}.json"
        try:
            # Pydantic V2 スタイル: model_dump() を使用
            session_data = session.to_dict()  # to_dict()メソッドはすでにmodel_dump()を使用
            
            # JSON文字列に変換して保存
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            print(f"セッション {session.id} を {file_path} に保存しました。")
        except Exception as e:
            print(f"エラー: セッション {session.id} の保存に失敗しました ({file_path}): {e}") 