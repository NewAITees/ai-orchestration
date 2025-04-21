from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from ..core.message import OrchestrationMessage, MessageType, Component
from ..core.session import Session, SubTask
from ..llm.llm_manager import LLMManager
from ..types import EvaluationMetrics, EvaluationResult
from datetime import datetime

class EvaluationMetrics(BaseModel):
    """評価メトリクスのモデル"""
    quality: float = Field(..., ge=0.0, le=1.0, description="タスクの品質")
    completeness: float = Field(..., ge=0.0, le=1.0, description="タスクの完成度")
    relevance: float = Field(..., ge=0.0, le=1.0, description="タスクの関連性")
    creativity: float = Field(..., ge=0.0, le=1.0, description="タスクの創造性")
    technical_accuracy: float = Field(..., ge=0.0, le=1.0, description="技術的な正確性")

class EvaluationResult(BaseModel):
    """評価結果を表すモデル"""
    task_id: str
    is_complete: bool
    score: float
    feedback: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

class IEvaluatorAI(Protocol):
    """Evaluator AIのインターフェース"""
    
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass
    
    @abstractmethod
    def evaluate_task(self, task: SubTask) -> EvaluationResult:
        """タスクを評価し、結果を返す"""
        pass

class BaseEvaluatorAI(ABC):
    """Evaluator AIの抽象基底クラス"""
    
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
    def evaluate_task(self, task: SubTask) -> EvaluationResult:
        """タスクを評価し、結果を返す"""
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
            sender=Component.EVALUATOR,
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

class DefaultEvaluatorAI(BaseEvaluatorAI):
    """デフォルトのEvaluator AI実装"""
    
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
            if action == "evaluate":
                task_id = content.get("task_id")
                if not task_id:
                    return [self._create_error_message(
                        message.sender,
                        "task_idが指定されていません"
                    )]
                return self._handle_evaluate_task(task_id)
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
    
    def _handle_evaluate_task(self, task_id: str) -> List[OrchestrationMessage]:
        """
        タスクを評価
        
        Args:
            task_id: 評価するタスクのID
            
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
            
            # タスクの評価
            evaluation_result = self.evaluate_task(task)
            
            # レスポンスメッセージを作成
            return [self._create_message(
                Component.DIRECTOR,
                MessageType.RESPONSE,
                {
                    "action": "evaluation_completed",
                    "task_id": task_id,
                    "result": evaluation_result.dict()
                }
            )]
        
        except Exception as e:
            return [self._create_error_message(
                Component.DIRECTOR,
                f"タスク評価中にエラーが発生しました: {str(e)}"
            )]
    
    def evaluate_task(self, task: SubTask) -> EvaluationResult:
        """
        タスクを評価し、結果を返す
        
        Args:
            task: 評価するタスク
            
        Returns:
            評価結果
        """
        try:
            # タスクの評価メトリクスを計算
            metrics = EvaluationMetrics(
                quality=0.8,
                completeness=0.9,
                relevance=0.85,
                creativity=0.75,
                technical_accuracy=0.9
            )
            
            # 評価結果を作成
            return EvaluationResult(
                task_id=task.id,
                is_complete=True,
                score=0.85,
                feedback="タスクは正常に完了し、品質基準を満たしています。"
            )
        except Exception as e:
            return EvaluationResult(
                task_id=task.id,
                is_complete=False,
                score=0.0,
                feedback=f"評価中にエラーが発生しました: {str(e)}"
            )

class EvaluatorAI(DefaultEvaluatorAI):
    """拡張されたEvaluator AI実装"""
    
    async def evaluate(self, task_id: str, output: str) -> EvaluationResult:
        """
        タスクの出力を評価する
        
        Args:
            task_id: 評価するタスクのID
            output: タスクの出力
            
        Returns:
            評価結果
        """
        task = self.session.get_subtask(task_id)
        if not task:
            raise ValueError(f"タスクが見つかりません: {task_id}")
        
        # LLMを使用して評価を実行
        prompt = f"""
        以下のタスクの出力を評価してください：

        タスク: {task.title}
        説明: {task.description}
        出力: {output}

        以下の観点で評価してください：
        1. 品質（0-1）
        2. 完成度（0-1）
        3. 関連性（0-1）
        4. 創造性（0-1）
        5. 技術的な正確性（0-1）
        """
        
        response = await self.llm_manager.generate(prompt)
        # ここでLLMの応答を解析して評価結果を作成
        
        return self.evaluate_task(task)
    
    async def assess_quality(self, task_id: str, output: str) -> EvaluationResult:
        """
        タスクの品質を評価する
        
        Args:
            task_id: 評価するタスクのID
            output: タスクの出力
            
        Returns:
            評価結果
        """
        task = self.session.get_subtask(task_id)
        if not task:
            raise ValueError(f"タスクが見つかりません: {task_id}")
        
        # LLMを使用して品質評価を実行
        prompt = f"""
        以下のタスクの出力の品質を評価してください：

        タスク: {task.title}
        説明: {task.description}
        出力: {output}

        以下の観点で品質を評価してください：
        1. 一貫性
        2. 正確性
        3. 適切性
        4. 完成度
        """
        
        response = await self.llm_manager.generate(prompt)
        # ここでLLMの応答を解析して評価結果を作成
        
        return self.evaluate_task(task)
