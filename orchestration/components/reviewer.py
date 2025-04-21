from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Protocol
from pydantic import BaseModel, Field
from ..core.message import OrchestrationMessage, MessageType, Component
from ..core.session import Session, SubTask

class ReviewResult(BaseModel):
    """レビュー結果のモデル"""
    
    task_id: str = Field(..., description="タスクの一意な識別子")
    status: str = Field(..., description="レビューの状態")
    score: float = Field(..., description="タスクの評価スコア")
    feedback: str = Field(..., description="タスクに関するフィードバック")
    suggestions: List[str] = Field(default_factory=list, description="改善提案のリスト")
    metrics: Dict[str, float] = Field(default_factory=dict, description="評価指標")

class IReviewerAI(Protocol):
    """Reviewer AIのインターフェース"""
    
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass
    
    @abstractmethod
    def review_task(self, task: SubTask) -> ReviewResult:
        """タスクをレビューし、結果を返す"""
        pass

class BaseReviewerAI(ABC):
    """Reviewer AIの抽象基底クラス"""
    
    def __init__(self, session: Session):
        """
        初期化
        
        Args:
            session: 関連付けられたセッション
        """
        self.session = session
        self.current_task: Optional[SubTask] = None
    
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass
    
    @abstractmethod
    def review_task(self, task: SubTask) -> ReviewResult:
        """タスクをレビューし、結果を返す"""
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
            sender=Component.REVIEWER,
            receiver=receiver,
            content=content,
            session_id=self.session.id
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

class DefaultReviewerAI(BaseReviewerAI):
    """デフォルトのReviewer AI実装"""
    
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
            if action == "review_task":
                return self._handle_review_task(content.get("task_id"))
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
    
    def _handle_review_task(self, task_id: str) -> List[OrchestrationMessage]:
        """
        タスクをレビュー
        
        Args:
            task_id: レビューするタスクのID
            
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
            
            # タスクのレビュー
            review_result = self.review_task(task)
            
            # レスポンスメッセージを作成
            return [self._create_message(
                Component.DIRECTOR,
                MessageType.RESPONSE,
                {
                    "action": "review_completed",
                    "task_id": task_id,
                    "result": review_result.dict()
                }
            )]
        
        except Exception as e:
            return [self._create_error_message(
                Component.DIRECTOR,
                f"タスクレビュー中にエラーが発生しました: {str(e)}"
            )]
    
    def review_task(self, task: SubTask) -> ReviewResult:
        """
        タスクをレビューし、結果を返す
        
        Args:
            task: レビューするタスク
            
        Returns:
            レビュー結果
        """
        # 実際の実装では、LLMを使用してタスクをレビューする
        # ここではダミーの実装を提供
        
        # タスクの内容に基づいてレビュー
        if "キャラクター設定" in task.title:
            feedback = "キャラクターの設定は適切ですが、背景ストーリーの詳細を追加するとより深みが出るでしょう。"
            suggestions = [
                "各キャラクターの具体的な目標を追加する",
                "キャラクター間の関係性をより詳細に描写する",
                "過去の重要な出来事を追加する"
            ]
            metrics = {
                "completeness": 0.8,
                "consistency": 0.9,
                "depth": 0.7
            }
        elif "ストーリー構成" in task.title:
            feedback = "ストーリーの構成は基本的に良好ですが、クライマックスシーンの描写を強化するとより効果的でしょう。"
            suggestions = [
                "クライマックスシーンの詳細な描写を追加する",
                "各セクションの長さのバランスを調整する",
                "伏線の配置を検討する"
            ]
            metrics = {
                "structure": 0.85,
                "pacing": 0.8,
                "impact": 0.75
            }
        else:
            feedback = "タスクは基本的な要件を満たしていますが、より詳細な内容を追加することで改善できます。"
            suggestions = [
                "より具体的な例を追加する",
                "説明の詳細度を上げる",
                "関連する要素を追加する"
            ]
            metrics = {
                "quality": 0.8,
                "completeness": 0.7,
                "clarity": 0.85
            }
        
        return ReviewResult(
            task_id=task.id,
            status="COMPLETED",
            score=0.8,  # ダミーのスコア
            feedback=feedback,
            suggestions=suggestions,
            metrics=metrics
        ) 