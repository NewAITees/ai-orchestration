from enum import Enum, auto
from typing import Dict, List, Optional, Any, Union, Literal, TypedDict, Protocol, runtime_checkable
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from abc import ABC, abstractmethod

class OrchestratorMode(str, Enum):
    """オーケストレーションモード"""
    CREATIVE = "creative"  # 創作モード
    CODING = "coding"      # コーディングモード
    RESEARCH = "research"  # 調査モード


class ComponentType(str, Enum):
    """AIコンポーネントの種類"""
    DIRECTOR = "director"  # 指示・統合担当
    PLANNER = "planner"    # 計画立案担当
    WORKER = "worker"      # タスク実行担当
    REVIEWER = "reviewer"  # 評価担当


class DirectorMode(str, Enum):
    """Director AIの動作モード"""
    CONTROL = "control"          # 制御モード
    INTEGRATION = "integration"  # 統合モード


class ReviewerMode(str, Enum):
    """Reviewer AIの評価モード"""
    DECOMPOSITION = "decomposition"  # 分解評価モード
    RESULT = "result"                # 結果評価モード


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


class ProcessPhase(str, Enum):
    """処理フェーズ"""
    TASK_DECOMPOSITION = "task_decomposition"  # タスク分解
    USER_FEEDBACK = "user_feedback"            # ユーザーフィードバック
    TASK_EXECUTION = "task_execution"          # タスク実行
    RESULT_INTEGRATION = "result_integration"  # 結果統合


class EvaluationStatus(str, Enum):
    """評価結果のステータス"""
    PASS = "pass"                # 合格
    FAIL = "fail"                # 不合格
    PARTIAL = "partial"          # 部分的に合格


