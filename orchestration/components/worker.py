from typing import Dict, Any, List, Optional
from ..core.message import MessageType, Component
from ..core.session import Session
from ..types import (
    TaskStatus, TaskExecutionResult, IWorkerAI,
    OrchestrationMessage, SubTask, BaseAIComponent
)
from .llm_manager import LLMManager

class DefaultWorkerAI(BaseAIComponent):
    """Worker AIのデフォルト実装"""
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
    
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass  # 実装は省略
    
    def execute_task(self, task: SubTask) -> TaskExecutionResult:
        """タスクを実行し、結果を返す"""
        pass  # 実装は省略 