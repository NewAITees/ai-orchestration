from typing import List, Optional, Any, Dict, Protocol, TYPE_CHECKING, runtime_checkable
from abc import ABC, abstractmethod
from datetime import datetime

# --- 型定義とLLMマネージャーのインポート ---
# types.py から必要なものをインポート
# TaskStatus, TaskExecutionResult, TaskModel, SubTask を追加
from ..types import OrchestrationMessage, MessageType, Component, TaskStatus, TaskExecutionResult, TaskModel, SubTask, SubtaskID
# llm パッケージから BaseLLMManager をインポート (パスが正しいか確認)
from ..llm.llm_manager import BaseLLMManager

# --- 循環参照回避のためのインポート ---
if TYPE_CHECKING:
    # Session は core からインポート
    from ..core.session import Session
    # Task関連のスキーマも必要なら types から (既に上で import 済み)
    # from ..types import TaskModel, SubTask # 例

# --- プロトコル定義 (変更なし) ---
class AIComponentProtocol(Protocol):
    """AIコンポーネントの基本インターフェース"""
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]: ...

# --- 基底クラス ---
class BaseAIComponent(ABC):
    """全AIコンポーネントの共通基底クラス"""
    
    def __init__(self, session: 'Session', llm_manager: BaseLLMManager, **kwargs) -> None:
        """
        コンポーネントを初期化

        Args:
            session (Session): 現在のセッションオブジェクト
            llm_manager (BaseLLMManager): 使用するLLMマネージャー
            **kwargs: ファクトリーから渡される可能性のある追加設定
        """
        self.session = session
        self.llm_manager = llm_manager
        self.last_used: datetime = datetime.now()
        print(f"コンポーネント {self._get_component_type().value} ({self.__class__.__name__}) をセッション {session.id} で初期化しました。設定: {kwargs}")
        
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """
        受信したメッセージを処理し、応答メッセージのリストを返す抽象メソッド。
        将来的には Command パターンに置き換わる可能性がある。
        """
        pass
        
    def _create_response(
        self,
        receiver: Component,
        content: Dict[str, Any],
        action: Optional[str] = None
    ) -> OrchestrationMessage:
        """応答メッセージ (MessageType.RESPONSE) を作成するヘルパーメソッド。"""
        response_message = OrchestrationMessage(
            type=MessageType.RESPONSE,
            sender=self._get_component_type(),
            receiver=receiver,
            content=content,
            session_id=self.session.id,
            action=action
        )
        return response_message
        
    def _create_error_response(
        self,
        receiver: Component,
        error_message: str,
        action: Optional[str] = None
    ) -> OrchestrationMessage:
        """エラーメッセージ (MessageType.ERROR) を作成するヘルパーメソッド。"""
        error_content = {"error": error_message}
        error_response = OrchestrationMessage(
            type=MessageType.ERROR,
            sender=self._get_component_type(),
            receiver=receiver,
            content=error_content,
            session_id=self.session.id,
            action=action
        )
        print(f"[{self._get_component_type().value}] Error Response created for {receiver.value}: Action={action}, Error='{error_message}'")
        return error_response
    
    def update_last_used(self) -> None:
        """最終使用時刻を現在時刻に更新する。"""
        self.last_used = datetime.now()
    
    @abstractmethod
    def _get_component_type(self) -> Component:
        """自身のコンポーネントタイプ (Enum) を返す抽象メソッド。"""
        pass

# --- 各コンポーネントの基底クラスとプロトコル (Director, Planner, Worker, Reviewer) ---
# これらのクラスの import 文と型ヒントも確認・修正が必要
# 特に Session, BaseAIComponent, OrchestrationMessage, Component, MessageType を参照している箇所

# Director AI
class DirectorProtocol(AIComponentProtocol, Protocol):
    """Director AIのインターフェース"""
    def control_process(self, task_id: TaskID) -> None:
        pass
    def integrate_results(self, results: List[Any]) -> Any:
        pass

