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
            if action == "analyze_task":
                return self._handle_analyze_task(content.get("task", ""))
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
    
    def _handle_analyze_task(self, task: str) -> List[OrchestrationMessage]:
        """
        タスクを分析し、サブタスクに分解
        
        Args:
            task: 分析対象のタスク
            
        Returns:
            応答メッセージのリスト
        """
        try:
            # タスクの前処理と検証
            if not task or len(task.strip()) == 0:
                return [self._create_error_message(
                    Component.DIRECTOR,
                    "タスクが空です"
                )]
            
            # タスク分析の実行
            analysis_result = self.analyze_task(task)
            
            # 分析結果をJSONに変換
            result_json = analysis_result.dict()
            
            # レスポンスメッセージを作成
            return [self._create_message(
                Component.DIRECTOR,
                MessageType.RESPONSE,
                {
                    "action": "task_analyzed",
                    "result": result_json
                }
            )]
        
        except Exception as e:
            return [self._create_error_message(
                Component.DIRECTOR,
                f"タスク分析中にエラーが発生しました: {str(e)}"
            )]
    
    def analyze_task(self, task: str) -> TaskAnalysisResult:
        """
        タスクを分析し、構造化された結果を返す
        
        Args:
            task: 分析対象のタスク
            
        Returns:
            分析結果
        """
        try:
            # LLMを使用してタスクを分析
            prompt = f"""
            以下のタスクを分析し、必要な情報を抽出してください：
            
            タスク: {task}
            
            1. タスクの種類を判定
            2. 複雑さを1-10で評価
            3. 必要なステップ数を推定
            4. サブタスクを特定
            5. 要件と制約を抽出
            """
            
            response = self.llm_manager.get_completion(prompt)
            
            # 現在はダミーの実装を提供
            # 実際の実装では、LLMの応答を解析して適切な値を設定
            return TaskAnalysisResult(
                main_task=task,
                task_type="creative_writing",
                complexity=5,
                estimated_steps=3,
                subtasks=[
                    {
                        "title": "キャラクター設定",
                        "description": "物語の主要キャラクターの設定を作成",
                        "dependencies": []
                    },
                    {
                        "title": "プロット作成",
                        "description": "物語の基本的なプロットを構築",
                        "dependencies": ["キャラクター設定"]
                    },
                    {
                        "title": "本文執筆",
                        "description": "実際の物語を執筆",
                        "dependencies": ["プロット作成"]
                    }
                ],
                requirements=["魅力的なキャラクター", "一貫したストーリー"],
                constraints=["適切な長さ", "ターゲット読者層に適した内容"]
            )
        except Exception as e:
            raise Exception(f"タスク分析中にエラーが発生しました: {str(e)}") 