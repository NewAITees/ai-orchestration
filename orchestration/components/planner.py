from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Protocol, TYPE_CHECKING
from pydantic import BaseModel, Field
from ..core.message import OrchestrationMessage, MessageType, Component
from ..core.session import Session, SubTask
from .llm_manager import LLMManager
from .base import BasePlannerAI
from ..types import TaskModel

class TaskAnalysisResult(BaseModel):
    """タスク分析結果のモデル"""
    
    main_task: str = Field(..., description="分析対象のメインタスク")
    task_type: str = Field(..., description="タスクのタイプ")
    complexity: int = Field(ge=1, le=10, description="タスクの複雑さ (1-10)")
    estimated_steps: int = Field(..., description="推定されるステップ数")
    subtasks: List[Dict[str, Any]] = Field(..., description="サブタスクのリスト")
    requirements: List[str] = Field(default_factory=list, description="タスクの要件")
    constraints: List[str] = Field(default_factory=list, description="タスクの制約")

class IPlannerAI(Protocol):
    """Planner AIのインターフェース"""
    
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass
    
    @abstractmethod
    def analyze_task(self, task: str) -> TaskAnalysisResult:
        """タスクを分析し、構造化された結果を返す"""
        pass

class PlannerAI(BasePlannerAI):
    """
    Planner AI の具体的な実装例。
    タスク計画や要件分析を担当する。
    """

    def __init__(self, session: 'Session', llm_manager: 'BaseLLMManager', **kwargs) -> None:
        """PlannerAIを初期化"""
        # Call the base class __init__
        super().__init__(session, llm_manager, **kwargs)
        # Add Planner-specific initialization if needed
        # Example: self.planning_depth = kwargs.get("planning_depth", 3)
        print(f"PlannerAI ({self.session.id}) initialized with config: {kwargs}")

    def analyze_requirements(self, requirements: List[str]) -> List[SubTask]:
        """
        与えられた要件を分析し、サブタスクのリストを生成する（仮実装）。
        将来的には plan_task に統合されるか、LLM を使用する。
        """
        print(f"[Planner] Analyzing requirements: {requirements}")
        subtasks = []
        # Dummy implementation: create one subtask per requirement
        for i, req in enumerate(requirements):
            subtask_id = f"subtask_{self.session.id}_{i+1}"
            subtask = SubTask(
                id=subtask_id,
                title=f"Subtask for: {req[:30]}...",
                description=f"Address the requirement: {req}",
                # status, created_at etc. will use defaults from SubTask model
            )
            subtasks.append(subtask)
            print(f"[Planner] Created subtask: {subtask_id}")

        # Add created subtasks to the session
        # for st in subtasks:
        #     self.session.add_subtask(st) # Let the caller (e.g., Director or Command) handle adding to session

        return subtasks

    def plan_task(self, task: TaskModel, requirements: List[str] = None) -> Any:
        """
        与えられたメインタスクと要件に基づいて実行計画（サブタスクリストなど）を作成する。
        """
        print(f"[Planner] Planning task: {task.id} - '{task.title}'")
        if requirements:
             print(f"[Planner] with requirements: {requirements}")

        # 1. Analyze requirements (could call self.analyze_requirements or have integrated logic)
        # Example: Use LLM to break down the main task based on description and requirements
        prompt = f"Break down the following task into smaller, manageable subtasks:\n"
        prompt += f"Main Task ID: {task.id}\n"
        prompt += f"Title: {task.title}\n"
        prompt += f"Description: {task.description}\n"
        if requirements:
             prompt += f"Requirements: {', '.join(requirements)}\n"
        prompt += "Provide the subtasks as a list of JSON objects, each with 'id', 'title', 'description', and 'dependencies' (list of IDs)."

        try:
            # Use the LLM manager provided by the base class
            print(f"[Planner] Sending planning request to LLM for task {task.id}")
            llm_response = self.llm_manager.generate(prompt) # Assuming generate method exists
            print(f"[Planner] Received LLM response for planning task {task.id}")

            # 2. Parse LLM response to create SubTask objects
            # This part needs robust parsing and error handling
            # plan_result = self._parse_llm_plan(llm_response)
            # Dummy plan result for now
            plan_result = {
                 "subtasks": [
                     {"id": f"{task.id}-sub1", "title": "Subtask 1", "description": "First step", "dependencies": []},
                     {"id": f"{task.id}-sub2", "title": "Subtask 2", "description": "Second step", "dependencies": [f"{task.id}-sub1"]}
                 ],
                 "planning_summary": "Generated a two-step plan."
            }
            print(f"[Planner] Plan created for task {task.id}: {plan_result.get('planning_summary')}")

            # Maybe create SubTask objects from plan_result["subtasks"] here?
            # subtask_objects = [SubTask.model_validate(st_data) for st_data in plan_result["subtasks"]]
            # It might be better for the command/caller to handle subtask creation/addition to session

            return plan_result # Return the structured plan

        except Exception as e:
            print(f"Error during LLM call or plan parsing for task {task.id}: {e}")
            # Return an error structure or raise exception
            return {"error": f"Planning failed: {e}", "subtasks": []}

    def validate_solution(self, solution: Any) -> bool:
        """
        提供されたソリューションが要件を満たしているか検証する (仮実装)。
        """
        print(f"[Planner] Validating solution: {str(solution)[:100]}...")
        # Add actual validation logic here, potentially using LLM or rules
        is_valid = isinstance(solution, dict) and "result" in solution # Dummy check
        print(f"[Planner] Validation result: {is_valid}")
        return is_valid

    # Add helper methods like _parse_llm_plan if needed
    # def _parse_llm_plan(self, llm_response: str) -> Dict[str, Any]:
    #     # Logic to parse JSON or structured text from LLM
    #     pass

