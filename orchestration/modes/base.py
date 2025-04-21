from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class ModeConfig(BaseModel):
    """モード設定を定義するためのベースモデル"""
    
    prompt_templates: Dict[str, str]
    component_settings: Dict[str, Dict[str, Any]]
    process_settings: Dict[str, Any]

class AbstractMode(ABC):
    """すべてのモードの基底クラス"""
    
    def __init__(self):
        self.id: str = self._get_id()
        self.name: str = self._get_name()
        self.description: str = self._get_description()
    
    @abstractmethod
    def _get_id(self) -> str:
        """モードの識別子を返す"""
        pass
    
    @abstractmethod
    def _get_name(self) -> str:
        """表示用の名前を返す"""
        pass
    
    @abstractmethod
    def _get_description(self) -> str:
        """モードの説明を返す"""
        pass
    
    @abstractmethod
    def get_config(self) -> ModeConfig:
        """モードの設定を返す"""
        pass
    
    @abstractmethod
    def initialize(self) -> None:
        """モードの初期化処理"""
        pass 