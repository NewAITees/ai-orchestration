from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from ..core.message import OrchestrationMessage, MessageType, Component
from ..core.session import Session, SubTask
from ..types import TaskStatus, TaskStatusModel
from .planner import DefaultPlannerAI
from .worker import DefaultWorkerAI
from .evaluator import DefaultEvaluatorAI
from .llm_manager import LLMManager

class IDirectorAI(Protocol):
    """Director AIのインターフェース"""
    
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass
    
    @abstractmethod
    def get_task_status(self, task_id: str) -> Optional[TaskStatusModel]:
        """指定されたタスクの状態を取得する"""
        pass
    
    @abstractmethod
    def update_task_status(self, task_id: str, status: str, progress: Optional[float] = None, error: Optional[str] = None) -> None:
        """タスクの状態を更新する"""
        pass

class BaseDirectorAI(ABC):
    """Director AIの抽象基底クラス"""
    
    def __init__(self, session: Session, llm_manager: LLMManager) -> None:
        """
        初期化
        
        Args:
            session: 関連付けられたセッション
            llm_manager: LLMマネージャー
        """
        self.session = session
        self.llm_manager = llm_manager
        self.planner = DefaultPlannerAI(session, llm_manager)
        self.worker = DefaultWorkerAI(session, llm_manager)
        self.evaluator = DefaultEvaluatorAI(session, llm_manager)
        self.task_statuses: Dict[str, TaskStatusModel] = {}
    
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatusModel]:
        """指定されたタスクの状態を取得する"""
        return self.task_statuses.get(task_id)
    
    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: Optional[float] = None,
        error: Optional[str] = None
    ) -> None:
        """
        タスクの状態を更新する
        
        Args:
            task_id: 更新するタスクのID
            status: 新しい状態
            progress: 進捗状況（オプション）
            error: エラーメッセージ（オプション）
        """
        if task_id in self.task_statuses:
            task_status = self.task_statuses[task_id]
            task_status.status = status
            if progress is not None:
                task_status.progress = progress
            if error is not None:
                task_status.error = error
    
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
            sender=Component.DIRECTOR,
            receiver=receiver,
            content=content,
            session_id=self.session.id,
            action=content.get("action", "")
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

class DefaultDirectorAI(BaseDirectorAI):
    """デフォルトのDirector AI実装"""
    
    def __init__(self, session: Session, llm_manager: LLMManager) -> None:
        """
        初期化
        
        Args:
            session: 関連付けられたセッション
            llm_manager: LLMマネージャー
        """
        super().__init__(session, llm_manager)
        self.planner = DefaultPlannerAI(session, llm_manager)
        self.worker = DefaultWorkerAI(session, llm_manager)
        self.evaluator = DefaultEvaluatorAI(session, llm_manager)
        self.task_statuses: Dict[str, TaskStatusModel] = {}
    
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """
        メッセージを処理し、応答メッセージのリストを返す
        
        Args:
            message: 処理するメッセージ
            
        Returns:
            応答メッセージのリスト
        """
        if message.type != MessageType.COMMAND:
            return [self._create_error_message(
                message.sender,
                f"サポートされていないメッセージタイプ: {message.type}"
            )]
        
        content = message.content
        action = content.get("action")
        
        try:
            if action == "start_session":
                return self._handle_start_session()
            elif action == "execute_task":
                return self._handle_execute_task(content.get("task_id"))
            elif action == "evaluate_task":
                return self._handle_evaluate_task(content.get("task_id"))
            else:
                return [self._create_error_message(
                    message.sender,
                    f"サポートされていないアクション: {action}"
                )]
        except Exception as e:
            return [self._create_error_message(
                message.sender,
                f"メッセージ処理中にエラーが発生しました: {str(e)}"
            )]
    
    def _handle_start_session(self) -> List[OrchestrationMessage]:
        """
        セッションを開始し、タスク分析を実行
        
        Returns:
            応答メッセージのリスト
        """
        try:
            # Planner AIにタスク分析を依頼
            analysis_messages = self.planner.process_message(
                self._create_message(
                    Component.PLANNER,
                    MessageType.COMMAND,
                    {"action": "analyze_task"}
                )
            )
            return analysis_messages
        except Exception as e:
            return [self._create_error_message(
                Component.CLIENT,
                f"セッション開始中にエラーが発生しました: {str(e)}"
            )]
    
    def _handle_execute_task(self, task_id: str) -> List[OrchestrationMessage]:
        """
        タスクを実行
        
        Args:
            task_id: 実行するタスクのID
            
        Returns:
            応答メッセージのリスト
        """
        try:
            # タスクの状態を更新
            self.update_task_status(task_id, TaskStatus.EXECUTING)
            
            # Worker AIにタスク実行を依頼
            execution_messages = self.worker.process_message(
                self._create_message(
                    Component.WORKER,
                    MessageType.COMMAND,
                    {
                        "action": "execute_task",
                        "task_id": task_id
                    }
                )
            )
            return execution_messages
        except Exception as e:
            self.update_task_status(task_id, TaskStatus.FAILED, error=str(e))
            return [self._create_error_message(
                Component.CLIENT,
                f"タスク実行中にエラーが発生しました: {str(e)}"
            )]
    
    def _handle_evaluate_task(self, task_id: str) -> List[OrchestrationMessage]:
        """
        タスクの評価を実行
        
        Args:
            task_id: 評価するタスクのID
            
        Returns:
            応答メッセージのリスト
        """
        try:
            # タスクの状態を更新
            self.update_task_status(task_id, TaskStatus.REVIEWING)
            
            # Evaluator AIにタスク評価を依頼
            evaluation_messages = self.evaluator.process_message(
                self._create_message(
                    Component.EVALUATOR,
                    MessageType.COMMAND,
                    {
                        "action": "evaluate_task",
                        "task_id": task_id
                    }
                )
            )
            return evaluation_messages
        except Exception as e:
            self.update_task_status(task_id, TaskStatus.FAILED, error=str(e))
            return [self._create_error_message(
                Component.CLIENT,
                f"タスク評価中にエラーが発生しました: {str(e)}"
            )] 