from typing import Dict, Any, List, Optional
from ..core.message import MessageType, Component
from ..core.session import Session
from ..types import (
    TaskStatus, TaskExecutionResult, IWorkerAI,
    OrchestrationMessage, SubTask, BaseAIComponent
)
from .llm_manager import LLMManager
from .base import BaseAIComponent

class WorkerAI(BaseAIComponent):
    """WorkerAI"""
    component_type = Component.WORKER
    
    def __init__(self, session: Session, llm_manager: LLMManager) -> None:
        """
        初期化
        Args:
            session: 関連付けられたセッション
            llm_manager: LLMマネージャー
        """
        super().__init__(session)
        self.llm_manager = llm_manager
    
    def _process_command(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """コマンド処理"""
        content = message.content
        action = content.get("action")
        
        try:
            if action == "execute_task":
                task_id = content.get("task_id")
                if not task_id:
                    return [self._create_error_response(
                        message.sender,
                        "task_id が指定されていません"
                    )]
                
                # タスク実行
                task = self.session.get_subtask(task_id)
                if not task:
                    return [self._create_error_response(
                        message.sender,
                        f"タスクが見つかりません: {task_id}"
                    )]
                
                context = content.get("context", {})
                result = self.execute_task(task, context)
                
                return [self._create_response(
                    message.sender,
                    {"result": result},
                    "task_executed"
                )]
            else:
                return [self._create_error_response(
                    message.sender,
                    f"未対応のアクション: {action}"
                )]
        except Exception as e:
            return [self._create_error_response(
                message.sender,
                f"コマンド処理中にエラーが発生しました: {str(e)}"
            )]
    
    def execute_task(self, task, context=None) -> Dict[str, Any]:
        """タスク実行"""
        context = context or {}
        
        # LLMを使用したタスク実行
        if self.llm_manager:
            prompt = f"""
            以下のタスクを実行してください:
            タイトル: {task.title}
            説明: {task.description}
            要件: {', '.join(task.requirements) if task.requirements else 'なし'}
            """
            # 実際のLLM呼び出しはここで行う
        
        # サンプルの実行結果（実際はLLMの出力）
        result_content = f"{task.title}の実行結果：タスクが完了しました。"
        
        task.update_status(TaskStatus.COMPLETED)
        task.result = result_content
        
        return {
            "content": result_content,
            "status": TaskStatus.COMPLETED,
            "requirements_met": [req for req in (task.requirements or [])]
        } 