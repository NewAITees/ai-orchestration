from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from ..core.message import MessageType, Component
from ..core.session import Session
from ..types import (
    TaskStatus, TaskExecutionResult, IWorkerAI,
    OrchestrationMessage, SubTask
)
from .llm_manager import LLMManager

class BaseWorkerAI(ABC, IWorkerAI):
    """Worker AIの抽象基底クラス"""
    
    def __init__(self, session: Session, llm_manager: LLMManager) -> None:
        """
        初期化
        
        Args:
            session: 関連付けられたセッション
            llm_manager: LLMマネージャー
        """
        self.session = session
        self.llm_manager = llm_manager
        self.current_task: Optional[SubTask] = None
    
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass
    
    @abstractmethod
    def execute_task(self, task: SubTask) -> TaskExecutionResult:
        """タスクを実行し、結果を返す"""
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
            sender=Component.WORKER,
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

class DefaultWorkerAI(BaseWorkerAI):
    """デフォルトのWorker AI実装"""
    
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
            if action == "execute_task":
                task_id = content.get("task_id")
                if not task_id:
                    return [self._create_error_message(
                        message.sender,
                        "task_idが指定されていません"
                    )]
                return self._handle_execute_task(task_id)
            elif action == "stop_task":
                return self._handle_stop_task()
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
    
    def _handle_execute_task(self, task_id: str) -> List[OrchestrationMessage]:
        """
        タスクを実行
        
        Args:
            task_id: 実行するタスクのID
            
        Returns:
            応答メッセージのリスト
        """
        try:
            # タスクの取得
            task = self.session.get_subtask(task_id)
            if not task:
                return [self._create_error_message(
                    Component.DIRECTOR,
                    f"タスクが見つかりません: {task_id}"
                )]
            
            # タスクの状態を更新
            task.update_status(TaskStatus.EXECUTING)
            self.current_task = task
            
            # タスクの実行
            execution_result = self.execute_task(task)
            
            # タスクの状態を更新
            task.update_status(TaskStatus.COMPLETED)
            task.result = execution_result.result
            
            # レスポンスメッセージを作成
            return [self._create_message(
                Component.DIRECTOR,
                MessageType.RESPONSE,
                {
                    "action": "task_completed",
                    "task_id": task_id,
                    "result": execution_result.dict()
                }
            )]
        
        except Exception as e:
            if self.current_task:
                self.current_task.update_status(TaskStatus.FAILED)
            return [self._create_error_message(
                Component.DIRECTOR,
                f"タスク実行中にエラーが発生しました: {str(e)}"
            )]
    
    def _handle_stop_task(self) -> List[OrchestrationMessage]:
        """
        現在実行中のタスクを停止
        
        Returns:
            応答メッセージのリスト
        """
        if not self.current_task:
            return [self._create_error_message(
                Component.DIRECTOR,
                "実行中のタスクがありません"
            )]
        
        try:
            # タスクの状態を更新
            self.current_task.update_status(TaskStatus.CANCELLED)
            
            # レスポンスメッセージを作成
            return [self._create_message(
                Component.DIRECTOR,
                MessageType.RESPONSE,
                {
                    "action": "task_stopped",
                    "task_id": self.current_task.id
                }
            )]
        
        except Exception as e:
            return [self._create_error_message(
                Component.DIRECTOR,
                f"タスク停止中にエラーが発生しました: {str(e)}"
            )]
    
    def execute_task(self, task: SubTask) -> TaskExecutionResult:
        """
        タスクを実行し、結果を返す
        
        Args:
            task: 実行するタスク
            
        Returns:
            タスクの実行結果
        """
        try:
            # タスクの種類に応じた処理を実行
            prompt = f"""
            以下のタスクを実行してください：
            
            タスク: {task.title}
            説明: {task.description}
            要件: {task.requirements if hasattr(task, 'requirements') else []}
            制約: {task.constraints if hasattr(task, 'constraints') else []}
            
            出力形式:
            1. 実行結果
            2. フィードバック
            3. 評価指標
            """
            
            response = self.llm_manager.get_completion(prompt)
            
            # 現在はダミーの実装を提供
            # 実際の実装では、LLMの応答を解析して適切な値を設定
            return TaskExecutionResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                result={"output": response},
                feedback="タスクが正常に完了しました",
                metrics={"completion_rate": 1.0}
            )
        except Exception as e:
            return TaskExecutionResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                result={"error": str(e)},
                feedback=f"タスク実行中にエラーが発生しました: {str(e)}",
                metrics={"completion_rate": 0.0}
            ) 