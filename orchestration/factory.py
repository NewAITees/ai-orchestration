# orchestration/factory.py
from typing import Dict, Any, Type
from .components.base import BaseAIComponent
# Import specific component classes - adjust paths if necessary
from .components.director import DirectorAI  # Placeholder, replace with actual class
from .components.planner import PlannerAI    # Placeholder, replace with actual class
from .components.worker import WorkerAI      # Placeholder, replace with actual class
from .components.evaluator import EvaluatorAI # Placeholder, replace with actual class
from .components.reviewer import ReviewerAI
# Assuming Reviewer is meant to be Evaluator as per proposal
# from .components.reviewer import ReviewerAI # If ReviewerAI is separate, import it too

from .core.session import Session # Assuming Session is in core
from .llm.llm_manager import BaseLLMManager # Assuming BaseLLMManager exists

class AIComponentFactory:
    """AIコンポーネントのファクトリークラス"""
    
    @staticmethod
    def create_component(
        component_type: str,
        session: Session,
        llm_manager: BaseLLMManager, # Changed from LLMManager to BaseLLMManager based on base.py
        config: Dict[str, Any] = None
    ) -> BaseAIComponent:
        """
        設定に基づいて適切なAIコンポーネントを生成
        
        Args:
            component_type: コンポーネントの種類 ("director", "planner", "worker", "evaluator")
            session: セッションオブジェクト
            llm_manager: LLMマネージャー
            config: コンポーネント固有の設定 (オプション)
            
        Returns:
            生成されたAIコンポーネント
            
        Raises:
            ValueError: 不明なコンポーネントタイプが指定された場合
        """
        # Map component type strings to actual classes
        # Ensure these imports point to the correct classes
        components: Dict[str, Type[BaseAIComponent]] = {
            "director": DirectorAI,
            "planner": PlannerAI,
            "worker": WorkerAI,
            "evaluator": EvaluatorAI,
            # "reviewer": ReviewerAI # Add if Reviewer is a separate component
        }
        
        # Validate component type
        if component_type not in components:
            raise ValueError(f"不明なコンポーネントタイプ: {component_type}")
            
        # Get the correct class constructor
        component_class: Type[BaseAIComponent] = components[component_type]
        
        # Instantiate the component, passing session, llm_manager, and optional config
        # Using **(config or {}) ensures config is passed as kwargs if provided
        # Note: Ensure component constructors accept session, llm_manager, and potentially **kwargs
        return component_class(session, llm_manager, **(config or {}))
    
    @staticmethod
    def create_orchestration_system(
        session: Session,
        llm_manager: BaseLLMManager, # Changed from LLMManager to BaseLLMManager
        config: Dict[str, Any] = None
    ) -> Dict[str, BaseAIComponent]:
        """
        オーケストレーションシステム全体 (全主要コンポーネント) を生成
        
        Args:
            session: セッションオブジェクト
            llm_manager: LLMマネージャー
            config: 各コンポーネントの設定を含む辞書 (オプション)
                     例: {"director": {"setting1": "value1"}, "planner": {"setting2": "value2"}}
            
        Returns:
            コンポーネント名をキーとする生成済みコンポーネントの辞書
        """
        config = config or {}
        
        components = {
            "director": DirectorAI(session, llm_manager),
            "planner": PlannerAI(session, llm_manager),
            "worker": WorkerAI(session, llm_manager),
            "evaluator": EvaluatorAI(session, llm_manager)
        }
        
        # セッションにコンポーネントを設定
        session.components = components
        
        return components 