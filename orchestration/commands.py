# orchestration/commands.py
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    # Import Session from the correct location
    # Import necessary types/models from types.py
    from ..ai_types import SubTask, SubtaskStatus, TaskExecutionResult, TaskModel, TaskStatus

    # Import Base classes for components (assuming they exist in components.base or specific files)
    # It might be better to import the specific protocols/interfaces if available
    from ..components.base import BasePlannerAI, BaseWorkerAI  # Adjust path if needed
    from ..core.session import Session


class Command(ABC):
    """コマンドの抽象基底クラス"""

    def __init__(self, session: "Session") -> None:
        """
        コマンドを初期化
        Args:
            session: 実行コンテキストとなるセッションオブジェクト
        """
        self.session = session

    @abstractmethod
    def execute(self) -> dict[str, Any]:
        """コマンドの実行ロジックを定義"""
        pass


class PlanTaskCommand(Command):
    """タスク計画を実行するコマンド"""

    def __init__(
        self, session: "Session", task_id: str, requirements: list[str] | None = None
    ) -> None:
        """
        タスク計画コマンドを初期化
        Args:
            session: セッションオブジェクト
            task_id: 計画対象のメインタスクID (SubTask IDではない想定)
            requirements: 計画のための追加要件 (オプション)
        """
        super().__init__(session)
        self.task_id = task_id  # This ID likely refers to the main task concept
        self.requirements = requirements or []

    def execute(self) -> dict[str, Any]:
        """Plannerコンポーネントを使用してタスク計画を実行"""
        print(f"[PlanTaskCommand] Executing for task ID: {self.task_id}")
        # Get the planner component using the session's getter
        planner: BasePlannerAI | None = self.session.get_component("planner")
        if not planner:
            print(f"Error: Planner component not found in session {self.session.id}")
            return {"error": "Plannerコンポーネントが見つかりません", "status": "failure"}

        # Get the main task details (Need a way to represent/get the main task)
        # Option 1: Assume task_id refers to a SubTask that *is* the main task
        # task: Optional['SubTask'] = self.session.get_subtask(self.task_id)
        # Option 2: Assume Session has a concept of a main task or task details
        # task_details = self.session.get_task_details(self.task_id) # Hypothetical
        # For now, create a dummy TaskModel representing the main task
        # In reality, this TaskModel should probably exist in the session or be passed
        main_task_model = TaskModel(
            id=self.task_id, title=f"Main Task {self.task_id}", description="Main task description"
        )

        # Execute the planning logic using the planner component's method
        # Ensure the planner component has a 'plan_task' method accepting TaskModel
        try:
            # Call the planner's plan_task method
            plan_result = planner.plan_task(task=main_task_model, requirements=self.requirements)
            print(f"[PlanTaskCommand] Planner returned plan: {plan_result}")

            # Process the plan result - e.g., add created subtasks to the session
            if isinstance(plan_result, dict) and "subtasks" in plan_result:
                created_subtasks = []
                for subtask_data in plan_result.get("subtasks", []):
                    try:
                        # Validate and create SubTask objects
                        subtask_obj = SubTask.model_validate(subtask_data)
                        created_subtasks.append(subtask_obj)
                        # Add the validated subtask to the session
                        self.session.add_subtask(subtask_obj)
                    except Exception as val_err:
                        print(
                            f"Warning: Failed to validate/add subtask {subtask_data.get('id')}: {val_err}"
                        )
                print(
                    f"[PlanTaskCommand] Added {len(created_subtasks)} subtasks to session {self.session.id}"
                )
                # Update main task status? Session status?
                # self.session.update_task_status(self.task_id, TaskStatus.PLANNING) # Need correct status enum

            # Return success with the planning result
            return {"result": plan_result, "status": "success"}

        except AttributeError as ae:
            # Catch if planner doesn't have plan_task method
            print(f"Error: Planner component does not have 'plan_task' method: {ae}")
            return {
                "error": "Planner に plan_task メソッドが実装されていません",
                "status": "failure",
            }
        except Exception as e:
            # Catch other errors during planning
            error_msg = f"タスク計画中にエラー発生 (Task ID: {self.task_id}): {e}"
            print(f"[PlanTaskCommand] {error_msg}")
            # Update status to failed?
            # self.session.update_task_status(self.task_id, TaskStatus.FAILED)
            return {"error": error_msg, "status": "failure"}


