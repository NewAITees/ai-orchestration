from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field
from ..core.message import OrchestrationMessage, MessageType, Component
from ..core.session import Session, SubTask
from ..types import TaskStatus, TaskStatusModel, OrchestrationMessage, MessageType, Component, TaskID, SubTask, FinalResult, SessionStatus
from .planner import DefaultPlannerAI
from .worker import DefaultWorkerAI
from .reviewer import ReviewerAI
from .llm_manager import LLMManager
from .base import BaseDirectorAI, BaseAIComponent

class IDirectorAI(Protocol):
    """Director AIのインターフェース"""
    
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass
    
    @abstractmethod
    def get_task_status(self, task_id: str) -> Optional[TaskStatusModel]:
        """指定されたタスクの状態を取得する"""
        pass
    
    @abstractmethod
    def update_task_status(self, task_id: str, status: str, progress: Optional[float] = None, error: Optional[str] = None) -> None:
        """タスクの状態を更新する"""
        pass

class DirectorAI(BaseAIComponent):
    """DirectorAI"""
    component_type = Component.DIRECTOR
    
    def _process_command(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """コマンド処理"""
        content = message.content
        action = content.get("action")
        task_id = content.get("task_id")
        
        try:
            if action == "start_process" and task_id:
                # プロセス開始処理
                self.execute_process(task_id)
                return [self._create_response(
                    message.sender,
                    {"task_id": task_id},
                    "process_started"
                )]
            elif action == "integrate":
                # 結果統合処理
                results = content.get("results", [])
                integrated = self.integrate_results(results)
                return [self._create_response(
                    message.sender,
                    {"result": integrated},
                    "integration_completed"
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
    
    def execute_process(self, task_id: str) -> None:
        """プロセス制御"""
        # 計画から実行、評価までの流れを制御
        planner = self.session.get_component("planner")
        if not planner:
            raise ValueError("Plannerコンポーネントが見つかりません")
        
        # 計画フェーズ
        plan_result = planner.plan_task(task_id)
        
        # 実行フェーズ
        worker = self.session.get_component("worker")
        if not worker:
            raise ValueError("Workerコンポーネントが見つかりません")
        
        results = []
        for subtask in plan_result.get("subtasks", []):
            # サブタスクの追加と実行
            task_obj = SubTask(
                id=subtask["id"],
                title=subtask["title"],
                description=subtask["description"]
            )
            self.session.add_subtask(task_obj)
            result = worker.execute_task(task_obj)
            results.append(result)
        
        # 統合フェーズ
        integrated = self.integrate_results(results)
    
    def integrate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """結果統合"""
        # 結果統合ロジック
        summary = "\n".join([f"- {result.get('content', '')[:50]}..." for result in results])
        return {
            "status": "completed",
            "summary": summary,
            "complete": len(results) > 0
        }

class DefaultDirectorAI(BaseDirectorAI):
    """デフォルトのDirector AI実装"""
    
    def __init__(self, session: Session, llm_manager: LLMManager, **kwargs) -> None:
        """
        初期化
        Args:
            session: 関連付けられたセッション
            llm_manager: LLMマネージャー
            **kwargs: 追加の設定パラメータ
        """
        super().__init__(session, llm_manager, **kwargs)
        self.planner = DefaultPlannerAI(session, llm_manager)
        self.worker = DefaultWorkerAI(session, llm_manager)
        self.evaluator = DefaultEvaluatorAI(session, llm_manager)
    
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
        task_id = content.get("task_id")
        
        try:
            if action == "start_process" and task_id:
                self.execute_process(task_id)
                return [self._create_response(
                    message.sender,
                    {"status": "process_started", "task_id": task_id},
                    "process_started"
                )]
            elif action == "integrate":
                results = content.get("results", [])
                integrated = self.integrate_results(results)
                return [self._create_response(
                    message.sender,
                    {"integrated_result": integrated.model_dump()},
                    "integration_completed"
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
    
    def execute_process(self, task_id: TaskID) -> None:
        """
        プロセス全体の実行を制御
        Args:
            task_id: メインタスクのID
        """
        try:
            # タスクの状態を実行中に更新
            self.update_status(task_id, TaskStatus.EXECUTING)
            
            # Plannerにタスク計画を依頼
            task = self.session.get_task(task_id)
            if not task:
                raise ValueError(f"タスク {task_id} が見つかりません")
            
            plan_result = self.planner.plan_task(task)
            
            # 計画の検証
            if not self.planner.validate_plan(plan_result):
                raise ValueError("タスク計画の検証に失敗しました")
            
            # サブタスクの実行
            execution_results = []
            for subtask in plan_result.subtasks:
                self.session.add_subtask(subtask)
                result = self.worker.execute_task(subtask)
                execution_results.append(result)
                
                # 実行結果の評価
                evaluation = self.evaluator.evaluate_task(subtask, result)
                if not evaluation.is_successful:
                    improvements = self.evaluator.suggest_improvements(evaluation)
                    print(f"タスク {subtask.id} の改善提案: {improvements}")
            
            # 全体の結果を統合
            final_result = self.integrate_results(execution_results)
            
            # タスクの状態を完了に更新
            self.update_status(
                task_id,
                TaskStatus.COMPLETED,
                {"final_result": final_result.model_dump()}
            )
            
        except Exception as e:
            error_msg = f"プロセス実行中にエラーが発生しました: {str(e)}"
            print(f"[Director] {error_msg}")
            self.update_status(task_id, TaskStatus.FAILED, {"error": error_msg})
            raise
    
    def integrate_results(self, results: List[TaskExecutionResult]) -> FinalResult:
        """
        実行結果を統合して最終結果を生成
        Args:
            results: 統合する実行結果のリスト
        Returns:
            統合された最終結果
        """
        successful_count = 0
        failed_count = 0
        outputs = []
        
        for result in results:
            if result.status == TaskStatus.COMPLETED:
                successful_count += 1
                outputs.append(result.output)
            else:
                failed_count += 1
        
        return FinalResult(
            status="completed" if failed_count == 0 else "partially_completed",
            successful_count=successful_count,
            failed_count=failed_count,
            total_results=len(results),
            outputs=outputs
        ) 