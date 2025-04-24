from typing import List, Optional, Any, Dict, Protocol, TYPE_CHECKING, runtime_checkable
from abc import ABC, abstractmethod

# --- 型定義とLLMマネージャーのインポート ---
# types.py から必要なものをインポート
# TaskStatus, TaskExecutionResult, TaskModel, SubTask を追加
from ..types import OrchestrationMessage, MessageType, Component, TaskStatus, TaskExecutionResult, TaskModel, SubTask, SubtaskID, TaskID, TaskStatusModel, PlanningResult, EvaluationResult, FinalResult, Improvement
# llm パッケージから BaseLLMManager をインポート (パスが正しいか確認)
from ..llm.llm_manager import BaseLLMManager

# --- 循環参照回避のためのインポート ---
if TYPE_CHECKING:
    # Session は core からインポート
    from ..core.session import Session
    # Task関連のスキーマも必要なら types から (既に上で import 済み)
    # from ..types import TaskModel, SubTask # 例

# --- プロトコル定義 (変更なし) ---
@runtime_checkable
class AIComponentProtocol(Protocol):
    """全AIコンポーネント共通のインターフェース"""
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass
    
    def get_status(self, task_id: TaskID) -> Optional[TaskStatusModel]:
        """タスクの状態を取得"""
        pass
    
    def update_status(self, task_id: TaskID, status: TaskStatus, metadata: Optional[Dict[str, Any]] = None) -> None:
        """タスクの状態を更新"""
        pass

# --- 基底クラス ---
class BaseAIComponent(ABC):
    """全AIコンポーネントの共通基底クラス"""
    component_type: Component  # サブクラスで設定
    
    def __init__(self, session, llm_manager=None):
        """初期化"""
        self.session = session
        self.llm_manager = llm_manager
        
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージ処理 - 統一インターフェース"""
        try:
            if message.type == MessageType.COMMAND:
                return self._process_command(message)
            elif message.type == MessageType.QUERY:
                return self._process_query(message)
            else:
                return [self._create_error_response(
                    message.sender, 
                    f"未対応のメッセージタイプ: {message.type}"
                )]
        except Exception as e:
            return [self._create_error_response(
                message.sender, 
                f"処理中にエラーが発生しました: {str(e)}"
            )]
    
    @abstractmethod
    def _process_command(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """コマンド処理（サブクラスで実装）"""
        pass
    
    def _process_query(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """クエリ処理 - デフォルト実装"""
        content = message.content
        query_type = content.get("query_type")
        
        if query_type == "status":
            task_id = content.get("task_id")
            # 実装省略
            return [self._create_response(
                message.sender,
                {"status": "unknown"},
                "status_query_response"
            )]
        else:
            return [self._create_error_response(
                message.sender,
                f"未対応のクエリタイプ: {query_type}"
            )]
    
    def _create_response(self, receiver: Component, content: Dict[str, Any], 
                         action: str) -> OrchestrationMessage:
        """応答メッセージを作成"""
        return OrchestrationMessage(
            type=MessageType.RESPONSE,
            sender=self.component_type,
            receiver=receiver,
            content={"status": "success", **content},
            session_id=self.session.id,
            action=action
        )
    
    def _create_error_response(self, receiver: Component, 
                              error_message: str) -> OrchestrationMessage:
        """エラーメッセージを作成"""
        return OrchestrationMessage(
            type=MessageType.ERROR,
            sender=self.component_type,
            receiver=receiver,
            content={"status": "failure", "error": error_message},
            session_id=self.session.id
        )

# --- 各コンポーネントの基底クラスとプロトコル (Director, Planner, Worker, Reviewer) ---
# これらのクラスの import 文と型ヒントも確認・修正が必要
# 特に Session, BaseAIComponent, OrchestrationMessage, Component, MessageType を参照している箇所

# Director AI
@runtime_checkable
class DirectorProtocol(AIComponentProtocol, Protocol):
    """Director AIのインターフェース"""
    def execute_process(self, task_id: TaskID) -> None:
        """プロセス全体の実行を制御"""
        pass
    
    def integrate_results(self, results: List[TaskExecutionResult]) -> FinalResult:
        """実行結果を統合して最終結果を生成"""
        pass

class BaseDirectorAI(BaseAIComponent):
    """Director AIの基本実装"""
    component_type = Component.DIRECTOR
    
    @abstractmethod
    def execute_process(self, task_id: TaskID) -> None:
        """プロセス全体の実行を制御"""
        pass
        
    @abstractmethod
    def integrate_results(self, results: List[TaskExecutionResult]) -> FinalResult:
        """結果統合の基本実装"""
        pass

# Planner AI
@runtime_checkable
class PlannerProtocol(AIComponentProtocol, Protocol):
    """Planner AIのインターフェース"""
    async def plan_task(self, task: TaskModel, requirements: Optional[List[str]] = None) -> PlanningResult:
        """タスクの実行計画を生成"""
        pass
    
    async def validate_plan(self, plan: PlanningResult) -> bool:
        """生成された計画の妥当性を検証"""
        pass

class BasePlannerAI(BaseAIComponent):
    """Planner AIの基本実装"""
    component_type = Component.PLANNER
    
    @abstractmethod
    async def plan_task(self, task: TaskModel, requirements: Optional[List[str]] = None) -> PlanningResult:
        """タスク計画の基本実装"""
        pass
    
    @abstractmethod
    async def validate_plan(self, plan: PlanningResult) -> bool:
        """ソリューション検証の基本実装"""
        pass

# Worker AI
@runtime_checkable
class WorkerProtocol(AIComponentProtocol, Protocol):
    """Worker AIのインターフェース"""
    def execute_task(self, task: SubTask, context: Optional[Dict[str, Any]] = None) -> TaskExecutionResult:
        """タスクを実行"""
        pass
    
    def stop_execution(self, task_id: TaskID) -> None:
        """タスクの実行を停止"""
        pass

class BaseWorkerAI(BaseAIComponent):
    """Worker AIの基本実装"""
    component_type = Component.WORKER
    
    @abstractmethod
    def execute_task(self, task: SubTask, context: Optional[Dict[str, Any]] = None) -> TaskExecutionResult:
        """タスク実行の基本実装"""
        pass
    
    @abstractmethod
    def stop_execution(self, task_id: TaskID) -> None:
        """タスク停止の基本実装"""
        pass

# Reviewer AI (Evaluator と同一視する提案だったが、ここでは Reviewer として残す)
# もし Evaluator に統一する場合は、このクラスは削除し、BaseEvaluatorAI を修正する
@runtime_checkable
class ReviewerProtocol(AIComponentProtocol, Protocol):
    """Reviewer AIのインターフェース"""
    async def evaluate_task(self, task: SubTask, result: Optional[TaskExecutionResult] = None) -> EvaluationResult:
        """タスクの評価を実行"""
        pass
    
    async def suggest_improvements(self, evaluation: EvaluationResult) -> List[Improvement]:
        """改善提案を生成"""
        pass

class BaseReviewerAI(BaseAIComponent):
    """Reviewer AIの基本実装（EvaluatorとReviewerを統合）"""
    component_type = Component.REVIEWER
    
    @abstractmethod
    async def evaluate_task(self, task: SubTask, result: Optional[TaskExecutionResult] = None) -> EvaluationResult:
        """タスク評価の基本実装"""
        pass
    
    @abstractmethod
    async def suggest_improvements(self, evaluation: EvaluationResult) -> List[Improvement]:
        """改善提案生成の基本実装"""
        pass 