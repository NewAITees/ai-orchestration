import pytest
from typing import Generator
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import Settings
from app.orchestration.core.session import Session
from app.orchestration.components.evaluator import DefaultEvaluatorAI
from app.orchestration.components.planner import DefaultPlannerAI
from app.orchestration.components.worker import DefaultWorkerAI
from app.llm.llm_manager import LLMManager, BaseLLMManager
from app.orchestration.components.base import (
    AIComponent,
    IDirector,
    IPlanner,
    IWorker,
    IReviewer
)
from app.orchestration.core.session import SessionManager
from app.schemas.task import Task, TaskResult, TaskAnalysis
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
from typing import Dict, Any

@pytest.fixture
def test_settings() -> Settings:
    """テスト用の設定を提供するフィクスチャ"""
    return Settings(
        PROJECT_NAME="Test AI Playground",
        API_V1_STR="/api/v1",
        SECRET_KEY="test-secret-key",
        OPENAI_API_KEY="test-openai-key",
        ENVIRONMENT="test"
    )

@pytest.fixture
def client() -> Generator:
    """FastAPIのテストクライアントを提供するフィクスチャ"""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def mock_llm_manager() -> BaseLLMManager:
    """LLMマネージャーのモックを提供"""
    mock = MagicMock(spec=LLMManager)
    mock.generate = AsyncMock(return_value="テスト用の応答です。")
    mock.stream = AsyncMock(return_value=iter(["テスト用の", "ストリーミング", "応答です。"]))
    return mock

@pytest.fixture
def test_task() -> Task:
    """テスト用タスクを提供"""
    return Task(
        id="test-task",
        description="テストタスクの説明",
        priority=1,
        status="pending"
    )

@pytest.fixture
def test_task_result() -> TaskResult:
    """テスト用タスク結果を提供"""
    return TaskResult(
        task_id="test-task",
        status="success",
        output="テスト結果",
        error_message=None
    )

@pytest.fixture
def test_task_analysis() -> TaskAnalysis:
    """テスト用タスク分析を提供"""
    return TaskAnalysis(
        task_id="test-task",
        is_complete=True,
        subtasks=[],
        components=["test-component"]
    )

@pytest.fixture
def test_session() -> Session:
    """テスト用セッションを提供"""
    return Session(
        id="test-session",
        mode="test"
    )

@pytest.fixture
def session_manager() -> SessionManager:
    """セッションマネージャーを提供"""
    return SessionManager()

@pytest.fixture
def mock_components(mock_llm_manager) -> Dict[str, Any]:
    """AIコンポーネントのモックセットを提供"""
    return {
        "director": MagicMock(spec=IDirector),
        "planner": MagicMock(spec=IPlanner),
        "worker": MagicMock(spec=IWorker),
        "reviewer": MagicMock(spec=IReviewer)
    }

@pytest.fixture
def mock_component(mock_llm_manager) -> AIComponent:
    """汎用AIコンポーネントのモックを提供"""
    mock = MagicMock(spec=AIComponent)
    mock.llm_manager = mock_llm_manager
    mock.process = AsyncMock(return_value=TaskResult(
        task_id="test-task",
        status="success",
        output="テスト結果"
    ))
    return mock

@pytest.fixture
def evaluator(test_session: Session, mock_llm_manager: LLMManager) -> DefaultEvaluatorAI:
    """テスト用のEvaluatorAIを提供するフィクスチャ"""
    return DefaultEvaluatorAI(test_session, mock_llm_manager)

@pytest.fixture
def planner(test_session: Session, mock_llm_manager: LLMManager) -> DefaultPlannerAI:
    """テスト用のPlannerAIを提供するフィクスチャ"""
    return DefaultPlannerAI(test_session)

@pytest.fixture
def worker(test_session: Session, mock_llm_manager: LLMManager) -> DefaultWorkerAI:
    """テスト用のWorkerAIを提供するフィクスチャ"""
    return DefaultWorkerAI(test_session)
