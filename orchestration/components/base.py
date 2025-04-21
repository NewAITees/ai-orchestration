from typing import List, Optional, Any, Dict
from abc import ABC, abstractmethod
from datetime import datetime
from ..llm.llm_manager import BaseLLMManager
from ..schemas.task import Task, TaskAnalysis, TaskResult
from .interfaces import Message, AIComponentProtocol
from ..core.session import Session
from ..core.llm_manager import LLMManager
from ..types import OrchestrationMessage, MessageType, Component
from ..types import TaskStatus, TaskExecutionResult

class BaseAIComponent(ABC):
    """全AIコンポーネントの共通基底クラス"""
    
    def __init__(self, session: Session, llm_manager: LLMManager) -> None:
        self.session = session
        self.llm_manager = llm_manager
        
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理する基本メソッド"""
        pass
        
    def _create_response(
        self,
        receiver: Component,
        content: Dict[str, Any],
        action: Optional[str] = None
    ) -> OrchestrationMessage:
        """応答メッセージを作成するヘルパーメソッド"""
        return OrchestrationMessage(
            type=MessageType.RESPONSE,
            sender=Component.WORKER,
            receiver=receiver,
            content=content,
            session_id=self.session.id,
            action=action
        )
        
    def _create_error_response(
        self,
        receiver: Component,
        error: str
    ) -> OrchestrationMessage:
        """エラーメッセージを作成するヘルパーメソッド"""
        return OrchestrationMessage(
            type=MessageType.ERROR,
            sender=Component.WORKER,
            receiver=receiver,
            content={"error": error},
            session_id=self.session.id
        )

class BaseDirectorAI(BaseAIComponent):
    """Director AIの基本実装"""
    
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージ処理の基本実装"""
        if message.type == MessageType.COMMAND:
            return self._process_command(message)
        elif message.type == MessageType.CONTROL:
            return self._process_control(message)
        return [self._create_error_response(
            message.receiver,
            "不明なメッセージタイプ"
        )]
    
    def _process_command(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """コマンドメッセージの処理"""
        try:
            action = message.content.get("action")
            if action == "start_process":
                self.control_process(message.content.get("task_id"))
                return [self._create_response(
                    message.sender,
                    {"status": "process_started"},
                    "process_started"
                )]
            elif action == "integrate":
                results = message.content.get("results", [])
                integrated = self.integrate_results(results)
                return [self._create_response(
                    message.sender,
                    {"integrated_result": integrated},
                    "integration_completed"
                )]
            return [self._create_error_response(
                message.sender,
                "不明なコマンド"
            )]
        except Exception as e:
            return [self._create_error_response(
                message.sender,
                str(e)
            )]
    
    def _process_control(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """制御メッセージの処理"""
        try:
            control_type = message.content.get("type")
            if control_type == "status_update":
                self.session.update_status(message.content.get("status"))
                return [self._create_response(
                    message.sender,
                    {"status": "updated"},
                    "status_updated"
                )]
            return [self._create_error_response(
                message.sender,
                "不明な制御タイプ"
            )]
        except Exception as e:
            return [self._create_error_response(
                message.sender,
                str(e)
            )]
    
    def control_process(self, task_id: str) -> None:
        """プロセス制御の基本実装"""
        pass
        
    def integrate_results(self, results: List[Any]) -> Any:
        """結果統合の基本実装"""
        pass

class AIComponent(ABC):
    """すべてのAIコンポーネントの基底クラス
    
    共通の機能とインターフェースを提供する。
    """
    
    def __init__(self, llm_manager: BaseLLMManager):
        self.llm_manager = llm_manager
        self.last_used = datetime.now()
        
    def update_last_used(self) -> None:
        """最終使用時刻を更新"""
        self.last_used = datetime.now()
        
    @abstractmethod
    async def process(self, task: Task) -> TaskResult:
        """タスクを処理し、結果を返す
        
        Args:
            task: 処理対象のタスク
            
        Returns:
            タスクの処理結果
        """
        pass

class IDirector(AIComponent, Protocol):
    """Director AIのインターフェース"""
    
    async def control_process(self, task_id: str) -> None:
        """プロセスを制御する"""
        pass
        
    async def integrate_results(self, results: List[TaskResult]) -> TaskResult:
        """複数の結果を統合する"""
        pass

class IPlanner(AIComponent, Protocol):
    """Planner AIのインターフェース"""
    
    async def analyze_task(self, task: Task) -> TaskAnalysis:
        """タスクを分析する"""
        pass
        
    async def generate_subtasks(self, analysis: TaskAnalysis) -> List[Task]:
        """サブタスクを生成する"""
        pass

class IWorker(AIComponent, Protocol):
    """Worker AIのインターフェース"""
    
    async def execute_task(self, task: Task) -> TaskResult:
        """タスクを実行する"""
        pass
        
    async def validate_result(self, result: TaskResult) -> bool:
        """結果を検証する"""
        pass

class IReviewer(AIComponent, Protocol):
    """Reviewer AIのインターフェース"""
    
    async def evaluate_result(self, result: TaskResult) -> float:
        """結果を評価する"""
        pass
        
    async def provide_feedback(self, result: TaskResult) -> str:
        """フィードバックを提供する"""
        pass 