class ErrorLevel(str, Enum):
    """エラーレベル"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ToolType(str, Enum):
    """ツールの種類"""
    SEARCH = "search"            # 検索ツール
    CODE_EXECUTION = "code_execution"  # コード実行ツール
    DATA_ANALYSIS = "data_analysis"    # データ分析ツール
    FILE_OPERATION = "file_operation"  # ファイル操作ツール
    CUSTOM = "custom"                  # カスタムツール


# 型エイリアス
TaskID = str
SubtaskID = str
SessionID = str
FeedbackID = str
ModelName = str


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


class EvaluationFeedbackDict(TypedDict):
    """評価フィードバックの辞書形式"""
    evaluation: EvaluationResult
    score: float
    feedback: str
    improvement_suggestions: List[str]


class TaskProgressDict(TypedDict):
    """タスク進捗状態の辞書形式"""
    status: TaskStatus
    progress: float
    current_phase: ProcessPhase
    current_subtask: Optional[SubtaskID]
    completed_subtasks: int
    total_subtasks: int
    started_at: str
    estimated_completion: Optional[str]


# パラメータ型
ModelParameters = Dict[str, Any]
ComponentParameters = Dict[str, Any]

# 結果型
ProcessingResult = Dict[str, Any]
FinalResult = Dict[str, Any]

# モード固有の型 - 創作モード
class CreativeModeOptions(TypedDict, total=False):
    """創作モードのオプション"""
    genre: str                 # ジャンル
    style: str                 # 文体スタイル
    tone: str                  # トーン（明るい、暗いなど）
    character_focus: bool      # キャラクター重視
    plot_focus: bool           # プロット重視
    world_building: bool       # 世界観構築重視
    target_length: str         # 目標長さ（短編、中編など）
    structure_type: str        # 構造タイプ（三幕構成など）


class StoryStructureElement(TypedDict):
    """物語構造の要素"""
    type: str                  # 要素タイプ（章、シーンなど）
    title: str                 # タイトル
    description: str           # 説明
    characters: List[str]      # 登場キャラクター
    goals: List[str]           # 目標
    conflicts: List[str]       # 葛藤要素


# ユーザーリクエスト型
class OrchestratorRequest(TypedDict, total=False):
    """オーケストレータリクエスト"""
    prompt: str                           # ユーザープロンプト
    mode: OrchestratorMode                # 動作モード
    model: Optional[ModelName]            # 使用モデル
    session_id: Optional[SessionID]       # セッションID
    creative_options: Optional[CreativeModeOptions]  # 創作モード設定
    params: Optional[Dict[str, Any]]     # その他のパラメータ


class MessageType(str, Enum):
    """メッセージタイプ"""
    COMMAND = "command"
    RESPONSE = "response"
    ERROR = "error"
    STATUS = "status"
    FEEDBACK = "feedback"
    QUERY = "query"


class Component(str, Enum):
    """コンポーネント"""
    DIRECTOR = "director"
    WORKER = "worker"
    REVIEWER = "reviewer"
    PLANNER = "planner"
    ORCHESTRATOR = "orchestrator"
    API = "api"
    CLIENT = "client"
    ALL = "all"


class TaskModel(BaseModel):
    """タスクの基本モデル"""
    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    requirements: List[str] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True,  # Allow ORM mode
        validate_assignment=True,  # Validate when attributes are assigned
        json_encoders={  # Custom JSON encoders
            datetime: lambda dt: dt.isoformat()
        }
    )

    def update_status(self, status: TaskStatus) -> None:
        """タスクの状態を更新する"""
        self.status = status
        self.updated_at = datetime.now()
        if status == TaskStatus.COMPLETED:
            self.completed_at = datetime.now()


class TaskStatusModel(BaseModel):
    """タスクステータスの詳細モデル"""
    task_id: str
    status: TaskStatus
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    current_stage: str
    subtasks: List[Dict[str, Any]] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)


class MessageModel(BaseModel):
    """メッセージの基本モデル"""
    type: MessageType
    sender: Component
    receiver: Component
    content: Dict[str, Any]
    session_id: str
    action: Optional[str] = None


class TaskExecutionResult(BaseModel):
    """タスク実行結果を表すモデル"""
    task_id: str
    status: TaskStatus
    result: Dict[str, Any]
    feedback: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    created_at: datetime = Field(default_factory=datetime.now)


class SubTask(BaseModel):
    """サブタスクの基本モデル"""
    id: str
    title: str
    description: str
    status: SubtaskStatus = SubtaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    requirements: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def update_status(self, status: SubtaskStatus) -> None:
        """タスクの状態を更新する"""
        self.status = status
        self.updated_at = datetime.now()


class OrchestrationMessage(BaseModel):
    """オーケストレーションメッセージの基本モデル"""
    type: MessageType
    sender: Component
    receiver: Component
    content: Dict[str, Any]
    session_id: str
    action: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class TaskAnalysisResult(BaseModel):
    """タスク分析結果のモデル"""
    
    main_task: str = Field(..., description="分析対象のメインタスク")
    task_type: str = Field(..., description="タスクのタイプ")
    complexity: int = Field(ge=1, le=10, description="タスクの複雑さ (1-10)")
    estimated_steps: int = Field(..., description="推定されるステップ数")
    subtasks: List[Dict[str, Any]] = Field(..., description="サブタスクのリスト")
    requirements: List[str] = Field(default_factory=list, description="タスクの要件")
    constraints: List[str] = Field(default_factory=list, description="タスクの制約")

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "main_task": "小説の執筆",
                    "task_type": "creative_writing",
                    "complexity": 8,
                    "estimated_steps": 5,
                    "subtasks": [
                        {"id": "plot", "title": "プロット作成"},
                        {"id": "characters", "title": "キャラクター設定"}
                    ],
                    "requirements": ["3000文字以上", "SF要素を含む"],
                    "constraints": ["暴力的な表現を避ける"]
                }
            ]
        }
    )

class ReviewResult(BaseModel):
    """レビュー結果のモデル"""
    
    task_id: str = Field(..., description="タスクの一意な識別子")
    status: str = Field(..., description="レビューの状態")
    score: float = Field(..., description="タスクの評価スコア")
    feedback: str = Field(..., description="タスクに関するフィードバック")
    suggestions: List[str] = Field(default_factory=list, description="改善提案のリスト")
    metrics: Dict[str, float] = Field(default_factory=dict, description="評価指標")

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "task_id": "task_123",
                    "status": "reviewed",
                    "score": 8.5,
                    "feedback": "全体的に良好な出力です。",
                    "suggestions": ["文章の簡潔さを改善", "具体例の追加"],
                    "metrics": {
                        "readability": 0.85,
                        "coherence": 0.92,
                        "creativity": 0.78
                    }
                }
            ]
        }
    ) 

class PlanningResult(BaseModel):
    """計画結果のモデル"""
    
    task_id: str = Field(..., description="タスクの一意な識別子")
    subtasks: List[Dict[str, Any]] = Field(..., description="計画されたサブタスクのリスト")
    dependencies: Dict[str, List[str]] = Field(default_factory=dict, description="サブタスク間の依存関係")
    estimated_duration: Dict[str, float] = Field(default_factory=dict, description="各サブタスクの推定所要時間")
    resource_requirements: Dict[str, List[str]] = Field(default_factory=dict, description="各サブタスクのリソース要件")
    
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "task_id": "task_123",
                    "subtasks": [
                        {"id": "subtask_1", "title": "要件分析", "description": "タスクの要件を詳細に分析する"},
                        {"id": "subtask_2", "title": "設計", "description": "システム設計を行う"}
                    ],
                    "dependencies": {
                        "subtask_2": ["subtask_1"]
                    },
                    "estimated_duration": {
                        "subtask_1": 2.0,
                        "subtask_2": 3.0
                    },
                    "resource_requirements": {
                        "subtask_1": ["分析ツール"],
                        "subtask_2": ["設計ツール", "ドキュメントテンプレート"]
                    }
                }
            ]
        }
    )

class Improvement(BaseModel):
    """改善提案のモデル"""
    
    id: str = Field(..., description="改善提案の一意な識別子")
    title: str = Field(..., description="改善提案のタイトル")
    description: str = Field(..., description="改善提案の詳細な説明")
    priority: int = Field(default=1, ge=1, le=5, description="優先度（1-5）")
    impact: float = Field(default=0.0, ge=0.0, le=1.0, description="予想される改善効果（0-1）")
    effort: float = Field(default=0.0, ge=0.0, le=1.0, description="必要な労力（0-1）")
    status: str = Field(default="proposed", description="改善提案の状態")
    created_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "imp_123",
                    "title": "パフォーマンス最適化",
                    "description": "データベースクエリの最適化による応答時間の改善",
                    "priority": 4,
                    "impact": 0.8,
                    "effort": 0.6,
                    "status": "proposed"
                }
            ]
        }
    )

class FinalResult(BaseModel):
    """最終結果のモデル"""
    
    task_id: str = Field(..., description="タスクの一意な識別子")
    status: TaskStatus = Field(..., description="タスクの最終状態")
    result: Dict[str, Any] = Field(..., description="タスクの最終結果")
    metrics: Dict[str, float] = Field(default_factory=dict, description="評価指標")
    improvements: List[Improvement] = Field(default_factory=list, description="改善提案のリスト")
    completed_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "task_id": "task_123",
                    "status": TaskStatus.COMPLETED,
                    "result": {
                        "output": "タスク完了の出力結果",
                        "artifacts": ["file1.txt", "file2.json"]
                    },
                    "metrics": {
                        "accuracy": 0.95,
                        "completion_time": 120.5
                    },
                    "improvements": []
                }
            ]
        }
    )

class EvaluationResult(BaseModel):
    """タスク評価結果のモデル"""
    task_id: str = Field(..., description="評価対象のタスクID")
    status: TaskStatus = Field(..., description="評価のステータス")
    score: float = Field(..., ge=0.0, le=1.0, description="評価スコア")
    feedback: str = Field(..., description="評価フィードバック")
    metrics: Dict[str, float] = Field(default_factory=dict, description="評価メトリクス")
    created_at: datetime = Field(default_factory=datetime.now, description="評価実施日時")

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "task_id": "task_123",
                    "status": TaskStatus.COMPLETED,
                    "score": 0.85,
                    "feedback": "タスクは概ね完了していますが、改善の余地があります。",
                    "metrics": {
                        "quality": 0.8,
                        "completeness": 0.9,
                        "relevance": 0.85
                    }
                }
            ]
        }
    )





# AI Component Interfaces and Base Classes
@runtime_checkable
class IDirectorAI(Protocol):
    """Director AIのインターフェース"""
    
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass
    
    @abstractmethod
    def control_process(self, task_id: TaskID) -> None:
        """タスクの実行プロセスを制御する"""
        pass

@runtime_checkable
class IPlannerAI(Protocol):
    """Planner AIのインターフェース"""
    
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass
    
    @abstractmethod
    def analyze_task(self, task: str) -> TaskAnalysisResult:
        """タスクを分析し、構造化された結果を返す"""
        pass

@runtime_checkable
class IWorkerAI(Protocol):
    """Worker AIのインターフェース"""
    
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass
    
    @abstractmethod
    def execute_task(self, task: SubTask) -> TaskExecutionResult:
        """タスクを実行し、結果を返す"""
        pass

@runtime_checkable
class IReviewerAI(Protocol):
    """Reviewer AIのインターフェース"""
    
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass
    
    @abstractmethod
    def review_task(self, task: SubTask) -> ReviewResult:
        """タスクをレビューし、結果を返す"""
        pass

class BaseAIComponent(ABC):
    """全AIコンポーネントの共通基底クラス"""
    
    def __init__(self, session: 'Session'):
        """
        初期化
        Args:
            session: 関連付けられたセッション
        """
        self.session = session
        self.current_task: Optional[SubTask] = None
    
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass
    
    def _create_message(
        self,
        receiver: Component,
        message_type: MessageType,
        content: Dict[str, Any]
    ) -> OrchestrationMessage:
        """
        メッセージを作成する
        Args:
            receiver: メッセージの受信者
            message_type: メッセージのタイプ
            content: メッセージの内容
        Returns:
            作成されたメッセージ
        """
        return OrchestrationMessage(
            type=message_type,
            sender=self.component_type,  # コンポーネントタイプは継承先で定義
            receiver=receiver,
            content=content,
            session_id=self.session.id
        )
    
    def _create_error_message(
        self,
        receiver: Component,
        error_message: str
    ) -> OrchestrationMessage:
        """
        エラーメッセージを作成する
        Args:
            receiver: メッセージの受信者
            error_message: エラーメッセージ
        Returns:
            作成されたエラーメッセージ
        """
        return self._create_message(
            receiver,
            MessageType.ERROR,
            {"error": error_message}
        )