class DefaultPlannerAI(BasePlannerAI):
    """デフォルトのPlanner AI実装"""
    component_type = Component.PLANNER
    
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
            if action == "plan":
                task_data = content.get("task")
                if not task_data:
                    return [self._create_error_response(
                        message.sender,
                        "plan コマンドには 'task' データが必要です",
                        "invalid_command"
                    )]
                
                task = Task.model_validate(task_data)
                plan = self.create_plan(task)
                
                return [self._create_response(
                    message.sender,
                    {"plan": plan.model_dump()},
                    "plan_created"
                )]
            elif action == "revise":
                plan_data = content.get("plan")
                feedback_data = content.get("feedback")
                if not plan_data or not feedback_data:
                    return [self._create_error_response(
                        message.sender,
                        "revise コマンドには 'plan' と 'feedback' データが必要です",
                        "invalid_command"
                    )]
                
                plan = Plan.model_validate(plan_data)
                feedback = PlanFeedback.model_validate(feedback_data)
                revised_plan = self.revise_plan(plan, feedback)
                
                return [self._create_response(
                    message.sender,
                    {"plan": revised_plan.model_dump()},
                    "plan_revised"
                )]
            else:
                return [self._create_error_response(
                    message.sender,
                    f"サポートされていないアクション: {action}",
                    "unsupported_action"
                )]
        except Exception as e:
            error_msg = f"コマンド処理中にエラーが発生しました: {str(e)}"
            print(f"[Planner] {error_msg}")
            return [self._create_error_response(
                message.sender,
                error_msg,
                f"{action}_failed" if action else "command_failed"
            )]
    
    def create_plan(self, task: Task) -> Plan:
        """
        タスクの実行計画を作成
        Args:
            task: 計画を作成するタスク
        Returns:
            作成された計画
        """
        try:
            # タスクの状態を計画作成中に更新
            self.update_status(task.id, TaskStatus.PLANNING)
            
            # LLMを使用して計画を生成
            prompt = self._create_planning_prompt(task)
            llm_response = self.llm_manager.generate(prompt)
            
            # 計画を生成（実際の実装ではLLMの応答を適切にパース）
            plan = Plan(
                id=generate_id(prefix="plan"),
                task_id=task.id,
                steps=[
                    PlanStep(
                        id=generate_id(prefix="step"),
                        description="サンプルステップ",
                        estimated_duration=60,
                        dependencies=[],
                        resources=[]
                    )
                ],
                estimated_completion_time=datetime.now() + timedelta(hours=1),
                status=PlanStatus.CREATED,
                metadata={"complexity": "medium", "priority": "high"}
            )
            
            # タスクの状態を更新
            self.update_status(
                task.id,
                TaskStatus.PLANNED,
                {"plan": plan.model_dump()}
            )
            
            return plan
            
        except Exception as e:
            error_msg = f"計画作成中にエラーが発生しました: {str(e)}"
            print(f"[Planner] {error_msg}")
            self.update_status(task.id, TaskStatus.FAILED, {"error": error_msg})
            raise
    
    def revise_plan(self, plan: Plan, feedback: PlanFeedback) -> Plan:
        """
        フィードバックに基づいて計画を修正
        Args:
            plan: 修正する計画
            feedback: 計画に対するフィードバック
        Returns:
            修正された計画
        """
        try:
            # タスクの状態を計画修正中に更新
            self.update_status(plan.task_id, TaskStatus.REVISING)
            
            # LLMを使用して計画を修正
            prompt = self._create_revision_prompt(plan, feedback)
            llm_response = self.llm_manager.generate(prompt)
            
            # 修正された計画を生成（実際の実装ではLLMの応答を適切にパース）
            revised_plan = Plan(
                id=generate_id(prefix="plan"),
                task_id=plan.task_id,
                steps=plan.steps,  # 実際には修正されたステップを設定
                estimated_completion_time=plan.estimated_completion_time,
                status=PlanStatus.REVISED,
                metadata=plan.metadata
            )
            
            # タスクの状態を更新
            self.update_status(
                plan.task_id,
                TaskStatus.PLANNED,
                {"plan": revised_plan.model_dump()}
            )
            
            return revised_plan
            
        except Exception as e:
            error_msg = f"計画修正中にエラーが発生しました: {str(e)}"
            print(f"[Planner] {error_msg}")
            self.update_status(plan.task_id, TaskStatus.FAILED, {"error": error_msg})
            raise 