from typing import Dict, Any, List, Optional, TYPE_CHECKING
from ..core.message import OrchestrationMessage, MessageType, Component
from ..core.session import Session
from ..llm.llm_manager import LLMManager
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

    def _process_command(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
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
                
                requirements = content.get("requirements", [])
                plan_result = self.plan_task(task_id, requirements)
                
                return [self._create_response(
                    message.sender,
                    {"plan": plan_result},
                    "task_planned"
                )]
            elif action == "validate_plan":
                plan = content.get("plan")
                if not plan:
                    return [self._create_error_response(
                        message.sender,
                        "plan が指定されていません"
                    )]
                
                validation_result = self.validate_plan(plan)
                
                return [self._create_response(
                    message.sender,
                    {"validation_result": validation_result},
                    "plan_validated"
                )]
            else:
                return [self._create_error_response(
                    message.sender,
                    f"未対応のアクション: {action}"
                )]
        except Exception as e:
            error_msg = f"コマンド処理中にエラーが発生しました: {str(e)}"
            print(f"[Planner] {error_msg}")
            return [self._create_error_response(
                message.sender,
                error_msg
            )]

    def plan_task(self, task_id: str, requirements: List[str] = None) -> Dict[str, Any]:
        """タスク計画作成"""
        task = self.session.get_subtask(task_id)
        requirements = requirements or (task.requirements if task else [])
        
        try:
            # タスクタイプの判定
            task_type = self._determine_task_type(task)
            
            # テンプレート変数の準備
            variables = {
                "task_id": task_id,
                "task_title": task.title if task else "メインタスク",
                "task_description": task.description if task else "",
                "requirements": requirements,
                "session_context": {
                    "title": getattr(self.session, 'title', ''),
                    "mode": getattr(self.session, 'mode', '')
                }
            }
            
            # LLMを使用して計画を生成
            template_id = f"planner/{task_type}_planning"
            result_content = self.llm_manager.generate_with_template(template_id, variables)
            
            # 結果の解析（JSONの抽出）
            parsed_result = self.llm_manager.parse_json_response(result_content)
            
            # 計画結果の作成
            planning_result = {
                "task_id": task_id,
                "subtasks": parsed_result.get("subtasks", []),
                "dependencies": {},
                "strategy": parsed_result.get("strategy", "順次実行"),
                "metadata": parsed_result.get("metadata", {})
            }
            
            return planning_result
            
        except Exception as e:
            error_msg = f"タスク計画中にエラーが発生しました: {str(e)}"
            print(f"[Planner] {error_msg}")
            return {
                "task_id": task_id,
                "subtasks": [],
                "dependencies": {},
                "error": error_msg
            }

    def validate_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """計画の検証"""
        try:
            # テンプレート変数の準備
            variables = {
                "plan": plan,
                "session_id": self.session.id
            }
            
            # LLMを使用して計画を検証
            template_id = "planner/plan_validation"
            result_content = self.llm_manager.generate_with_template(template_id, variables)
            
            # 結果の解析
            parsed_result = self.llm_manager.parse_json_response(result_content)
            
            return parsed_result
            
        except Exception as e:
            error_msg = f"計画検証中にエラーが発生しました: {str(e)}"
            print(f"[Planner] {error_msg}")
            return {
                "is_valid": False,
                "issues": [error_msg],
                "suggestions": ["計画を再生成してください"]
            }

    def _determine_task_type(self, task: Optional[TaskModel]) -> str:
        """タスクタイプを判定"""
        if not task:
            return "generic"
            
        title = task.title.lower() if task.title else ""
        description = task.description.lower() if task.description else ""
        
        if any(keyword in title or keyword in description for keyword in 
              ["創作", "小説", "物語", "creative", "story"]):
            return "creative"
        
        if any(keyword in title or keyword in description for keyword in 
              ["コード", "プログラム", "実装", "code", "programming"]):
            return "coding"
        
        if any(keyword in title or keyword in description for keyword in 
              ["分析", "調査", "研究", "analysis", "research"]):
            return "analysis"
        
        return "generic"

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