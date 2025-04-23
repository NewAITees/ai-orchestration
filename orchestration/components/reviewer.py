import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum, auto
from dataclasses import dataclass

from ..core.message import OrchestrationMessage, MessageType, Component
from ..core.session import Session
from ..llm.llm_manager import LLMManager
from ..types import (
    ReviewResult, IReviewerAI, BaseAIComponent,
    SubTask, TaskStatus, TaskExecutionResult
)

logger = logging.getLogger(__name__)

class TaskType(Enum):
    """タスクタイプの定義"""
    CREATIVE = auto()
    CODING = auto()
    ANALYSIS = auto()
    GENERIC = auto()

class EvaluationMetrics(BaseModel):
    """評価メトリクスのモデル"""
    quality: float = Field(..., ge=0.0, le=1.0, description="タスクの品質")
    completeness: float = Field(..., ge=0.0, le=1.0, description="タスクの完成度")
    relevance: float = Field(..., ge=0.0, le=1.0, description="タスクの関連性")
    creativity: float = Field(..., ge=0.0, le=1.0, description="タスクの創造性")
    technical_accuracy: float = Field(..., ge=0.0, le=1.0, description="技術的な正確性")

@dataclass
class EvaluationContext:
    """評価コンテキスト"""
    task_id: str
    task_title: str
    task_description: str
    requirements: List[str]
    result_content: str
    metrics: EvaluationMetrics

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
        self._task_type_keywords = {
            TaskType.CREATIVE: ["創作", "小説", "物語", "キャラクター", "ストーリー", "シナリオ", "creative", "story", "character"],
            TaskType.CODING: ["コード", "プログラム", "実装", "code", "programming", "implementation"],
            TaskType.ANALYSIS: ["分析", "調査", "研究", "analysis", "research"]
        }
    
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        if message.type != MessageType.COMMAND:
            return [self._create_error_message(
                message.sender,
                f"サポートされていないメッセージタイプ: {message.type}"
            )]
        
        content = message.content
        action = content.get("action")
        
        action_handlers = {
            "review_task": self._handle_review_task,
            "suggest_improvements": self._handle_suggest_improvements,
            "evaluate_task": self._handle_evaluate_task
        }
        
        try:
            handler = action_handlers.get(action)
            if not handler:
                return [self._create_error_message(
                    message.sender,
                    f"サポートされていないアクション: {action}"
                )]
            
            return handler(message)
            
        except Exception as e:
            logger.error(f"メッセージ処理中にエラーが発生: {str(e)}", exc_info=True)
            return [self._create_error_message(
                message.sender,
                f"メッセージ処理中にエラーが発生しました: {str(e)}"
            )]
    
    def _handle_review_task(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """review_taskアクションの処理"""
        content = message.content
        task_data = content.get("task")
        result_data = content.get("result")
        
        if not task_data:
            return [self._create_error_message(
                message.sender,
                "review_task コマンドには 'task' データが必要です"
            )]
        
        try:
            task = SubTask.model_validate(task_data)
            result = TaskExecutionResult.model_validate(result_data) if result_data else None
            review = self.review_task(task, result)
            
            return [self._create_message(
                message.sender,
                MessageType.RESPONSE,
                {"review": review.model_dump()}
            )]
        except Exception as e:
            logger.error(f"タスクレビュー中にエラーが発生: {str(e)}", exc_info=True)
            return [self._create_error_message(
                message.sender,
                f"タスクレビュー中にエラーが発生しました: {str(e)}"
            )]
    
    def _handle_suggest_improvements(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """suggest_improvementsアクションの処理"""
        content = message.content
        review_data = content.get("review")
        
        if not review_data:
            return [self._create_error_message(
                message.sender,
                "suggest_improvements コマンドには 'review' データが必要です"
            )]
        
        try:
            review = ReviewResult.model_validate(review_data)
            improvements = self.suggest_improvements(review)
            
            return [self._create_message(
                message.sender,
                MessageType.RESPONSE,
                {"improvements": [imp.model_dump() for imp in improvements]}
            )]
        except Exception as e:
            logger.error(f"改善提案生成中にエラーが発生: {str(e)}", exc_info=True)
            return [self._create_error_message(
                message.sender,
                f"改善提案生成中にエラーが発生しました: {str(e)}"
            )]
    
    def _handle_evaluate_task(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """evaluate_taskアクションの処理"""
        content = message.content
        task_id = content.get("task_id")
        output = content.get("output")
        
        if not task_id or not output:
            return [self._create_error_message(
                message.sender,
                "evaluate_task コマンドには 'task_id' と 'output' が必要です"
            )]
        
        try:
            evaluation = self.evaluate_task(task_id, output)
            return [self._create_message(
                message.sender,
                MessageType.RESPONSE,
                {"evaluation": evaluation.model_dump()}
            )]
        except Exception as e:
            logger.error(f"タスク評価中にエラーが発生: {str(e)}", exc_info=True)
            return [self._create_error_message(
                message.sender,
                f"タスク評価中にエラーが発生しました: {str(e)}"
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
        logger.info(f"タスクレビュー開始: {task.id} - {task.title}")
        
        try:
            # タスクの状態を評価中に更新
            task.status = TaskStatus.REVIEWING
            
            # タスクタイプを判定
            task_type = self._determine_task_type(task)
            template_id = f"reviewer/{task_type.name.lower()}_review"
            
            # 評価コンテキストを作成
            context = self._create_evaluation_context(task, result)
            
            # LLMを使用してタスクを評価
            llm_response = self.llm_manager.generate_with_template(template_id, context.__dict__)
            
            # 評価結果を生成
            metrics = self._calculate_metrics(task, result, llm_response)
            suggestions = self._extract_suggestions(llm_response)
            
            review = ReviewResult(
                task_id=task.id,
                status="completed",
                score=self._calculate_overall_score(metrics),
                feedback=llm_response,
                suggestions=suggestions,
                metrics=metrics.dict()
            )
            
            # タスクの状態を更新
            task.status = TaskStatus.REVIEW_COMPLETED
            logger.info(f"タスクレビュー完了: {task.id} スコア: {review.score}")
            
            return review
            
        except Exception as e:
            error_msg = f"タスクレビュー中にエラーが発生しました: {str(e)}"
            logger.error(error_msg, exc_info=True)
            task.status = TaskStatus.FAILED
            raise
    
    def evaluate_task(self, task_id: str, output: str) -> ReviewResult:
        """
        タスクの出力を評価する
        Args:
            task_id: 評価するタスクのID
            output: タスクの出力
        Returns:
            評価結果
        """
        logger.info(f"タスク評価開始: {task_id}")
        
        task = self.session.get_subtask(task_id)
        if not task:
            raise ValueError(f"タスクが見つかりません: {task_id}")
        
        try:
            # タスクタイプを判定
            task_type = self._determine_task_type(task)
            template_id = f"reviewer/{task_type.name.lower()}_evaluation"
            
            # 評価コンテキストを作成
            context = self._create_evaluation_context(task, None)
            context.result_content = output
            
            # LLMを使用して評価を実行
            llm_response = self.llm_manager.generate_with_template(template_id, context.__dict__)
            
            # 評価結果を生成
            metrics = self._calculate_metrics(task, None, llm_response)
            suggestions = self._extract_suggestions(llm_response)
            
            review = ReviewResult(
                task_id=task.id,
                status="completed",
                score=self._calculate_overall_score(metrics),
                feedback=llm_response,
                suggestions=suggestions,
                metrics=metrics.dict()
            )
            
            logger.info(f"タスク評価完了: {task_id} スコア: {review.score}")
            return review
            
        except Exception as e:
            error_msg = f"タスク評価中にエラーが発生しました: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise
    
    def suggest_improvements(self, review: ReviewResult) -> List[Dict[str, Any]]:
        """
        レビュー結果に基づいて改善提案を生成する
        Args:
            review: レビュー結果
        Returns:
            改善提案のリスト
        """
        logger.info(f"改善提案生成開始: {review.task_id}")
        
        try:
            template_id = "reviewer/improvement_suggestion"
            
            # LLMを使用して改善提案を生成
            llm_response = self.llm_manager.generate_with_template(
                template_id,
                {"review": review.dict()}
            )
            
            # 改善提案を抽出
            improvements = self._extract_improvements(llm_response)
            
            logger.info(f"改善提案生成完了: {review.task_id} 提案数: {len(improvements)}")
            return improvements
            
        except Exception as e:
            error_msg = f"改善提案生成中にエラーが発生しました: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise
    
    def _determine_task_type(self, task: SubTask) -> TaskType:
        """タスクタイプを判定"""
        if hasattr(task, 'task_type') and task.task_type:
            try:
                return TaskType[task.task_type.upper()]
            except KeyError:
                pass
        
        title = task.title.lower() if task.title else ""
        description = task.description.lower() if task.description else ""
        
        for task_type, keywords in self._task_type_keywords.items():
            if any(keyword in title or keyword in description for keyword in keywords):
                return task_type
        
        return TaskType.GENERIC
    
    def _create_evaluation_context(
        self,
        task: SubTask,
        result: Optional[TaskExecutionResult]
    ) -> EvaluationContext:
        """評価コンテキストを作成"""
        result_content = ""
        if result:
            result_content = result.result if isinstance(result.result, str) else str(result.result)
        
        return EvaluationContext(
            task_id=task.id,
            task_title=task.title,
            task_description=task.description,
            requirements=task.requirements if hasattr(task, 'requirements') else [],
            result_content=result_content,
            metrics=EvaluationMetrics(
                quality=0.0,
                completeness=0.0,
                relevance=0.0,
                creativity=0.0,
                technical_accuracy=0.0
            )
        )
    
    def _calculate_metrics(
        self,
        task: SubTask,
        result: Optional[TaskExecutionResult],
        llm_response: str
    ) -> EvaluationMetrics:
        """評価メトリクスを計算"""
        # LLMの応答から評価メトリクスを抽出
        try:
            metrics_data = self.llm_manager.parse_json_response(llm_response).get("metrics", {})
            return EvaluationMetrics(
                quality=metrics_data.get("quality", 0.8),
                completeness=metrics_data.get("completeness", 0.8),
                relevance=metrics_data.get("relevance", 0.8),
                creativity=metrics_data.get("creativity", 0.8),
                technical_accuracy=metrics_data.get("technical_accuracy", 0.8)
            )
        except Exception as e:
            logger.warning(f"メトリクス抽出に失敗: {str(e)}", exc_info=True)
            return EvaluationMetrics(
                quality=0.8,
                completeness=0.8,
                relevance=0.8,
                creativity=0.8,
                technical_accuracy=0.8
            )
    
    def _calculate_overall_score(self, metrics: EvaluationMetrics) -> float:
        """総合スコアを計算"""
        weights = {
            "quality": 0.3,
            "completeness": 0.3,
            "relevance": 0.2,
            "creativity": 0.1,
            "technical_accuracy": 0.1
        }
        
        return sum([
            getattr(metrics, metric) * weight
            for metric, weight in weights.items()
        ])
    
    def _extract_suggestions(self, llm_response: str) -> List[str]:
        """LLMの応答から改善提案を抽出"""
        try:
            response_data = self.llm_manager.parse_json_response(llm_response)
            return response_data.get("suggestions", [])
        except Exception as e:
            logger.warning(f"提案抽出に失敗: {str(e)}", exc_info=True)
            return []
    
    def _extract_improvements(self, llm_response: str) -> List[Dict[str, Any]]:
        """LLMの応答から改善提案を抽出"""
        try:
            response_data = self.llm_manager.parse_json_response(llm_response)
            return response_data.get("improvements", [])
        except Exception as e:
            logger.warning(f"改善提案抽出に失敗: {str(e)}", exc_info=True)
            return [] 