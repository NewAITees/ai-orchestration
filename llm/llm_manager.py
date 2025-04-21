from typing import Optional, Dict, Any, AsyncGenerator
from abc import ABC, abstractmethod
from datetime import datetime

class BaseLLMManager(ABC):
    """LLMマネージャーの基底クラス
    
    すべてのLLMマネージャー実装が継承すべき基底クラス。
    共通のインターフェースと基本機能を提供する。
    """
    
    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.parameters = parameters or {}
        self.last_used = datetime.now()
        
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """テキスト生成のコア機能
        
        Args:
            prompt: 入力プロンプト
            **kwargs: 追加パラメータ
            
        Returns:
            生成されたテキスト
        """
        pass
        
    @abstractmethod
    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """ストリーミングテキスト生成
        
        Args:
            prompt: 入力プロンプト
            **kwargs: 追加パラメータ
            
        Yields:
            生成されたテキストのチャンク
        """
        pass
        
    def update_last_used(self) -> None:
        """最終使用時刻を更新"""
        self.last_used = datetime.now()

class LLMManager(BaseLLMManager):
    """統合LLMマネージャー
    
    すべてのAIコンポーネントで共通して使用される標準LLMインターフェース。
    具体的な実装はサブクラスで提供される。
    """
    
    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ):
        super().__init__(model_name, api_key, base_url, parameters)
        self._validate_parameters()
        
    def _validate_parameters(self) -> None:
        """パラメータの検証"""
        if not self.model_name:
            raise ValueError("model_name must be specified")
            
    async def generate(self, prompt: str, **kwargs) -> str:
        """テキスト生成の実装"""
        self.update_last_used()
        # 具体的な実装はサブクラスで提供
        raise NotImplementedError
        
    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """ストリーミングテキスト生成の実装"""
        self.update_last_used()
        # 具体的な実装はサブクラスで提供
        raise NotImplementedError 