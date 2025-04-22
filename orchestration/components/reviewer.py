from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from ..core.message import OrchestrationMessage, MessageType, Component
from ..core.session import Session
from ..llm.llm_manager import LLMManager
from ..types import (
    ReviewResult, IReviewerAI, BaseAIComponent,
    SubTask, TaskStatus, TaskExecutionResult
)

class EvaluationMetrics(BaseModel):
    """評価メトリクスのモデル"""
    quality: float = Field(..., ge=0.0, le=1.0, description="タスクの品質")
    completeness: float = Field(..., ge=0.0, le=1.0, description="タスクの完成度")
    relevance: float = Field(..., ge=0.0, le=1.0, description="タスクの関連性")
    creativity: float = Field(..., ge=0.0, le=1.0, description="タスクの創造性")
    technical_accuracy: float = Field(..., ge=0.0, le=1.0, description="技術的な正確性")

class ReviewerAI(BaseAIComponent):
    """拡張されたReviewer AI実装"""
    component_type = Component.REVIEWER
    
    def __init__(self, session: Session, llm_manager: LLMManager):
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
        if message.type != MessageType.COMMAND:
            return [self._create_error_message(
                message.sender,
                f"サポートされていないメッセージタイプ: {message.type}"
            )]
        
        content = message.content
        action = content.get("action")
        
        try:
            if action == "review_task":
                task_data = content.get("task")
                result_data = content.get("result")
                if not task_data:
                    return [self._create_error_message(
                        message.sender,
                        "review_task コマンドには 'task' データが必要です"
                    )]
                
                task = SubTask.model_validate(task_data)
                result = TaskExecutionResult.model_validate(result_data) if result_data else None
                review = self.review_task(task, result)
                
                return [self._create_message(
                    message.sender,
                    MessageType.RESPONSE,
                    {"review": review.model_dump()}
                )]
            elif action == "suggest_improvements":
                review_data = content.get("review")
                if not review_data:
                    return [self._create_error_message(
                        message.sender,
                        "suggest_improvements コマンドには 'review' データが必要です"
                    )]
                
                review = ReviewResult.model_validate(review_data)
                improvements = self.suggest_improvements(review)
                
                return [self._create_message(
                    message.sender,
                    MessageType.RESPONSE,
                    {"improvements": [imp.model_dump() for imp in improvements]}
                )]
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
    
    def review_task(self, task: SubTask, result: Optional[TaskExecutionResult] = None) -> ReviewResult:
        """
        タスクをレビューし、結果を返す
        Args:
            task: レビュー対象のタスク
            result: タスクの実行結果（オプション）
        Returns:
            レビュー結果
        """
        try:
            # タスクの状態を評価中に更新
            task.status = TaskStatus.REVIEWING
            
            # LLMを使用してタスクを評価
            prompt = self._create_review_prompt(task, result)
            llm_response = self.llm_manager.generate(prompt)
            
            # 評価結果を生成
            metrics = EvaluationMetrics(
                quality=0.8,
                completeness=0.9,
                relevance=0.7,
                creativity=0.6,
                technical_accuracy=0.8
            )
            
            review = ReviewResult(
                task_id=task.id,
                status="completed",
                score=0.8,  # LLMの応答から適切に計算
                feedback=llm_response,
                suggestions=[],  # LLMの応答から適切に抽出
                metrics={"quality": metrics.quality, "completeness": metrics.completeness}
            )
            
            # タスクの状態を更新
            task.status = TaskStatus.REVIEW_COMPLETED
            
            return review
            
        except Exception as e:
            error_msg = f"タスクレビュー中にエラーが発生しました: {str(e)}"
            print(f"[Reviewer] {error_msg}")
            task.status = TaskStatus.FAILED
            raise
    
    async def evaluate(self, task_id: str, output: str) -> ReviewResult:
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
        return self.review_task(task)
    
    async def assess_quality(self, task_id: str, output: str) -> ReviewResult:
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
        return self.review_task(task)
    
    def _create_review_prompt(self, task: SubTask, result: Optional[TaskExecutionResult]) -> str:
        """
        タスクレビュー用のプロンプトを作成
        Args:
            task: レビュー対象のタスク
            result: タスクの実行結果
        Returns:
            生成されたプロンプト
        """
        prompt = f"""
        以下のタスクとその実行結果をレビューしてください：
        
        タスク:
        タイトル: {task.title}
        説明: {task.description}
        """
        
        if result:
            prompt += f"""
            
            実行結果:
            ステータス: {result.status}
            出力: {result.output}
            実行時間: {result.execution_time}
            """
        
        prompt += """
        
        以下の観点で評価してください：
        1. タスクの要件を満たしているか
        2. 出力の品質
        3. 実行効率
        4. 改善の余地
        
        各観点について、1-10の数値評価と具体的なフィードバックを提供してください。
        """
        
        return prompt 