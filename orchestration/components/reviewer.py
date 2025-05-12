import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING, Tuple, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum, auto
from dataclasses import dataclass
import json
import traceback
import asyncio
import re
from pathlib import Path
import os

from ..types import (
    TaskStatus, SubtaskStatus, ReviewResult, SubTask, 
    IReviewerAI, BaseAIComponent, Component,
    MessageType, OrchestrationMessage, TaskExecutionResult,
    Improvement, EvaluationResult,
    Task,
    TaskResult,
    EvaluationStatus,
)
from ..core.session import Session
from ..llm.llm_manager import LLMManager, BaseLLMManager

logger = logging.getLogger(__name__)

class ReviewerError(Exception):
    """Reviewer AIの例外クラス"""
    pass

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

class EvaluationContext(BaseModel):
    """評価コンテキストのモデル"""
    task_id: str
    task_title: str
    task_description: str
    requirements: List[str] = Field(default_factory=list)
    result_content: str = ""
    metrics: EvaluationMetrics

class ReviewerAI(BaseAIComponent):
    """拡張されたReviewer AI実装"""
    component_type = Component.REVIEWER
    
    def __init__(self, session: Session, llm_manager: LLMManager, output_dir: str = "./output"):
        """
        初期化
        Args:
            session: 関連付けられたセッション
            llm_manager: LLMマネージャー
            output_dir (str): 評価履歴の出力ディレクトリ
        """
        super().__init__(session)
        self.llm_manager = llm_manager
        self._task_type_keywords = {
            TaskType.CREATIVE: ["創作", "小説", "物語", "キャラクター", "ストーリー", "シナリオ", "creative", "story", "character"],
            TaskType.CODING: ["コード", "プログラム", "実装", "code", "programming", "implementation"],
            TaskType.ANALYSIS: ["分析", "調査", "研究", "analysis", "research"]
        }
        self.evaluator = self._create_evaluator()
        self.reviewer = self._create_reviewer()
        self.evaluation_history: List[EvaluationResult] = []
        self.output_dir = output_dir
    
    def _create_llm_client(self, template_path: str) -> BaseLLMManager:
        """LLMクライアントを作成"""
        return self.llm_manager

    async def _generate_with_template(self, template_path: str, variables: Dict[str, Any]) -> str:
        """テンプレートを使用してテキストを生成"""
        return await self.llm_manager.generate_with_template(template_path, variables)
    
    async def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
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
            
            return await handler(message)
            
        except Exception as e:
            logger.error(f"メッセージ処理中にエラーが発生: {str(e)}", exc_info=True)
            return [self._create_error_message(
                message.sender,
                f"メッセージ処理中にエラーが発生しました: {str(e)}"
            )]
    
    async def _handle_review_task(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
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
            review = await self.review_task(task, result)
            
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
    
    async def _handle_suggest_improvements(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
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
            improvements = await self.suggest_improvements(review)
            
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
    
    async def _handle_evaluate_task(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
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
            evaluation = await self.evaluate_task(task_id, output)
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
    
    async def review_task(self, task: SubTask, result: Optional[TaskExecutionResult] = None) -> ReviewResult:
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
            task.status = SubtaskStatus.REVIEWING
            
            # タスクタイプを判定
            task_type = self._determine_task_type(task)
            template_id = f"reviewer/{task_type.name.lower()}_review"
            
            # 評価コンテキストを作成
            context = self._create_evaluation_context(task, result)
            
            # LLMを使用してタスクを評価
            llm_response = await self._generate_with_template(template_id, context.__dict__)
            
            # 評価結果を生成
            metrics = await self._calculate_metrics(task, result, llm_response)
            suggestions = await self._extract_suggestions(llm_response)
            
            review = ReviewResult(
                task_id=task.id,
                status="completed",
                score=self._calculate_overall_score(metrics),
                feedback=llm_response,
                suggestions=suggestions,
                metrics=metrics.model_dump()
            )
            
            # タスクの状態を更新
            task.status = SubtaskStatus.COMPLETED
            logger.info(f"タスクレビュー完了: {task.id} スコア: {review.score}")
            
            return review
            
        except Exception as e:
            error_msg = f"タスクレビュー中にエラーが発生しました: {str(e)}"
            logger.error(error_msg, exc_info=True)
            task.status = TaskStatus.FAILED
            raise
    
    async def evaluate_task(self, task: Union[str, SubTask], output: Optional[str] = None) -> EvaluationResult:
        """
        タスクとその結果を評価する
        
        Args:
            task: 評価するタスクのIDまたはSubTaskオブジェクト
            output: タスクの出力（オプション）
            
        Returns:
            EvaluationResult: 評価結果
        """
        logger.info(f"タスク評価開始: {task if isinstance(task, str) else task.id}")
        
        try:
            if isinstance(task, str):
                task_obj = self.session.get_subtask(task)
                if not task_obj:
                    raise ValueError(f"タスクが見つかりません: {task}")
            else:
                task_obj = task
            
            # タスクタイプを判定
            task_type = self._determine_task_type(task_obj)
            template_id = f"reviewer/{task_type.name.lower()}_evaluation"
            
            # 評価コンテキストを作成
            context = self._create_evaluation_context(task_obj, None)
            if output:
                context.result_content = output
            
            # LLMを使用して評価を実行
            llm_response = await self._generate_with_template(template_id, context.model_dump())
            
            # 評価結果を生成
            metrics = await self._calculate_metrics(task_obj, None, llm_response)
            total_score = self._calculate_overall_score(metrics)
            feedback = await self._extract_feedback(llm_response)
            
            # EvaluationResultオブジェクトを作成
            evaluation_result = EvaluationResult(
                task_id=task_obj.id,
                status=TaskStatus.COMPLETED,
                score=total_score,
                feedback=feedback,
                metrics=metrics.model_dump(),
                created_at=datetime.now()  # created_atを明示的に設定
            )
            
            # 評価履歴に追加
            self.evaluation_history.append(evaluation_result)
            
            return evaluation_result
            
        except Exception as e:
            error_msg = f"タスク評価中にエラーが発生しました: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise
    
    async def suggest_improvements(self, review: ReviewResult) -> List[Dict[str, Any]]:
        """
        レビュー結果に基づいて改善提案を生成する

        Args:
            review (ReviewResult): レビュー結果

        Returns:
            List[Dict[str, Any]]: 改善提案のリスト。各提案は以下の形式:
            {
                "title": str,       # 改善提案のタイトル
                "description": str, # 詳細な説明
                "priority": str     # 優先度（"high", "medium", "low"）
            }
        """
        try:
            logger.info(f"改善提案の生成開始: {review.task_id}")
            
            # レビュー結果からコンテキストを作成
            context = {
                "task_id": review.task_id,
                "metrics": review.metrics,
                "feedback": review.feedback,
                "score": review.score
            }
            
            # LLMを使用して改善提案を生成
            template_id = "reviewer/improvement_suggestions"
            response = await self._generate_with_template(template_id, context)
            
            # レスポンスから改善提案を抽出
            improvements = []
            try:
                suggestions = json.loads(response)
                if isinstance(suggestions, list):
                    for suggestion in suggestions:
                        if all(key in suggestion for key in ["title", "description", "priority"]):
                            improvements.append({
                                "title": suggestion["title"],
                                "description": suggestion["description"],
                                "priority": suggestion["priority"].lower()
                            })
            except json.JSONDecodeError:
                logger.error("改善提案のJSONパースに失敗しました")
                
            # デフォルトの改善提案を追加（改善提案が空の場合）
            if not improvements:
                improvements.append({
                    "title": "全体的な品質向上",
                    "description": "タスクの完了度と品質を向上させるため、より詳細なレビューと修正が推奨されます。",
                    "priority": "medium"
                })
            
            logger.info(f"改善提案の生成完了: {len(improvements)}件の提案を生成")
            return improvements
            
        except Exception as e:
            error_msg = f"改善提案の生成中にエラーが発生しました: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return [{"title": "エラー", "description": error_msg, "priority": "high"}]
    
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
    
    async def _calculate_metrics(
        self,
        task: SubTask,
        result: Optional[TaskExecutionResult],
        llm_response: str
    ) -> EvaluationMetrics:
        """評価メトリクスを計算"""
        try:
            response_data = await self.llm_manager.parse_json_response(llm_response)
            metrics_data = response_data.get("metrics", {})
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
    
    async def _extract_suggestions(self, llm_response: str) -> List[str]:
        """LLMの応答から改善提案を抽出"""
        try:
            response_data = await self.llm_manager.parse_json_response(llm_response)
            return response_data.get("suggestions", [])
        except Exception as e:
            logger.warning(f"提案抽出に失敗: {str(e)}", exc_info=True)
            return []
    
    async def _extract_feedback(self, llm_response: str) -> str:
        """LLMの応答からフィードバックを抽出する"""
        try:
            response_data = await self.llm_manager.parse_json_response(llm_response)
            feedback = response_data.get("feedback", "")
            if not feedback:
                feedback = "評価は完了しましたが、詳細なフィードバックは生成されませんでした。"
            return feedback
        except Exception as e:
            logger.warning(f"フィードバック抽出に失敗: {str(e)}", exc_info=True)
            return "評価処理中にエラーが発生しました。"
    
    def _create_evaluator(self) -> BaseLLMManager:
        """評価用のLLMクライアントを作成"""
        return self._create_llm_client("reviewer/evaluate")
    
    def _create_reviewer(self) -> BaseLLMManager:
        """改善提案用のLLMクライアントを作成"""
        return self._create_llm_client("reviewer/improve")
    
    def _create_evaluation_prompt(self, task: SubTask, result: Optional[TaskExecutionResult]) -> str:
        """評価プロンプトを生成"""
        return f"""
        Task ID: {task.id}
        Description: {task.description}
        Result: {result.output if result else 'No result'}
        
        Please evaluate this task and provide:
        1. Metrics (0-100):
           - Quality
           - Completeness
           - Efficiency
        2. Suggestions for improvement
        
        Format:
        Metrics: {{
            quality: X,
            completeness: Y,
            efficiency: Z
        }}
        
        Suggestions: [
            "suggestion1",
            "suggestion2",
            ...
        ]
        """
    
    def _create_improvement_prompt(self, evaluation: ReviewResult) -> str:
        """改善プロンプトを生成"""
        return f"""
        Evaluation Result:
        Task ID: {evaluation.task_id}
        Metrics: {evaluation.metrics}
        Suggestions: {evaluation.suggestions}
        
        Based on this evaluation, please provide detailed improvement proposals.
        
        Format:
        Improvements: [
            {{
                Title: "improvement title 1",
                Description: "detailed description 1"
            }},
            {{
                Title: "improvement title 2",
                Description: "detailed description 2"
            }},
            ...
        ]
        """
    
    def _evaluate_completeness(self, task: SubTask, result: Optional[TaskExecutionResult]) -> float:
        """タスクの完了度を評価する"""
        if result is None:
            return 0.0
        return result.get("metrics", {}).get("completeness", 0.0)
    
    def _evaluate_quality(self, task: SubTask, result: Optional[TaskExecutionResult]) -> float:
        """タスクの品質を評価する"""
        if result is None:
            return 0.0
        return result.get("metrics", {}).get("quality", 0.0)
    
    def _generate_feedback(self, task: SubTask, result: Optional[TaskExecutionResult], metrics: Dict[str, float], total_score: float) -> str:
        """評価結果に基づいてフィードバックを生成する"""
        completeness = metrics["completeness"]
        quality = metrics["quality"]
        
        feedback_parts = []
        
        # 完了度に関するフィードバック
        if completeness >= 0.8:
            feedback_parts.append("タスクは十分に完了しています。")
        elif completeness >= 0.5:
            feedback_parts.append("タスクは部分的に完了していますが、いくつかの要素が不足しています。")
        else:
            feedback_parts.append("タスクの完了度が低く、多くの要素が不足しています。")
            
        # 品質に関するフィードバック
        if quality >= 0.8:
            feedback_parts.append("結果の品質は高く、期待を満たしています。")
        elif quality >= 0.5:
            feedback_parts.append("結果の品質は許容範囲ですが、改善の余地があります。")
        else:
            feedback_parts.append("結果の品質が低く、大幅な改善が必要です。")
            
        # 総合評価
        if total_score >= 0.8:
            feedback_parts.append("全体として、タスクは成功していると評価できます。")
        elif total_score >= 0.5:
            feedback_parts.append("全体として、タスクは部分的に成功していますが、改善が必要です。")
        else:
            feedback_parts.append("全体として、タスクは期待を下回る結果となっています。")
            
        return " ".join(feedback_parts)
    
    def save_evaluation_history(self) -> None:
        """評価履歴をJSONファイルに保存する"""
        if not self.evaluation_history:
            return

        # Convert datetime objects to ISO format strings
        serializable_history = []
        for result in self.evaluation_history:
            result_dict = result.model_dump()
            if result_dict.get('created_at'):
                result_dict['created_at'] = result_dict['created_at'].isoformat()
            serializable_history.append(result_dict)

        # タイムスタンプを含むファイル名を生成
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"evaluation_history_{timestamp}.json"
        
        os.makedirs(self.output_dir, exist_ok=True)
        with open(os.path.join(self.output_dir, filename), 'w', encoding='utf-8') as f:
            json.dump(serializable_history, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    pass 