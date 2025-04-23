"""
デバッグ用のユーティリティクラス
"""
from datetime import datetime
import logging
from typing import Any, Dict, Optional

class Debugger:
    """デバッグ情報の記録と管理を行うクラス"""
    
    def __init__(self, debug_level: str = "info"):
        """
        デバッガーの初期化
        
        Args:
            debug_level: ログレベル（"debug", "info", "warning", "error", "critical"）
        """
        self.debug_level = debug_level.upper()
        self.logger = logging.getLogger(__name__)
        
        # ログレベルの設定
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        self.logger.setLevel(level_map.get(self.debug_level, logging.INFO))
        
        # ハンドラーの設定
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # エラー履歴の初期化
        self.error_history: Dict[str, list] = {}
    
    def log(self, level: str, message: str) -> None:
        """
        ログメッセージを記録
        
        Args:
            level: ログレベル
            message: ログメッセージ
        """
        level = level.upper()
        if hasattr(self.logger, level.lower()):
            log_method = getattr(self.logger, level.lower())
            log_method(message)
    
    def record_error(self, error_type: str, error_msg: str) -> None:
        """
        エラー情報を記録
        
        Args:
            error_type: エラーの種類
            error_msg: エラーメッセージ
        """
        if error_type not in self.error_history:
            self.error_history[error_type] = []
        
        error_record = {
            "timestamp": datetime.now().isoformat(),
            "message": error_msg
        }
        self.error_history[error_type].append(error_record)
        self.log("error", f"{error_type}: {error_msg}")
    
    def get_error_history(self, error_type: Optional[str] = None) -> Dict[str, list]:
        """
        エラー履歴を取得
        
        Args:
            error_type: 特定のエラータイプの履歴を取得する場合に指定
        
        Returns:
            エラー履歴の辞書
        """
        if error_type:
            return {error_type: self.error_history.get(error_type, [])}
        return self.error_history
    
    def clear_error_history(self, error_type: Optional[str] = None) -> None:
        """
        エラー履歴をクリア
        
        Args:
            error_type: 特定のエラータイプの履歴をクリアする場合に指定
        """
        if error_type:
            self.error_history.pop(error_type, None)
        else:
            self.error_history.clear() 