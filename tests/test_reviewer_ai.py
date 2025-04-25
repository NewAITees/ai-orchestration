import asyncio
import json
import os
import pytest
from typing import Dict, Any, List
from pathlib import Path

from orchestration.llm.llm_manager import LLMManager
from orchestration.components.reviewer import ReviewerAI
from orchestration.core.session import Session
from orchestration.types import (
    TaskStatus,
    SubtaskStatus,
    SubTask,
    TaskExecutionResult,
    EvaluationResult,
    EvaluationStatus
)

@pytest.fixture
def test_dir():
    """テストデータディレクトリのfixture"""
    dir_path = Path("./tests/reviewer_test_data")
    dir_path.mkdir(parents=True, exist_ok=True)
    yield dir_path
    # クリーンアップ: テストデータの削除
    for file in dir_path.glob("*.json"):
        file.unlink()
    if dir_path.exists():
        dir_path.rmdir()

@pytest.fixture
def session():
    """テストセッションのfixture"""
    return Session(id="test-reviewer-session")

@pytest.fixture
def reviewer(session, test_dir):
    """ReviewerAIインスタンスのfixture"""
    llm_manager = LLMManager(
        parameters={"temperature": 0.0, "top_p": 1.0, "max_tokens": 2000}
    )
    return ReviewerAI(session=session, llm_manager=llm_manager, output_dir=str(test_dir))

@pytest.fixture
def test_task(session):
    """テスト用タスクのfixture"""
    task = SubTask(
        id="task-1",
        title="キャラクター設定の作成",
        description="ファンタジー小説の主人公となる魔法使いの見習いのキャラクター設定を作成する。",
        requirements=["個性的な性格", "成長の余地がある", "魔法の才能に特徴がある"],
        status=SubtaskStatus.IN_PROGRESS
    )
    session.add_subtask(task)
    return task

@pytest.fixture
def test_result():
    """テスト用実行結果のfixture"""
    return TaskExecutionResult(
        task_id="task-1",
        status=TaskStatus.COMPLETED,
        result={
            "character": {
                "name": "エルウィン・リード",
                "age": 16,
                "gender": "男性",
                "appearance": [
                    "煤けたような黒髪",
                    "深い緑色の瞳",
                    "痩身で小柄な体格"
                ],
                "personality": [
                    "好奇心旺盛",
                    "やや内向的",
                    "努力家"
                ],
                "magic_talent": [
                    "一般的な魔法は平均以下",
                    "古代魔法に対して特異な感応力を持つ"
                ]
            }
        }
    )

@pytest.mark.asyncio
async def test_reviewer_task_evaluation(reviewer, test_task, test_result, test_dir):
    """ReviewerAIのタスク評価機能をテストする"""
    # 2回評価を実行
    result1 = await reviewer.evaluate_task(test_task, test_result)
    result2 = await reviewer.evaluate_task(test_task, test_result)
    
    # 評価結果の検証
    assert isinstance(result1, EvaluationResult)
    assert result1.task_id == test_task.id
    assert result1.status == TaskStatus.COMPLETED
    assert 0 <= result1.score <= 1.0
    assert isinstance(result1.feedback, str)
    assert isinstance(result1.metrics, dict)
    
    # 同じ入力に対して同じ結果が得られることを確認（created_atを除外）
    result1_dict = result1.model_dump()
    result2_dict = result2.model_dump()
    result1_dict.pop('created_at', None)
    result2_dict.pop('created_at', None)
    assert result1_dict == result2_dict
    
    # 評価履歴の保存を確認
    reviewer.save_evaluation_history()
    history_files = list(test_dir.glob("evaluation_history_*.json"))
    assert len(history_files) > 0
    
    # 最新の履歴ファイルを読み込んで検証
    latest_history_file = max(history_files, key=lambda p: p.stat().st_mtime)
    with open(latest_history_file) as f:
        history = json.load(f)
    
    assert len(history) >= 2  # 2回の評価結果が含まれているはず
    assert history[-1]["task_id"] == test_task.id
    assert history[-1]["score"] == result2.score

@pytest.mark.asyncio
async def test_evaluate_task(reviewer, test_task):
    """evaluate_taskメソッドの非同期テスト"""
    evaluation = await reviewer.evaluate_task(test_task, test_task.description)
    
    assert isinstance(evaluation, EvaluationResult)
    assert evaluation.task_id == test_task.id
    assert evaluation.status == TaskStatus.COMPLETED
    assert 0 <= evaluation.score <= 1.0
    assert isinstance(evaluation.feedback, str)
    assert isinstance(evaluation.metrics, dict)

@pytest.mark.asyncio
async def test_suggest_improvements(reviewer, test_task, test_result):
    """suggest_improvementsメソッドの非同期テスト"""
    review_result = await reviewer.review_task(test_task, test_result)
    improvements = await reviewer.suggest_improvements(review_result)
    
    assert improvements is not None
    assert isinstance(improvements, list)
    assert len(improvements) > 0
    for improvement in improvements:
        assert isinstance(improvement, dict)
        assert "title" in improvement
        assert "description" in improvement
        assert "priority" in improvement
        assert improvement["priority"] in ["high", "medium", "low"]

@pytest.mark.asyncio
async def test_calculate_metrics(reviewer, test_task, test_result):
    """_calculate_metricsメソッドの非同期テスト"""
    llm_response = await reviewer._generate_with_template(
        "orchestration/prompts/reviewer/evaluate.prompt",
        {"task": test_task.model_dump(), "result": test_result.model_dump()}
    )
    metrics = await reviewer._calculate_metrics(test_task, test_result, llm_response)
    
    assert metrics is not None
    assert 0 <= metrics.quality <= 1.0
    assert 0 <= metrics.completeness <= 1.0
    assert 0 <= metrics.relevance <= 1.0
    assert 0 <= metrics.creativity <= 1.0
    assert 0 <= metrics.technical_accuracy <= 1.0

if __name__ == "__main__":
    pytest.main(["-v", __file__])