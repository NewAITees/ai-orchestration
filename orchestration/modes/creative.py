from typing import Dict, Any
from .base import AbstractMode, ModeConfig

class CreativeMode(AbstractMode):
    """創作に特化したモード"""
    
    def _get_id(self) -> str:
        return "creative"
    
    def _get_name(self) -> str:
        return "創作モード"
    
    def _get_description(self) -> str:
        return "物語や文章の創作に特化したモード"
    
    def get_config(self) -> ModeConfig:
        return ModeConfig(
            prompt_templates={
                "director_control": "あなたはDirector AIとして創作プロセスを管理します。タスクを分析し、適切なサブタスクに分解し、各コンポーネントに指示を出してください。",
                "planner_analyze": "あなたはPlanner AIとして創作タスクを分析します。物語の構造、キャラクター設定、プロット展開などを考慮して、適切なサブタスクに分解してください。",
                "worker_execute": "あなたはWorker AIとして創作サブタスクを実行します。与えられた指示に従って、創造性豊かな文章を作成してください。",
                "reviewer_evaluate": "あなたはReviewer AIとして創作物を評価します。文章の質、一貫性、創造性などを評価し、改善点を指摘してください。"
            },
            component_settings={
                "director": {
                    "control_mode_enabled": True,
                    "integration_mode_enabled": True
                },
                "planner": {
                    "story_structure_analysis": True,
                    "character_development": True
                },
                "worker": {
                    "creative_writing_enhanced": True,
                    "style_adaptation": True
                },
                "reviewer": {
                    "creativity_evaluation": True,
                    "narrative_coherence_check": True
                }
            },
            process_settings={
                "max_decomposition_depth": 3,
                "feedback_iterations": 2,
                "detailed_planning": True
            }
        )
    
    def initialize(self) -> None:
        # 創作モード固有の初期化ロジック
        pass 