from typing import List, Optional, Any, Dict, Protocol
from abc import ABC, abstractmethod
from datetime import datetime
from ..llm.llm_manager import BaseLLMManager
from ..schemas.task import Task, TaskAnalysis, TaskResult
from ..core.session import Session
from ..types import OrchestrationMessage, MessageType, Component
from ..types import TaskStatus, TaskExecutionResult

# 基本プロトコル
class AIComponentProtocol(Protocol):
    """AIコンポーネントの基本インターフェース"""
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]: ...

# 共通の基底クラス
class BaseAIComponent(ABC):
    """全AIコンポーネントの共通基底クラス"""
    
    def __init__(self, session: Session, llm_manager: BaseLLMManager) -> None:
        self.session = session
        self.llm_manager = llm_manager
        self.last_used = datetime.now()
        
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理する基本メソッド"""
        pass
        
    def _create_response(
        self,
        receiver: Component,
        content: Dict[str, Any],
        action: Optional[str] = None
    ) -> OrchestrationMessage:
        """応答メッセージを作成するヘルパーメソッド"""
        return OrchestrationMessage(
            type=MessageType.RESPONSE,
            sender=self._get_component_type(),
            receiver=receiver,
            content=content,
            session_id=self.session.id,
            action=action
        )
        
    def _create_error_response(
        self,
        receiver: Component,
        error: str
    ) -> OrchestrationMessage:
        """エラーメッセージを作成するヘルパーメソッド"""
        return OrchestrationMessage(
            type=MessageType.ERROR,
            sender=self._get_component_type(),
            receiver=receiver,
            content={"error": error},
            session_id=self.session.id
        )
    
    def update_last_used(self) -> None:
        """最終使用時刻を更新"""
        self.last_used = datetime.now()
    
    @abstractmethod
    def _get_component_type(self) -> Component:
        """コンポーネントタイプを返す抽象メソッド"""
        pass

# Director AI
class DirectorProtocol(AIComponentProtocol, Protocol):
    """Director AIのインターフェース"""
    def control_process(self, task_id: str) -> None: ...
    def integrate_results(self, results: List[Any]) -> Any: ...

class BaseDirectorAI(BaseAIComponent):
    """Director AIの基本実装"""
    
    def _get_component_type(self) -> Component:
        return Component.DIRECTOR
    
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージ処理の基本実装"""
        if message.type == MessageType.COMMAND:
            return self._process_command(message)
        elif message.type == MessageType.CONTROL:
            return self._process_control(message)
        return [self._create_error_response(
            message.receiver,
            "不明なメッセージタイプ"
        )]
    
    def _process_command(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """コマンドメッセージの処理"""
        try:
            action = message.content.get("action")
            if action == "start_process":
                self.control_process(message.content.get("task_id"))
                return [self._create_response(
                    message.sender,
                    {"status": "process_started"},
                    "process_started"
                )]
            elif action == "integrate":
                results = message.content.get("results", [])
                integrated = self.integrate_results(results)
                return [self._create_response(
                    message.sender,
                    {"integrated_result": integrated},
                    "integration_completed"
                )]
            return [self._create_error_response(
                message.sender,
                "不明なコマンド"
            )]
        except Exception as e:
            return [self._create_error_response(
                message.sender,
                str(e)
            )]
    
    def _process_control(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """制御メッセージの処理"""
        try:
            control_type = message.content.get("type")
            if control_type == "status_update":
                self.session.update_status(message.content.get("status"))
                return [self._create_response(
                    message.sender,
                    {"status": "updated"},
                    "status_updated"
                )]
            return [self._create_error_response(
                message.sender,
                "不明な制御タイプ"
            )]
        except Exception as e:
            return [self._create_error_response(
                message.sender,
                str(e)
            )]
    
    def control_process(self, task_id: str) -> None:
        """プロセス制御の基本実装"""
        pass
        
    def integrate_results(self, results: List[Any]) -> Any:
        """結果統合の基本実装"""
        pass

# Planner AI
class PlannerProtocol(AIComponentProtocol, Protocol):
    """Planner AIのインターフェース"""
    def analyze_requirements(self, requirements: List[str]) -> List[str]: ...
    def validate_solution(self, solution: Any) -> bool: ...

class BasePlannerAI(BaseAIComponent):
    """Planner AIの基本実装"""
    
    def _get_component_type(self) -> Component:
        return Component.PLANNER
    
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージ処理の基本実装"""
        if message.type == MessageType.COMMAND:
            return self._process_command(message)
        return [self._create_error_response(
            message.receiver,
            "不明なメッセージタイプ"
        )]
    
    def _process_command(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """コマンドメッセージの処理"""
        try:
            action = message.content.get("action")
            if action == "analyze":
                requirements = message.content.get("requirements", [])
                analysis = self.analyze_requirements(requirements)
                return [self._create_response(
                    message.sender,
                    {"analysis": analysis},
                    "analysis_completed"
                )]
            elif action == "validate":
                solution = message.content.get("solution")
                is_valid = self.validate_solution(solution)
                return [self._create_response(
                    message.sender,
                    {"is_valid": is_valid},
                    "validation_completed"
                )]
            return [self._create_error_response(
                message.sender,
                "不明なコマンド"
            )]
        except Exception as e:
            return [self._create_error_response(
                message.sender,
                str(e)
            )]
    
    def analyze_requirements(self, requirements: List[str]) -> List[str]:
        """要件分析の基本実装"""
        pass
        
    def validate_solution(self, solution: Any) -> bool:
        """ソリューション検証の基本実装"""
        pass

# Worker AI
class WorkerProtocol(AIComponentProtocol, Protocol):
    """Worker AIのインターフェース"""
    def execute_task(self, task: Any) -> Any: ...
    def stop_task(self, task_id: str) -> None: ...

class BaseWorkerAI(BaseAIComponent):
    """Worker AIの基本実装"""
    
    def _get_component_type(self) -> Component:
        return Component.WORKER
    
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージ処理の基本実装"""
        if message.type == MessageType.COMMAND:
            return self._process_command(message)
        return [self._create_error_response(
            message.receiver,
            "不明なメッセージタイプ"
        )]
    
    def _process_command(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """コマンドメッセージの処理"""
        try:
            action = message.content.get("action")
            if action == "execute":
                task = message.content.get("task")
                result = self.execute_task(task)
                return [self._create_response(
                    message.sender,
                    {"result": result},
                    "execution_completed"
                )]
            elif action == "stop":
                task_id = message.content.get("task_id")
                self.stop_task(task_id)
                return [self._create_response(
                    message.sender,
                    {"status": "stopped"},
                    "task_stopped"
                )]
            return [self._create_error_response(
                message.sender,
                "不明なコマンド"
            )]
        except Exception as e:
            return [self._create_error_response(
                message.sender,
                str(e)
            )]
    
    def execute_task(self, task: Any) -> Any:
        """タスク実行の基本実装"""
        pass
        
    def stop_task(self, task_id: str) -> None:
        """タスク停止の基本実装"""
        pass

# Reviewer AI
class ReviewerProtocol(AIComponentProtocol, Protocol):
    """Reviewer AIのインターフェース"""
    def evaluate_solution(self, solution: Any) -> List[str]: ...
    def suggest_improvements(self, evaluation: List[str]) -> List[str]: ...

class BaseReviewerAI(BaseAIComponent):
    """Reviewer AIの基本実装"""
    
    def _get_component_type(self) -> Component:
        return Component.REVIEWER
    
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージ処理の基本実装"""
        if message.type == MessageType.COMMAND:
            return self._process_command(message)
        return [self._create_error_response(
            message.receiver,
            "不明なメッセージタイプ"
        )]
    
    def _process_command(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """コマンドメッセージの処理"""
        try:
            action = message.content.get("action")
            if action == "evaluate":
                solution = message.content.get("solution")
                evaluation = self.evaluate_solution(solution)
                return [self._create_response(
                    message.sender,
                    {"evaluation": evaluation},
                    "evaluation_completed"
                )]
            elif action == "suggest":
                evaluation = message.content.get("evaluation", [])
                improvements = self.suggest_improvements(evaluation)
                return [self._create_response(
                    message.sender,
                    {"improvements": improvements},
                    "suggestions_completed"
                )]
            return [self._create_error_response(
                message.sender,
                "不明なコマンド"
            )]
        except Exception as e:
            return [self._create_error_response(
                message.sender,
                str(e)
            )]
    
    def evaluate_solution(self, solution: Any) -> List[str]:
        """ソリューション評価の基本実装"""
        pass
        
    def suggest_improvements(self, evaluation: List[str]) -> List[str]:
        """改善提案の基本実装"""
        pass 