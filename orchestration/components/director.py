from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field
from ..core.message import OrchestrationMessage, MessageType, Component
from ..core.session import Session, SubTask
from ..types import TaskStatus, TaskStatusModel, OrchestrationMessage, MessageType, Component, TaskID, SubTask, FinalResult, SessionStatus
from .planner import DefaultPlannerAI
from .worker import DefaultWorkerAI
from .evaluator import DefaultEvaluatorAI
from .llm_manager import LLMManager
from .base import BaseDirectorAI

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

class DirectorAI(BaseDirectorAI):
    """
    Director AI の具体的な実装例。
    プロセス全体の制御と結果の統合を担当する。
    """

    def __init__(self, session: 'Session', llm_manager: 'BaseLLMManager', **kwargs) -> None:
        """DirectorAIを初期化"""
        # Call the base class __init__ passing session, llm_manager, and any extra args
        super().__init__(session, llm_manager, **kwargs)
        # Add Director-specific initialization if needed, using kwargs
        # Example: self.integration_strategy = kwargs.get("integration_strategy", "simple_concat")
        print(f"DirectorAI ({self.session.id}) initialized with config: {kwargs}")

    def control_process(self, task_id: TaskID) -> None:
        """
        指定されたタスクIDに基づいてプロセス制御を実行する。
        現在は Planner に 'plan_task' コマンドを発行する。
        """
        print(f"[Director] Controlling process for main task: {task_id}") # Assuming task_id is for the main task

        # Option 1: Get main task requirements from session or task data if needed
        # main_task = self.session.get_task(task_id) # Method might be needed in Session
        # requirements = main_task.requirements if main_task else ["Default requirement"]
        requirements = ["Requirement A", "Requirement B"] # Placeholder requirements

        # Use the CommandDispatcher held by the session to execute the planning command
        try:
            print(f"[Director] Dispatching 'plan_task' command for task: {task_id}")
            # Ensure 'plan_task' command exists and accepts 'task_id' and 'requirements'
            # The task_id here likely refers to the overall task to be planned.
            plan_command_result = self.session.dispatcher.execute_command(
                command_type="plan_task",
                task_id=task_id, # Pass the main task ID to the command
                requirements=requirements
            )
            print(f"[Director] 'plan_task' command result: {plan_command_result}")

            # Handle the result of the command execution
            if plan_command_result.get("status") == "failure":
                 error_msg = plan_command_result.get('error', 'Unknown planning error')
                 print(f"Error: Task planning failed for {task_id}: {error_msg}")
                 # Update session status or take other error handling actions
                 self.session.update_session_status(SessionStatus.FAILED) # Example action
            else:
                 # Planning successful, proceed to next step (e.g., execution)
                 # The plan might be in plan_command_result['result']
                 plan = plan_command_result.get("result", {}).get("plan")
                 print(f"[Director] Planning successful for {task_id}. Plan: {plan}")
                 # Potentially dispatch 'execute_task' commands based on the plan here
                 # ... logic to trigger execution ...

        except ValueError as ve:
             # Handle cases where the command type is unknown or component is missing
             print(f"Error dispatching command: {ve}")
             self.session.update_session_status(SessionStatus.FAILED)
        except Exception as e:
             # Catch other potential exceptions during command dispatch or execution
             print(f"Error during 'plan_task' command dispatch/execution for task {task_id}: {e}")
             # traceback.print_exc() # For detailed debugging
             self.session.update_session_status(SessionStatus.FAILED)

    def integrate_results(self, results: List[Any]) -> Any: # Should return FinalResult type if defined
        """
        複数のWorkerまたは他のコンポーネントからの結果を統合する。

        Args:
            results: 統合対象の結果のリスト。TaskExecutionResult の辞書形式などを期待。

        Returns:
            統合された最終結果 (仮: FinalResult 型)。
        """
        print(f"[Director] Integrating {len(results)} results...")
        # Implement logic to analyze and combine results into a final product
        # Example: Combine text outputs, analyze numerical data, etc.
        final_output_summary = "Integrated result summary:\n"
        successful_tasks = 0
        failed_tasks = 0

        for i, result_item in enumerate(results):
            # Assuming result_item might be the raw output of execute_command,
            # which contains {'result': TaskExecutionResult.dict(), 'status': 'success/failure'}
            # Or it could be just the TaskExecutionResult dict itself. Need consistency.
            task_exec_result_dict = None
            item_status = "unknown"

            if isinstance(result_item, dict):
                if "result" in result_item and isinstance(result_item["result"], dict):
                    # Case 1: Result from execute_command wrapper
                    task_exec_result_dict = result_item["result"]
                    item_status = result_item.get("status", "unknown")
                elif "task_id" in result_item and "status" in result_item:
                     # Case 2: Raw TaskExecutionResult dict
                     task_exec_result_dict = result_item
                     item_status = task_exec_result_dict.get("status", "unknown")

            if task_exec_result_dict:
                 task_id = task_exec_result_dict.get("task_id", "N/A")
                 task_status = task_exec_result_dict.get("status", "N/A") # This is TaskStatus/SubtaskStatus
                 output_data = task_exec_result_dict.get("result", {}).get("output", "N/A") # Get nested output
                 final_output_summary += f"  - Task {task_id} (Status: {task_status}): {output_data}\n"
                 if task_status == TaskStatus.COMPLETED or task_status == SubtaskStatus.COMPLETED:
                      successful_tasks += 1
                 elif task_status == TaskStatus.FAILED or task_status == SubtaskStatus.FAILED:
                      failed_tasks += 1
            else:
                 # Handle unexpected result format
                 final_output_summary += f"  - Result {i+1} (Unknown format): {str(result_item)}\n"
                 failed_tasks += 1


        print(f"[Director] Integration complete. Success: {successful_tasks}, Failed: {failed_tasks}.")

        # Structure the final result according to FinalResult type (hypothetical)
        final_result_obj: FinalResult = {
            "summary": final_output_summary,
            "status": "completed" if failed_tasks == 0 else "partially_completed",
            "successful_count": successful_tasks,
            "failed_count": failed_tasks,
            "total_results": len(results)
        }
        return final_result_obj

    # Add any Director-specific helper methods below
    # def _some_director_helper(self):
    #     pass

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