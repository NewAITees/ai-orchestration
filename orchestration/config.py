import os
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

from .ai_types import OrchestratorMode, ComponentType


class OrchestratorSettings(BaseSettings):
    """AIオーケストレーションシステムの設定"""
    
    # 基本設定
    BASE_DIR: Path = Field(default=Path(__file__).resolve().parent.parent)
    DEFAULT_MODEL: str = Field(default="gemma3:27b")
    DEFAULT_MODE: OrchestratorMode = Field(default=OrchestratorMode.CREATIVE)
    
    # Ollama関連の設定
    OLLAMA_HOST: str = Field(default="localhost")
    OLLAMA_PORT: int = Field(default=11434)
    OLLAMA_TIMEOUT: int = Field(default=60)
    OLLAMA_DEFAULT_MODEL: str = Field(default="gemma3:27b")
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    
    # コンポーネント設定
    ENABLED_COMPONENTS: Set[ComponentType] = Field(
        default={
            ComponentType.DIRECTOR,
            ComponentType.PLANNER,
            ComponentType.WORKER,
            ComponentType.REVIEWER
        }
    )
    
    # タイムアウト設定（秒）
    DECOMPOSITION_TIMEOUT: int = Field(default=180)
    EXECUTION_TIMEOUT: int = Field(default=300)
    INTEGRATION_TIMEOUT: int = Field(default=120)
    REVIEW_TIMEOUT: int = Field(default=60)
    
    # 試行回数設定
    MAX_DECOMPOSITION_RETRIES: int = Field(default=3)
    MAX_EXECUTION_RETRIES: int = Field(default=2)
    MAX_REVIEW_RETRIES: int = Field(default=2)
    
    # モデルパラメータ
    DEFAULT_TEMPERATURE: float = Field(default=0.7)
    DEFAULT_TOP_P: float = Field(default=0.9)
    DEFAULT_MAX_TOKENS: int = Field(default=2000)
    
    # セッション設定
    SESSION_EXPIRY_SECONDS: int = Field(default=3600 * 24)  # 24時間
    MAX_SESSIONS_PER_USER: int = Field(default=10)
    
    # ストレージ設定
    STORAGE_TYPE: str = Field(default="memory")  # "memory", "file", "database"
    STORAGE_PATH: str = Field(default="./data/orchestration")
    
    # ロギング設定
    LOG_LEVEL: str = Field(default="INFO")
    ENABLE_DEBUG_LOGGING: bool = Field(default=False)
    LOG_FILE_PATH: str = Field(default="./logs/orchestration.log")
    
    # 創作モード特有の設定
    CREATIVE_MODE_GENRES: List[str] = Field(
        default=[
            "ファンタジー", "SF", "ミステリー", "恋愛", "歴史", "ホラー", 
            "アドベンチャー", "日常", "コメディ", "ドラマ"
        ]
    )
    
    CREATIVE_MODE_STYLES: List[str] = Field(
        default=[
            "フォーマル", "カジュアル", "詩的", "専門的", "会話的", 
            "叙述的", "描写的", "客観的", "主観的"
        ]
    )
    
    CREATIVE_MODE_TONES: List[str] = Field(
        default=[
            "明るい", "暗い", "希望的", "悲観的", "緊張感のある", "穏やか", 
            "シリアス", "ユーモラス", "皮肉的", "感傷的"
        ]
    )
    
    CREATIVE_MODE_STRUCTURES: List[str] = Field(
        default=[
            "三幕構成", "英雄の旅", "五幕構成", "起承転結", "ミステリー形式", 
            "往復構造", "枠物語", "パラレルストーリー"
        ]
    )
    
    # コーディングモード特有の設定（参考用）
    CODING_MODE_LANGUAGES: List[str] = Field(
        default=[
            "Python", "JavaScript", "TypeScript", "Java", "C#", "C++", 
            "Go", "Rust", "Ruby", "PHP", "Swift", "Kotlin"
        ]
    )
    
    # 調査モード特有の設定（参考用）
    RESEARCH_MODE_TYPES: List[str] = Field(
        default=[
            "事実調査", "比較分析", "トレンド分析", "技術解説", 
            "概念説明", "問題解決", "要約"
        ]
    )
    
    class Config:
        """Pydantic設定"""
        env_file = ".env"
        env_prefix = "ORCHESTRATOR_"
        case_sensitive = True
    
    def get_ollama_url(self) -> str:
        """
        OllamaサーバーのURLを取得
        
        Returns:
            str: OllamaサーバーのURL
        """
        return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"


# デフォルトのパラメータ辞書
def get_default_model_parameters() -> Dict[str, Any]:
    """デフォルトのモデルパラメータを取得"""
    settings = OrchestratorSettings()
    return {
        "temperature": settings.DEFAULT_TEMPERATURE,
        "top_p": settings.DEFAULT_TOP_P,
        "max_tokens": settings.DEFAULT_MAX_TOKENS,
    }


def get_mode_specific_parameters(mode: OrchestratorMode) -> Dict[str, Any]:
    """モード固有のパラメータを取得"""
    settings = OrchestratorSettings()
    
    # 基本パラメータ
    base_params = get_default_model_parameters()
    
    # モード別パラメータ
    if mode == OrchestratorMode.CREATIVE:
        # 創作モード: より高い創造性を持たせるパラメータ
        return {
            **base_params,
            "temperature": 0.8,  # やや高め（創造性向上）
            "top_p": 0.92,
        }
    elif mode == OrchestratorMode.CODING:
        # コーディングモード: 正確性を重視したパラメータ
        return {
            **base_params,
            "temperature": 0.3,  # 低め（一貫性と正確性向上）
            "top_p": 0.95,
        }
    elif mode == OrchestratorMode.RESEARCH:
        # 調査モード: バランスの取れたパラメータ
        return {
            **base_params,
            "temperature": 0.5,  # 中間（事実性とわかりやすさのバランス）
            "top_p": 0.9,
        }
    
    # デフォルト
    return base_params


def get_component_specific_parameters(
    component_type: ComponentType,
    mode: OrchestratorMode
) -> Dict[str, Any]:
    """コンポーネント固有のパラメータを取得"""
    # モード別パラメータをベースにする
    base_params = get_mode_specific_parameters(mode)
    
    # コンポーネント別の調整
    if component_type == ComponentType.DIRECTOR:
        # Director: 指示と統合に特化（一貫性重視）
        return {
            **base_params,
            "temperature": max(0.3, base_params["temperature"] - 0.2),
        }
    elif component_type == ComponentType.PLANNER:
        # Planner: 分析と構造化に特化
        return {
            **base_params,
            "temperature": 0.0,  # 決定論的出力を担保
        }
    elif component_type == ComponentType.WORKER:
        # Worker: 実際の創造作業を行う（モード設定を尊重）
        return base_params
    elif component_type == ComponentType.REVIEWER:
        # Reviewer: 分析と評価に特化
        return {
            **base_params,
            "temperature": max(0.3, base_params["temperature"] - 0.2),
        }
    
    # デフォルト
    return base_params


# グローバル設定インスタンス
settings = OrchestratorSettings() 