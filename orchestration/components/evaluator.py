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
    
    def __init__(self, session: Session, llm_manager: LLMManager, **kwargs) -> None:
        """
        初期化
        Args:
            session: 関連付けられたセッション
            llm_manager: LLMマネージャー
            **kwargs: 追加の設定パラメータ
        """
        super().__init__(session, llm_manager, **kwargs)
    
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
            if action == "evaluate":
                task_data = content.get("task")
                result_data = content.get("result")
                if not task_data:
                    raise ValueError("evaluate コマンドには 'task' データが必要です")
                
                task = SubTask.model_validate(task_data)
                result = TaskExecutionResult.model_validate(result_data) if result_data else None
                evaluation = self.evaluate_task(task, result)
                
                return [self._create_response(
                    message.sender,
                    {"evaluation": evaluation.model_dump()},
                    "evaluation_completed"
                )]
            elif action == "suggest":
                evaluation_data = content.get("evaluation")
                if not evaluation_data:
                    raise ValueError("suggest コマンドには 'evaluation' データが必要です")
                
                evaluation = EvaluationResult.model_validate(evaluation_data)
                improvements = self.suggest_improvements(evaluation)
                
                return [self._create_response(
                    message.sender,
                    {"improvements": [imp.model_dump() for imp in improvements]},
                    "suggestions_completed"
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
    
    def evaluate_task(self, task: SubTask, result: Optional[TaskExecutionResult] = None) -> EvaluationResult:
        """
        タスクの実行結果を評価
        Args:
            task: 評価対象のタスク
            result: タスクの実行結果（オプション）
        Returns:
            評価結果
        """
        try:
            # タスクの状態を評価中に更新
            self.update_status(task.id, TaskStatus.REVIEWING)
            
            # LLMを使用してタスクを評価
            prompt = self._create_evaluation_prompt(task, result)
            llm_response = self.llm_manager.generate(prompt)
            
            # 評価結果を生成
            evaluation = EvaluationResult(
                task_id=task.id,
                is_successful=True,  # LLMの応答から適切に判定する必要あり
                score=0.8,  # LLMの応答から適切に計算する必要あり
                feedback=llm_response,
                metrics={
                    "quality": 0.8,
                    "completeness": 0.9,
                    "efficiency": 0.7
                }
            )
            
            # タスクの状態を更新
            self.update_status(
                task.id,
                TaskStatus.REVIEW_COMPLETED,
                {"evaluation": evaluation.model_dump()}
            )
            
            return evaluation
            
        except Exception as e:
            error_msg = f"タスク評価中にエラーが発生しました: {str(e)}"
            print(f"[Evaluator] {error_msg}")
            self.update_status(task.id, TaskStatus.FAILED, {"error": error_msg})
            raise
    
    def suggest_improvements(self, evaluation: EvaluationResult) -> List[Improvement]:
        """
        評価結果に基づく改善案を提案
        Args:
            evaluation: 評価結果
        Returns:
            改善案のリスト
        """
        try:
            # LLMを使用して改善案を生成
            prompt = self._create_improvement_prompt(evaluation)
            llm_response = self.llm_manager.generate(prompt)
            
            # 改善案を生成（実際の実装ではLLMの応答を適切にパース）
            improvements = [
                Improvement(
                    id=generate_id(prefix="improvement"),
                    description="サンプルの改善案",
                    priority="high",
                    effort_estimate="medium",
                    expected_impact="high"
                )
            ]
            
            return improvements
            
        except Exception as e:
            error_msg = f"改善案生成中にエラーが発生しました: {str(e)}"
            print(f"[Evaluator] {error_msg}")
            raise
    
    def _create_evaluation_prompt(self, task: SubTask, result: Optional[TaskExecutionResult]) -> str:
        """
        タスク評価用のプロンプトを作成
        Args:
            task: 評価対象のタスク
            result: タスクの実行結果
        Returns:
            生成されたプロンプト
        """
        prompt = f"""
        以下のタスクとその実行結果を評価してください：
        
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
    
    def _create_improvement_prompt(self, evaluation: EvaluationResult) -> str:
        """
        改善案生成用のプロンプトを作成
        Args:
            evaluation: 評価結果
        Returns:
            生成されたプロンプト
        """
        prompt = f"""
        以下の評価結果に基づいて、具体的な改善案を提案してください：
        
        タスクID: {evaluation.task_id}
        成功: {'はい' if evaluation.is_successful else 'いいえ'}
        スコア: {evaluation.score}
        フィードバック: {evaluation.feedback}
        
        メトリクス:
        """
        
        for metric, value in evaluation.metrics.items():
            prompt += f"\n- {metric}: {value}"
        
        prompt += """
        
        以下の形式で改善案を提案してください：
        1. 改善内容の説明
        2. 優先度（high/medium/low）
        3. 実装の難易度
        4. 期待される効果
        5. 具体的な実装手順
        """
        
        return prompt

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
