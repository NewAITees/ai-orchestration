"""
アプリケーション設定を管理するモジュール
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    アプリケーション設定クラス
    
    環境変数から設定を読み込み、デフォルト値を提供します。
    """
    
    # プロジェクトのベースディレクトリ
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    # ログ関連の設定
    LOG_DIR: Path = BASE_DIR / "logs"
    LOG_LEVEL: str = "info"
    MAX_LOGS: int = 1000
    
    # Agno関連の設定
    AGNO_HOST: str = "localhost"
    AGNO_PORT: int = 8000
    AGNO_TIMEOUT: int = 30
    AGNO_DEBUG: bool = False
    
    # Ollama関連の設定
    OLLAMA_HOST: str = "localhost"
    OLLAMA_PORT: int = 11434
    OLLAMA_TIMEOUT: int = 60
    OLLAMA_DEFAULT_MODEL: str = "gemma3:27b"
    OLLAMA_BASE_URL: str = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
    DEFAULT_MODEL: str = OLLAMA_DEFAULT_MODEL
    DEBUG_LEVEL: str = LOG_LEVEL
    
    # APIサーバーの設定
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_DEBUG: bool = False
    
    # セキュリティ設定
    API_KEY: Optional[str] = None
    SECRET_KEY: str = "your-secret-key-here"  # 本番環境では必ず変更してください
    
    # CORS設定
    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]
    
    # キャッシュ設定
    CACHE_TTL: int = 3600  # 1時間
    MAX_CACHE_SIZE: int = 1000
    
    # レート制限設定
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 3600  # 1時間あたり
    
    # モック設定 - テスト/開発時に使用
    MOCK_RESPONSES: bool = os.getenv("MOCK_RESPONSES", "True").lower() in ("true", "1", "t")
    
    class Config:
        """Pydantic設定クラス"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_agno_url(self) -> str:
        """
        AgnoサーバーのURLを取得
        
        Returns:
            str: AgnoサーバーのURL
        """
        return f"http://{self.AGNO_HOST}:{self.AGNO_PORT}"
    
    def get_ollama_url(self) -> str:
        """
        OllamaサーバーのURLを取得
        
        Returns:
            str: OllamaサーバーのURL
        """
        return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"
    
    def get_api_url(self) -> str:
        """
        APIサーバーのURLを取得
        
        Returns:
            str: APIサーバーのURL
        """
        return f"http://{self.API_HOST}:{self.API_PORT}"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        設定を辞書形式で取得
        
        Returns:
            Dict[str, Any]: 設定の辞書
        """
        return {
            key: str(value) if isinstance(value, Path) else value
            for key, value in self.model_dump().items()
        }

# グローバル設定インスタンス
settings = Settings() 