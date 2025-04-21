from typing import Optional, Dict, Any
from .types import ErrorLevel, TaskStatus, SubtaskStatus


class OrchestrationError(Exception):
    """オーケストレーションシステムの基底例外クラス"""
    def __init__(
        self,
        message: str,
        error_level: ErrorLevel = ErrorLevel.ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_level = error_level
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(OrchestrationError):
    """設定関連のエラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_level=ErrorLevel.ERROR,
            details=details
        )


class ModelError(OrchestrationError):
    """AIモデル関連のエラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_level=ErrorLevel.ERROR,
            details=details
        )


class TaskError(OrchestrationError):
    """タスク処理関連のエラー"""
    def __init__(
        self,
        message: str,
        task_status: TaskStatus,
        details: Optional[Dict[str, Any]] = None
    ):
        self.task_status = task_status
        super().__init__(
            message=message,
            error_level=ErrorLevel.ERROR,
            details=details
        )


class SubtaskError(OrchestrationError):
    """サブタスク処理関連のエラー"""
    def __init__(
        self,
        message: str,
        subtask_status: SubtaskStatus,
        details: Optional[Dict[str, Any]] = None
    ):
        self.subtask_status = subtask_status
        super().__init__(
            message=message,
            error_level=ErrorLevel.ERROR,
            details=details
        )


class SessionError(OrchestrationError):
    """セッション管理関連のエラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_level=ErrorLevel.ERROR,
            details=details
        )


class ValidationError(OrchestrationError):
    """バリデーション関連のエラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_level=ErrorLevel.WARNING,
            details=details
        )


class ComponentError(OrchestrationError):
    """コンポーネント関連のエラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_level=ErrorLevel.ERROR,
            details=details
        )


class PromptError(OrchestrationError):
    """プロンプト処理関連のエラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_level=ErrorLevel.ERROR,
            details=details
        )


class ModeError(OrchestrationError):
    """モード関連のエラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_level=ErrorLevel.ERROR,
            details=details
        )


class CriticalError(OrchestrationError):
    """致命的なエラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_level=ErrorLevel.CRITICAL,
            details=details
        ) 