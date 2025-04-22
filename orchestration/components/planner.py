from typing import Dict, Any, List, Optional, TYPE_CHECKING
from ..core.message import OrchestrationMessage, MessageType, Component
from ..core.session import Session
from .llm_manager import LLMManager
from ..types import (
    TaskModel, TaskAnalysisResult, IPlannerAI,
    BaseAIComponent, SubTask
)

class PlannerAI(BaseAIComponent):
    """
    Planner AI の具体的な実装例。
    タスク計画や要件分析を担当する。
    """
    component_type = Component.PLANNER

    def __init__(self, session: Session, llm_manager: LLMManager, **kwargs) -> None:
        """PlannerAIを初期化"""
        super().__init__(session)
        self.llm_manager = llm_manager
        print(f"PlannerAI ({self.session.id}) initialized with config: {kwargs}")

    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass  # 実装は省略

    def analyze_task(self, task: str) -> TaskAnalysisResult:
        """タスクを分析し、構造化された結果を返す"""
        pass  # 実装は省略

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

    def plan_task(self, task_id: str, requirements: List[str] = None) -> Dict[str, Any]:
        """タスク計画作成"""
        task = self.session.get_subtask(task_id)
        requirements = requirements or (task.requirements if task else [])
        
        # LLMを使用したタスク分解
        if self.llm_manager:
            prompt = f"""
            タスクを分解してください:
            タスクID: {task_id}
            タスク: {task.title if task else 'メインタスク'}
            説明: {task.description if task else ''}
            要件: {', '.join(requirements)}
            
            サブタスクのリストを作成してください。
            """
            # 実際のLLM呼び出しはここで行う
        
        # サンプルの計画（実際はLLMの出力を解析して生成）
        subtasks = [
            {"id": f"{task_id}-sub1", "title": "サブタスク1", "description": "最初のステップ"},
            {"id": f"{task_id}-sub2", "title": "サブタスク2", "description": "次のステップ"}
        ]
        
        return {
            "subtasks": subtasks,
            "dependencies": {
                f"{task_id}-sub2": [f"{task_id}-sub1"]
            }
        }

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

class DefaultPlannerAI(BaseAIComponent):
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
        super().__init__(session)
        self.llm_manager = llm_manager
    
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
            if action == "plan_task":
                task_id = content.get("task_id")
                if not task_id:
                    return [self._create_error_response(
                        message.sender,
                        "task_id が指定されていません"
                    )]
                
                # タスク計画作成
                requirements = content.get("requirements", [])
                plan = self.plan_task(task_id, requirements)
                
                return [self._create_response(
                    message.sender,
                    {"plan": plan},
                    "task_planned"
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