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
    
    def __init__(self, session: Session, llm_manager: LLMManager) -> None:
        """
        初期化
        
        Args:
            session: 関連付けられたセッション
            llm_manager: LLMマネージャー
        """
        super().__init__(session, llm_manager)
        self.planner = DefaultPlannerAI(session, llm_manager)
        self.worker = DefaultWorkerAI(session, llm_manager)
        self.evaluator = DefaultEvaluatorAI(session, llm_manager)
        self.task_statuses: Dict[str, TaskStatusModel] = {}
    
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
            if action == "start_session":
                return self._handle_start_session()
            elif action == "execute_task":
                return self._handle_execute_task(content.get("task_id"))
            elif action == "evaluate_task":
                return self._handle_evaluate_task(content.get("task_id"))
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
    
    def _handle_start_session(self) -> List[OrchestrationMessage]:
        """
        セッションを開始し、タスク分析を実行
        
        Returns:
            応答メッセージのリスト
        """
        try:
            # Planner AIにタスク分析を依頼
            analysis_messages = self.planner.process_message(
                self._create_message(
                    Component.PLANNER,
                    MessageType.COMMAND,
                    {"action": "analyze_task"}
                )
            )
            return analysis_messages
        except Exception as e:
            return [self._create_error_message(
                Component.CLIENT,
                f"セッション開始中にエラーが発生しました: {str(e)}"
            )]
    
    def _handle_execute_task(self, task_id: str) -> List[OrchestrationMessage]:
        """
        タスクを実行
        
        Args:
            task_id: 実行するタスクのID
            
        Returns:
            応答メッセージのリスト
        """
        try:
            # タスクの状態を更新
            self.update_task_status(task_id, TaskStatus.EXECUTING)
            
            # Worker AIにタスク実行を依頼
            execution_messages = self.worker.process_message(
                self._create_message(
                    Component.WORKER,
                    MessageType.COMMAND,
                    {
                        "action": "execute_task",
                        "task_id": task_id
                    }
                )
            )
            return execution_messages
        except Exception as e:
            self.update_task_status(task_id, TaskStatus.FAILED, error=str(e))
            return [self._create_error_message(
                Component.CLIENT,
                f"タスク実行中にエラーが発生しました: {str(e)}"
            )]
    
    def _handle_evaluate_task(self, task_id: str) -> List[OrchestrationMessage]:
        """
        タスクの評価を実行
        
        Args:
            task_id: 評価するタスクのID
            
        Returns:
            応答メッセージのリスト
        """
        try:
            # タスクの状態を更新
            self.update_task_status(task_id, TaskStatus.REVIEWING)
            
            # Evaluator AIにタスク評価を依頼
            evaluation_messages = self.evaluator.process_message(
                self._create_message(
                    Component.EVALUATOR,
                    MessageType.COMMAND,
                    {
                        "action": "evaluate_task",
                        "task_id": task_id
                    }
                )
            )
            return evaluation_messages
        except Exception as e:
            self.update_task_status(task_id, TaskStatus.FAILED, error=str(e))
            return [self._create_error_message(
                Component.CLIENT,
                f"タスク評価中にエラーが発生しました: {str(e)}"
            )] 