class BaseDirectorAI(BaseAIComponent):
    """Director AIの基本実装"""
    
    def _get_component_type(self) -> Component:
        return Component.DIRECTOR
    
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージ処理の基本実装 (旧式のまま)"""
        self.update_last_used()
        print(f"[Director] Received message: Type={message.type.value}, Action={message.action}, From={message.sender.value}")
        if message.type == MessageType.COMMAND:
            return self._process_command(message)
        elif message.type == MessageType.STATUS:
            print(f"[Director] Received status update: {message.content}")
            return []
        else:
            print(f"[Director] Unsupported message type: {message.type.value}")
            return [self._create_error_response(
                message.sender,
                f"不明なメッセージタイプ: {message.type.value}",
                action="unsupported_type"
            )]
    
    def _process_command(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """コマンドメッセージの処理 (旧式のまま)"""
        action = message.content.get("action")
        task_id = message.content.get("task_id")

        try:
            if action == "start_process" and task_id:
                print(f"[Director] Starting process for task: {task_id}")
                self.control_process(task_id)
                return [self._create_response(
                    message.sender,
                    {"status": "process_started", "task_id": task_id},
                    "process_started"
                )]
            elif action == "integrate":
                results = message.content.get("results", [])
                print(f"[Director] Integrating {len(results)} results.")
                integrated = self.integrate_results(results)
                return [self._create_response(
                    message.sender,
                    {"integrated_result": integrated},
                    "integration_completed"
                )]
            else:
                print(f"[Director] Unknown command action: {action}")
                return [self._create_error_response(
                    message.sender,
                    f"不明なコマンドアクション: {action}",
                    action="unknown_command"
                )]
        except Exception as e:
            error_msg = f"コマンド処理中にエラー発生 (Action: {action}): {e}"
            print(f"[Director] {error_msg}")
            return [self._create_error_response(
                message.sender,
                error_msg,
                action=f"{action}_failed" if action else "command_failed"
            )]
    
    @abstractmethod
    def control_process(self, task_id: TaskID) -> None:
        """プロセス制御の基本実装"""
        pass
        
    @abstractmethod
    def integrate_results(self, results: List[Any]) -> Any:
        """結果統合の基本実装"""
        pass

# Planner AI
class PlannerProtocol(AIComponentProtocol, Protocol):
    """Planner AIのインターフェース"""
    def analyze_requirements(self, requirements: List[str]) -> List[SubTask]:
        pass
    def plan_task(self, task: TaskModel, requirements: List[str] = None) -> Any:
        pass
    def validate_solution(self, solution: Any) -> bool:
        pass

class BasePlannerAI(BaseAIComponent):
    """Planner AIの基本実装"""
    
    def _get_component_type(self) -> Component:
        return Component.PLANNER
    
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージ処理 (旧式)"""
        self.update_last_used()
        print(f"[Planner] Received message: Type={message.type.value}, Action={message.action}, From={message.sender.value}")
        if message.type == MessageType.COMMAND:
            return self._process_command(message)
        else:
            print(f"[Planner] Unsupported message type: {message.type.value}")
            return [self._create_error_response(
                message.sender,
                f"不明なメッセージタイプ: {message.type.value}",
                action="unsupported_type"
            )]
    
    def _process_command(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """コマンドメッセージの処理 (旧式)"""
        action = message.content.get("action")
        try:
            if action == "analyze":
                requirements = message.content.get("requirements", [])
                print(f"[Planner] Analyzing requirements: {requirements}")
                analysis_result: List[SubTask] = self.analyze_requirements(requirements)
                analysis_content = {"analysis": [subtask.model_dump(mode='json') for subtask in analysis_result]}
                return [self._create_response(
                    message.sender,
                    analysis_content,
                    "analysis_completed"
                )]
            elif action == "plan_task":
                task_data = message.content.get("task")
                requirements = message.content.get("requirements", [])
                if not task_data:
                    raise ValueError("plan_task コマンドには 'task' データが必要です。")
                task = TaskModel.model_validate(task_data)
                print(f"[Planner] Planning task: {task.id} with requirements: {requirements}")
                plan = self.plan_task(task, requirements)
                return [self._create_response(
                    message.sender,
                    {"plan": plan},
                    "planning_completed"
                )]
            elif action == "validate":
                solution = message.content.get("solution")
                print(f"[Planner] Validating solution: {solution}")
                is_valid = self.validate_solution(solution)
                return [self._create_response(
                    message.sender,
                    {"is_valid": is_valid},
                    "validation_completed"
                )]
            else:
                print(f"[Planner] Unknown command action: {action}")
                return [self._create_error_response(
                    message.sender,
                    f"不明なコマンドアクション: {action}",
                    action="unknown_command"
                )]
        except Exception as e:
            error_msg = f"コマンド処理中にエラー発生 (Action: {action}): {e}"
            print(f"[Planner] {error_msg}")
            return [self._create_error_response(
                message.sender,
                error_msg,
                action=f"{action}_failed" if action else "command_failed"
            )]
    
    @abstractmethod
    def analyze_requirements(self, requirements: List[str]) -> List[SubTask]:
        """要件分析の基本実装 (将来的にplan_taskに統合？)"""
        pass
    
    @abstractmethod
    def plan_task(self, task: TaskModel, requirements: List[str] = None) -> Any:
        """タスク計画の基本実装"""
        pass
    
    @abstractmethod
    def validate_solution(self, solution: Any) -> bool:
        """ソリューション検証の基本実装"""
        pass

# Worker AI
@runtime_checkable
class WorkerProtocol(AIComponentProtocol, Protocol):
    """Worker AIのインターフェース"""
    def execute_task(self, task: SubTask, context: Optional[Dict[str, Any]] = None) -> TaskExecutionResult:
        pass
    def stop_task(self, task_id: SubtaskID) -> None:
        pass

class BaseWorkerAI(BaseAIComponent):
    """Worker AIの基本実装"""
    
    def _get_component_type(self) -> Component:
        return Component.WORKER
    
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージ処理 (旧式)"""
        self.update_last_used()
        print(f"[Worker] Received message: Type={message.type.value}, Action={message.action}, From={message.sender.value}")
        if message.type == MessageType.COMMAND:
            return self._process_command(message)
        else:
            print(f"[Worker] Unsupported message type: {message.type.value}")
            return [self._create_error_response(
                message.sender,
                f"不明なメッセージタイプ: {message.type.value}",
                action="unsupported_type"
            )]
    
    def _process_command(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """コマンドメッセージの処理 (旧式)"""
        action = message.content.get("action")
        task_id = message.content.get("task_id")

        try:
            if action == "execute":
                task_data = message.content.get("task")
                context = message.content.get("context")
                if not task_data:
                    raise ValueError("execute コマンドには 'task' データが必要です。")
                task = SubTask.model_validate(task_data)
                print(f"[Worker] Executing task: {task.id} with context: {context}")
                execution_result: TaskExecutionResult = self.execute_task(task, context)
                result_content = {"result": execution_result.model_dump(mode='json')}
                return [self._create_response(
                    message.sender,
                    result_content,
                    "execution_completed"
                )]
            elif action == "stop" and task_id:
                print(f"[Worker] Stopping task: {task_id}")
                self.stop_task(task_id)
                return [self._create_response(
                    message.sender,
                    {"status": "stop_requested", "task_id": task_id},
                    "task_stop_requested"
                )]
            else:
                err_action = "unknown_command"
                err_msg = f"不明なコマンドアクション: {action}"
                if action == "stop" and not task_id:
                    err_action = "missing_task_id"
                    err_msg = "stop コマンドには task_id が必要です。"
                print(f"[Worker] {err_msg}")
                return [self._create_error_response(
                    message.sender,
                    err_msg,
                    action=err_action
                )]
        except Exception as e:
            current_task_id = task.id if 'task' in locals() and hasattr(task, 'id') else task_id or "unknown"
            error_msg = f"コマンド処理中にエラー発生 (Action: {action}, TaskID: {current_task_id}): {e}"
            print(f"[Worker] {error_msg}")
            return [self._create_error_response(
                message.sender,
                error_msg,
                action=f"{action}_failed" if action else "command_failed"
            )]
    
    @abstractmethod
    def execute_task(self, task: SubTask, context: Optional[Dict[str, Any]] = None) -> TaskExecutionResult:
        """タスク実行の基本実装"""
        pass
    
    @abstractmethod
    def stop_task(self, task_id: SubtaskID) -> None:
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