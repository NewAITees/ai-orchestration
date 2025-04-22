from typing import List, Optional, Any, Dict, Protocol, TYPE_CHECKING, runtime_checkable
from abc import ABC, abstractmethod
from datetime import datetime

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
    
    def __init__(self, session: 'Session', llm_manager: 'BaseLLMManager', **kwargs) -> None:
        """
        基底クラスの初期化
        Args:
            session: 関連付けられたセッション
            llm_manager: LLMマネージャー
            **kwargs: 追加の設定パラメータ
        """
        self.session = session
        self.llm_manager = llm_manager
        self.component_status: Dict[TaskID, TaskStatusModel] = {}
    
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """
        メッセージを処理し、応答メッセージのリストを返す
        Args:
            message: 処理するメッセージ
        Returns:
            応答メッセージのリスト
        """
        try:
            if message.type == MessageType.COMMAND:
                return self._process_command(message)
            elif message.type == MessageType.QUERY:
                return self._process_query(message)
            else:
                return [self._create_error_response(
                    message.sender,
                    f"未対応のメッセージタイプ: {message.type}",
                    action="unsupported_message_type"
                )]
        except Exception as e:
            return [self._create_error_response(
                message.sender,
                f"メッセージ処理中にエラー発生: {e}",
                action="message_processing_error"
            )]
    
    def get_status(self, task_id: TaskID) -> Optional[TaskStatusModel]:
        """
        タスクの状態を取得
        Args:
            task_id: 対象タスクのID
        Returns:
            タスクの状態情報、存在しない場合はNone
        """
        return self.component_status.get(task_id)
    
    def update_status(self, task_id: TaskID, status: TaskStatus, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        タスクの状態を更新
        Args:
            task_id: 対象タスクのID
            status: 新しい状態
            metadata: 追加のメタデータ
        """
        current = self.component_status.get(task_id, TaskStatusModel(task_id=task_id))
        current.status = status
        if metadata:
            current.metadata.update(metadata)
        self.component_status[task_id] = current
        # セッションの状態も更新
        self.session.update_task_status(task_id, status)
    
    @abstractmethod
    def _process_command(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """コマンドメッセージの処理（サブクラスで実装）"""
        pass
    
    def _process_query(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """
        クエリメッセージの処理
        Args:
            message: 処理するクエリメッセージ
        Returns:
            応答メッセージのリスト
        """
        content = message.content
        query_type = content.get("query_type")
        
        if query_type == "status":
            task_id = content.get("task_id")
            if not task_id:
                return [self._create_error_response(
                    message.sender,
                    "task_id が指定されていません",
                    action="invalid_query"
                )]
            status = self.get_status(task_id)
            return [self._create_response(
                message.sender,
                {"status": status.model_dump() if status else None},
                "status_query_response"
            )]
        else:
            return [self._create_error_response(
                message.sender,
                f"未対応のクエリタイプ: {query_type}",
                action="unsupported_query_type"
            )]
    
    def _create_response(
        self,
        receiver: Component,
        content: Dict[str, Any],
        action: str
    ) -> OrchestrationMessage:
        """
        応答メッセージを作成
        Args:
            receiver: メッセージの受信者
            content: メッセージの内容
            action: アクション名
        Returns:
            作成されたメッセージ
        """
        return OrchestrationMessage(
            type=MessageType.RESPONSE,
            sender=self.component_type,
            receiver=receiver,
            content=content,
            session_id=self.session.id,
            action=action
        )
    
    def _create_error_response(
        self,
        receiver: Component,
        error_message: str,
        action: str = "error"
    ) -> OrchestrationMessage:
        """
        エラーメッセージを作成
        Args:
            receiver: メッセージの受信者
            error_message: エラーメッセージ
            action: アクション名
        Returns:
            作成されたエラーメッセージ
        """
        return self._create_response(
            receiver,
            {"error": error_message},
            action
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
    def plan_task(self, task: TaskModel, requirements: Optional[List[str]] = None) -> PlanningResult:
        """タスクの実行計画を生成"""
        pass
    
    def validate_plan(self, plan: PlanningResult) -> bool:
        """生成された計画の妥当性を検証"""
        pass

class BasePlannerAI(BaseAIComponent):
    """Planner AIの基本実装"""
    component_type = Component.PLANNER
    
    @abstractmethod
    def plan_task(self, task: TaskModel, requirements: Optional[List[str]] = None) -> PlanningResult:
        """タスク計画の基本実装"""
        pass
    
    @abstractmethod
    def validate_plan(self, plan: PlanningResult) -> bool:
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
class ReviewerProtocol(AIComponentProtocol, Protocol):
    """Reviewer AIのインターフェース"""
    def evaluate_solution(self, solution: Any, task: Optional[SubTask] = None) -> Dict[str, Any]:
        pass
    def suggest_improvements(self, evaluation_result: Dict[str, Any]) -> List[str]:
        pass

class BaseReviewerAI(BaseAIComponent):
    """Reviewer AIの基本実装"""
    
    def _get_component_type(self) -> Component:
        return Component.REVIEWER
    
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージ処理 (旧式)"""
        self.update_last_used()
        print(f"[Reviewer] Received message: Type={message.type.value}, Action={message.action}, From={message.sender.value}")
        if message.type == MessageType.COMMAND:
            return self._process_command(message)
        else:
            print(f"[Reviewer] Unsupported message type: {message.type.value}")
            return [self._create_error_response(
                message.sender,
                f"不明なメッセージタイプ: {message.type.value}",
                action="unsupported_type"
            )]
    
    def _process_command(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """コマンドメッセージの処理 (旧式)"""
        action = message.content.get("action")
        try:
            if action == "evaluate":
                solution = message.content.get("solution")
                task_data = message.content.get("task")
                task = SubTask.model_validate(task_data) if task_data else None
                print(f"[Reviewer] Evaluating solution for task {task.id if task else 'N/A'}: {solution}")
                evaluation = self.evaluate_solution(solution, task)
                return [self._create_response(
                    message.sender,
                    {"evaluation": evaluation},
                    "evaluation_completed"
                )]
            elif action == "suggest":
                evaluation_result = message.content.get("evaluation")
                if not evaluation_result:
                    raise ValueError("suggest コマンドには 'evaluation' データが必要です。")
                print(f"[Reviewer] Suggesting improvements based on evaluation: {evaluation_result}")
                improvements = self.suggest_improvements(evaluation_result)
                return [self._create_response(
                    message.sender,
                    {"improvements": improvements},
                    "suggestions_completed"
                )]
            else:
                print(f"[Reviewer] Unknown command action: {action}")
                return [self._create_error_response(
                    message.sender,
                    f"不明なコマンドアクション: {action}",
                    action="unknown_command"
                )]
        except Exception as e:
            error_msg = f"コマンド処理中にエラー発生 (Action: {action}): {e}"
            print(f"[Reviewer] {error_msg}")
            return [self._create_error_response(
                message.sender,
                error_msg,
                action=f"{action}_failed" if action else "command_failed"
            )]
    
    @abstractmethod
    def evaluate_solution(self, solution: Any, task: Optional[SubTask] = None) -> Dict[str, Any]:
        """ソリューション評価の基本実装"""
        pass
    
    @abstractmethod
    def suggest_improvements(self, evaluation_result: Dict[str, Any]) -> List[str]:
        """改善提案の基本実装"""
        pass

class BaseEvaluatorAI(BaseAIComponent):
    """Evaluator AIの基本実装 (ReviewerとEvaluatorを統合)"""
    component_type = Component.EVALUATOR
    
    @abstractmethod
    def evaluate_task(self, task: SubTask, result: Optional[TaskExecutionResult] = None) -> EvaluationResult:
        """タスクの実行結果を評価"""
        pass
    
    @abstractmethod
    def suggest_improvements(self, evaluation: EvaluationResult) -> List[Improvement]:
        """評価結果に基づく改善案を提案"""
        pass 