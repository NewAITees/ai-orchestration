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
import asyncio

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
    
    def __init__(self, session: Session, llm_manager: LLMManager, **kwargs) -> None:
        """
        初期化
        Args:
            session: 関連付けられたセッション
            llm_manager: LLMマネージャー
            **kwargs: 追加の設定パラメータ
        """
        super().__init__(session, llm_manager, **kwargs)
        self.active_tasks: Dict[TaskID, asyncio.Task] = {}
    
    def _process_command(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """
        コマンドメッセージを処理
        Args:
            message: 処理するメッセージ
        Returns:
            応答メッセージのリスト
        """
        content = message.content
        action = content.get("action")
        
        try:
            if action == "execute":
                task_data = content.get("task")
                context = content.get("context")
                if not task_data:
                    raise ValueError("execute コマンドには 'task' データが必要です")
                
                task = SubTask.model_validate(task_data)
                result = self.execute_task(task, context)
                
                return [self._create_response(
                    message.sender,
                    {"result": result.model_dump()},
                    "execution_completed"
                )]
            elif action == "stop":
                task_id = content.get("task_id")
                if not task_id:
                    raise ValueError("stop コマンドには 'task_id' が必要です")
                
                self.stop_execution(task_id)
                
                return [self._create_response(
                    message.sender,
                    {"status": "stopped", "task_id": task_id},
                    "execution_stopped"
                )]
            else:
                return [self._create_error_response(
                    message.sender,
                    f"サポートされていないアクション: {action}",
                    "unsupported_action"
                )]
        except Exception as e:
            return [self._create_error_response(
                message.sender,
                f"コマンド処理中にエラーが発生しました: {str(e)}",
                f"{action}_failed" if action else "command_failed"
            )]
    
    def execute_task(self, task: SubTask, context: Optional[Dict[str, Any]] = None) -> TaskExecutionResult:
        """
        タスクを実行
        Args:
            task: 実行するタスク
            context: 実行コンテキスト（オプション）
        Returns:
            実行結果
        """
        try:
            # タスクの状態を実行中に更新
            self.update_status(task.id, TaskStatus.EXECUTING)
            
            # LLMを使用してタスクを実行
            prompt = self._create_execution_prompt(task, context)
            llm_response = self.llm_manager.generate(prompt)
            
            # 実行結果を生成
            result = TaskExecutionResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output=llm_response,
                execution_time=datetime.now().isoformat(),
                metadata={"context": context} if context else {}
            )
            
            # タスクの状態を更新
            self.update_status(
                task.id,
                TaskStatus.COMPLETED,
                {"result": result.model_dump()}
            )
            
            return result
            
        except Exception as e:
            error_msg = f"タスク実行中にエラーが発生しました: {str(e)}"
            print(f"[Worker] {error_msg}")
            self.update_status(task.id, TaskStatus.FAILED, {"error": error_msg})
            raise
    
    def stop_execution(self, task_id: TaskID) -> None:
        """
        タスクの実行を停止
        Args:
            task_id: 停止するタスクのID
        """
        try:
            # 実行中のタスクを停止
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                task.cancel()
                del self.active_tasks[task_id]
                
                # タスクの状態を更新
                self.update_status(
                    task_id,
                    TaskStatus.CANCELLED,
                    {"message": "タスクの実行が停止されました"}
                )
            else:
                print(f"[Worker] タスク {task_id} は実行中ではありません")
        
        except Exception as e:
            error_msg = f"タスク停止中にエラーが発生しました: {str(e)}"
            print(f"[Worker] {error_msg}")
            self.update_status(task_id, TaskStatus.FAILED, {"error": error_msg})
            raise
    
    def _create_execution_prompt(self, task: SubTask, context: Optional[Dict[str, Any]]) -> str:
        """
        タスク実行用のプロンプトを作成
        Args:
            task: 実行するタスク
            context: 実行コンテキスト
        Returns:
            生成されたプロンプト
        """
        prompt = f"""
        以下のタスクを実行してください：
        
        タイトル: {task.title}
        説明: {task.description}
        """
        
        if context:
            prompt += "\n\n実行コンテキスト:"
            for key, value in context.items():
                prompt += f"\n{key}: {value}"
        
        prompt += """
        
        以下の形式で結果を提供してください：
        1. 実行した処理の説明
        2. 生成された成果物
        3. 実行中に発生した問題（もしあれば）
        4. 次のステップへの提案
        """
        
        return prompt 