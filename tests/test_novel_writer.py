import pytest
from typing import List
from app.orchestration.core.session import Session
from app.orchestration.components.director import DefaultDirectorAI
from app.orchestration.components.evaluator import DefaultEvaluatorAI
from app.orchestration.components.planner import DefaultPlannerAI
from app.orchestration.components.worker import DefaultWorkerAI
from app.orchestration.components.llm_manager import LLMManager
from app.cui.novel_writer import NovelWriter

class MockInput:
    def __init__(self, inputs: List[str]):
        self.inputs = inputs
        self.index = 0

    def __call__(self, prompt: str) -> str:
        if self.index >= len(self.inputs):
            raise IndexError("入力シーケンスが終了しました")
        result = self.inputs[self.index]
        self.index += 1
        return result

class MockOutput:
    def __init__(self):
        self.outputs: List[str] = []

    def __call__(self, text: str):
        self.outputs.append(text)

@pytest.fixture
def llm_manager():
    """LLMManagerのフィクスチャ"""
    return LLMManager()

@pytest.fixture
def evaluator(test_session: Session, llm_manager: LLMManager):
    """EvaluatorAIのフィクスチャ"""
    return DefaultEvaluatorAI(test_session, llm_manager)

@pytest.fixture
def planner(test_session: Session, llm_manager: LLMManager):
    """PlannerAIのフィクスチャ"""
    return DefaultPlannerAI(test_session, llm_manager)

@pytest.fixture
def worker(test_session: Session, llm_manager: LLMManager):
    """WorkerAIのフィクスチャ"""
    return DefaultWorkerAI(test_session, llm_manager)

def test_novel_writer_basic_flow(
    test_session: Session,
    evaluator: DefaultEvaluatorAI,
    planner: DefaultPlannerAI,
    worker: DefaultWorkerAI,
    llm_manager: LLMManager
):
    """小説作成の基本フローのテスト"""
    # モックの入力シーケンスを設定
    inputs = [
        "ファンタジーの冒険",  # タイトル
        "1",  # ジャンル（ファンタジー）
        "魔法使いの主人公",  # 要件1
        "冒険ファンタジー",  # 要件2
        "",  # 要件入力終了
        "1",  # タスク選択
        "y",  # 修正確認
        "より詳細な魔法の描写を追加",  # 修正内容
        "n",  # 修正終了
        "0"   # タスク実行終了
    ]
    mock_input = MockInput(inputs)
    mock_output = MockOutput()

    # NovelWriterの初期化と実行
    writer = NovelWriter(
        session=test_session,
        director=DefaultDirectorAI(test_session, llm_manager),
        evaluator=evaluator,
        planner=planner,
        worker=worker,
        input_func=mock_input,
        output_func=mock_output
    )

    writer.run()

    # 出力の検証
    outputs = mock_output.outputs
    assert any("=== 小説作成支援システム ===" in out for out in outputs)
    assert any("小説のタイトルを入力してください" in out for out in outputs)
    assert any("ジャンルを選択してください" in out for out in outputs)
    assert any("=== 要件の収集 ===" in out for out in outputs)
    assert any("=== タスク実行 ===" in out for out in outputs)

    # セッションの状態検証
    assert test_session.title == "ファンタジーの冒険"
    assert test_session.genre == "ファンタジー"
    assert len(test_session.requirements) == 2
    assert "魔法使いの主人公" in test_session.requirements
    assert "冒険ファンタジー" in test_session.requirements

def test_novel_writer_error_handling(
    test_session: Session,
    evaluator: DefaultEvaluatorAI,
    planner: DefaultPlannerAI,
    worker: DefaultWorkerAI,
    llm_manager: LLMManager
):
    """エラーハンドリングのテスト"""
    # 無効な入力を含むシーケンス
    inputs = [
        "",  # 無効なタイトル
        "ファンタジーの冒険",  # 有効なタイトル
        "5",  # 無効なジャンル
        "1",  # 有効なジャンル
        "",  # 要件なし（デフォルト使用）
        "0"   # タスク実行終了
    ]
    mock_input = MockInput(inputs)
    mock_output = MockOutput()

    writer = NovelWriter(
        session=test_session,
        director=DefaultDirectorAI(test_session, llm_manager),
        evaluator=evaluator,
        planner=planner,
        worker=worker,
        input_func=mock_input,
        output_func=mock_output
    )

    writer.run()

    # エラー処理の検証
    outputs = mock_output.outputs
    assert any("無効な入力です" in out for out in outputs)
    assert any("デフォルトの要件を使用します" in out for out in outputs)

    # デフォルト要件の検証
    assert len(test_session.requirements) == 3
    assert "魅力的な主人公" in test_session.requirements