class ExecuteTaskCommand(Command):
    """タスク実行を実行するコマンド"""

    def __init__(
        self, session: "Session", task_id: str, context: dict[str, Any] | None = None
    ) -> None:
        """
        タスク実行コマンドを初期化
        Args:
            session: セッションオブジェクト
            task_id: 実行対象の **サブタスク** ID
            context: 実行に必要なコンテキスト情報 (オプション)
        """
        super().__init__(session)
        self.task_id: str = task_id  # This is the SubtaskID
        self.context: dict[str, Any] = context or {}

    def execute(self) -> dict[str, Any]:
        """Workerコンポーネントを使用してタスクを実行"""
        print(f"[ExecuteTaskCommand] Executing for subtask ID: {self.task_id}")
        # Get the worker component
        worker: BaseWorkerAI | None = self.session.get_component("worker")
        if not worker:
            print(f"Error: Worker component not found in session {self.session.id}")
            return {"error": "Workerコンポーネントが見つかりません", "status": "failure"}

        # Get the specific SubTask object from the session
        task_to_execute: SubTask | None = self.session.get_subtask(self.task_id)
        if not task_to_execute:
            print(f"Error: Subtask with ID {self.task_id} not found in session {self.session.id}")
            return {
                "error": f"指定されたサブタスクIDが見つかりません: {self.task_id}",
                "status": "failure",
            }

        # Execute the task using the worker component
        # Ensure worker has 'execute_task' method accepting SubTask and context
        try:
            # Update subtask status before execution
            self.session.update_task_status(self.task_id, SubtaskStatus.IN_PROGRESS)

            # Call the worker's execute_task method
            # It should return a TaskExecutionResult object
            execution_result: TaskExecutionResult = worker.execute_task(
                task=task_to_execute, context=self.context
            )
            print(f"[ExecuteTaskCommand] Worker returned execution result: {execution_result}")

            # Update subtask status based on the result
            # Assuming TaskExecutionResult has a status field (TaskStatus or SubtaskStatus)
            final_status = execution_result.status
            self.session.update_task_status(self.task_id, final_status)

            # Return success with the execution result (as a dict)
            return {
                "result": execution_result.model_dump(mode="json"),  # Serialize result model
                "status": "success" if final_status == SubtaskStatus.COMPLETED else "failure",
            }

        except AttributeError as ae:
            print(f"Error: Worker component does not have 'execute_task' method: {ae}")
            self.session.update_task_status(self.task_id, SubtaskStatus.FAILED)  # Mark as failed
            return {
                "error": "Worker に execute_task メソッドが実装されていません",
                "status": "failure",
            }
        except Exception as e:
            # Catch other errors during execution
            error_msg = f"サブタスク実行中にエラー発生 (SubTask ID: {self.task_id}): {e}"
            print(f"[ExecuteTaskCommand] {error_msg}")
            # Update status to failed
            self.session.update_task_status(self.task_id, SubtaskStatus.FAILED)
            return {"error": error_msg, "status": "failure"}


# コマンドディスパッチャー
class CommandDispatcher:
    """コマンドの生成と実行を管理するクラス"""

    def __init__(self, session: "Session") -> None:
        """
        コマンドディスパッチャーを初期化
        Args:
            session: コマンド実行のコンテキストとなるセッションオブジェクト
        """
        self.session = session
        # Map command type strings to command classes
        self.command_map = {
            "plan_task": PlanTaskCommand,
            "execute_task": ExecuteTaskCommand,
            # Add other command mappings here as they are defined
            # e.g., "evaluate_task": EvaluateTaskCommand,
            # e.g., "integrate_results": IntegrateResultsCommand,
        }
        print(
            f"CommandDispatcher initialized for session {session.id} with commands: {list(self.command_map.keys())}"
        )

    def execute_command(self, command_type: str, **kwargs) -> dict[str, Any]:
        """
        指定されたタイプのコマンドを生成し、実行する

        Args:
            command_type: 実行するコマンドの種類 (例: "plan_task")
            **kwargs: コマンドのコンストラクタに渡す引数

        Returns:
            コマンドの実行結果 (通常は {"result": ..., "status": "success/failure"} 形式の辞書)

        Raises:
            ValueError: 不明なコマンドタイプが指定された場合
        """
        # Validate the command type
        if command_type not in self.command_map:
            error_msg = f"不明なコマンドタイプが指定されました: {command_type}"
            print(f"[CommandDispatcher] {error_msg}")
            # Raise ValueError or return an error dict based on desired handling
            # raise ValueError(error_msg)
            return {"error": error_msg, "status": "failure"}

        # Get the appropriate command class
        command_class = self.command_map[command_type]

        try:
            # Instantiate the command, passing the session and other arguments
            # Ensure kwargs match the command class __init__ signature
            command_instance = command_class(session=self.session, **kwargs)

            # Execute the command
            print(f"[CommandDispatcher] Executing command: {command_type} with args: {kwargs}")
            result = command_instance.execute()
            print(
                f"[CommandDispatcher] Command {command_type} finished with status: {result.get('status')}"
            )
            return result
        except TypeError as te:
            # Catch errors if kwargs don't match __init__
            error_msg = f"コマンド '{command_type}' の初期化引数が不正です: {te}"
            print(f"[CommandDispatcher] {error_msg}")
            return {"error": error_msg, "status": "failure"}
        except Exception as e:
            # Catch errors during command instantiation or execution
            error_msg = f"コマンド '{command_type}' の実行中に予期せぬエラーが発生しました: {e}"
            print(f"[CommandDispatcher] {error_msg}")
            # traceback.print_exc()
            # Return a standardized error dictionary
            return {"error": error_msg, "status": "failure"}
