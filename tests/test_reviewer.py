import json
import os
import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from orchestration.components.reviewer import ReviewerAI

@pytest.fixture
def reviewer():
    """ReviewerAIインスタンスを提供するフィクスチャ"""
    return ReviewerAI()

@pytest.fixture
def sample_task() -> Dict[str, Any]:
    """サンプルタスクデータを提供するフィクスチャ"""
    return {
        "id": "task-123",
        "description": "Create a function to calculate fibonacci numbers",
        "requirements": [
            "Function should be recursive",
            "Should handle negative numbers",
            "Should include type hints"
        ],
        "acceptance_criteria": [
            "All tests pass",
            "Documentation is complete",
            "Code follows PEP 8"
        ]
    }

@pytest.fixture
def sample_result() -> Dict[str, Any]:
    """サンプルタスク結果データを提供するフィクスチャ"""
    return {
        "task_id": "task-123",
        "code": """
def fibonacci(n: int) -> int:
    '''Calculate the nth fibonacci number recursively.
    
    Args:
        n (int): Position in fibonacci sequence
        
    Returns:
        int: The nth fibonacci number
        
    Raises:
        ValueError: If n is negative
    '''
    if n < 0:
        raise ValueError("Fibonacci is not defined for negative numbers")
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
        """,
        "tests_passed": True,
        "linting_passed": True,
        "documentation_complete": True
    }

@pytest.mark.unit
def test_evaluate_task_returns_valid_structure(reviewer: ReviewerAI, sample_task: Dict, sample_result: Dict):
    """evaluate_taskメソッドが正しい構造の結果を返すことを確認"""
    evaluation = reviewer.evaluate_task(sample_task, sample_result)
    
    assert isinstance(evaluation, dict)
    assert "metrics" in evaluation
    assert "feedback" in evaluation
    assert "score" in evaluation
    
    assert isinstance(evaluation["metrics"], dict)
    assert isinstance(evaluation["feedback"], list)
    assert isinstance(evaluation["score"], float)
    
    assert 0 <= evaluation["score"] <= 1.0
    assert all(isinstance(f, str) for f in evaluation["feedback"])

@pytest.mark.unit
def test_evaluate_task_handles_missing_data(reviewer: ReviewerAI):
    """evaluate_taskメソッドが不完全なデータを適切に処理することを確認"""
    incomplete_task = {"id": "task-123"}
    incomplete_result = {"task_id": "task-123"}
    
    evaluation = reviewer.evaluate_task(incomplete_task, incomplete_result)
    
    assert evaluation["score"] < 0.5  # 不完全なデータは低スコアになるべき
    assert any("missing" in f.lower() for f in evaluation["feedback"])  # 不足データに関するフィードバックがあるべき

@pytest.mark.unit
@patch("orchestration.components.reviewer.ReviewerAI._generate_suggestions")
def test_suggest_improvements_returns_valid_suggestions(
    mock_generate: Mock,
    reviewer: ReviewerAI,
    sample_task: Dict,
    sample_result: Dict
):
    """suggest_improvementsメソッドが有効な改善提案を返すことを確認"""
    mock_generate.return_value = [
        {"priority": "high", "suggestion": "Add more test cases"},
        {"priority": "medium", "suggestion": "Improve documentation"}
    ]
    
    evaluation = reviewer.evaluate_task(sample_task, sample_result)
    suggestions = reviewer.suggest_improvements(evaluation)
    
    assert isinstance(suggestions, list)
    assert all(isinstance(s, dict) for s in suggestions)
    assert all("priority" in s and "suggestion" in s for s in suggestions)
    assert all(s["priority"] in ["high", "medium", "low"] for s in suggestions)

@pytest.mark.unit
def test_save_evaluation_history(reviewer: ReviewerAI, tmp_path, sample_task: Dict, sample_result: Dict):
    """評価履歴が正しく保存されることを確認"""
    output_dir = tmp_path / "evaluations"
    os.makedirs(output_dir, exist_ok=True)
    
    evaluation = reviewer.evaluate_task(sample_task, sample_result)
    reviewer.save_evaluation_history(str(output_dir))
    
    history_file = output_dir / "evaluation_history.json"
    assert history_file.exists()
    
    with open(history_file) as f:
        history = json.load(f)
    
    assert isinstance(history, list)
    assert len(history) > 0
    assert all(isinstance(e, dict) for e in history)

@pytest.mark.unit
def test_suggestion_priority_based_on_score(reviewer: ReviewerAI, sample_task: Dict, sample_result: Dict):
    """スコアに基づいて適切な優先度が設定されることを確認"""
    # 低スコアのケース
    sample_result["tests_passed"] = False
    sample_result["linting_passed"] = False
    evaluation_low = reviewer.evaluate_task(sample_task, sample_result)
    suggestions_low = reviewer.suggest_improvements(evaluation_low)
    
    assert any(s["priority"] == "high" for s in suggestions_low)
    
    # 高スコアのケース
    sample_result["tests_passed"] = True
    sample_result["linting_passed"] = True
    evaluation_high = reviewer.evaluate_task(sample_task, sample_result)
    suggestions_high = reviewer.suggest_improvements(evaluation_high)
    
    assert all(s["priority"] != "high" for s in suggestions_high)

@pytest.mark.unit
def test_error_handling_in_suggest_improvements(reviewer: ReviewerAI):
    """suggest_improvementsメソッドのエラーハンドリングを確認"""
    invalid_evaluation = {"invalid": "data"}
    
    with pytest.raises(ValueError):
        reviewer.suggest_improvements(invalid_evaluation)

@pytest.mark.unit
def test_evaluation_metrics_calculation(reviewer: ReviewerAI, sample_task: Dict, sample_result: Dict):
    """評価メトリクスが正しく計算されることを確認"""
    evaluation = reviewer.evaluate_task(sample_task, sample_result)
    metrics = evaluation["metrics"]
    
    assert "completeness" in metrics
    assert "quality" in metrics
    assert 0 <= metrics["completeness"] <= 1.0
    assert 0 <= metrics["quality"] <= 1.0
    
    # 完全なタスクと結果は高スコアを得るべき
    assert metrics["completeness"] > 0.8
    assert metrics["quality"] > 0.8

@pytest.mark.integration
def test_end_to_end_review_process(reviewer: ReviewerAI, sample_task: Dict, sample_result: Dict, tmp_path):
    """レビュープロセス全体の統合テスト"""
    # 評価の実行
    evaluation = reviewer.evaluate_task(sample_task, sample_result)
    assert evaluation["score"] > 0
    
    # 改善提案の生成
    suggestions = reviewer.suggest_improvements(evaluation)
    assert len(suggestions) > 0
    
    # 履歴の保存
    output_dir = tmp_path / "evaluations"
    os.makedirs(output_dir, exist_ok=True)
    reviewer.save_evaluation_history(str(output_dir))
    
    history_file = output_dir / "evaluation_history.json"
    assert history_file.exists()
    
    # 履歴の検証
    with open(history_file) as f:
        history = json.load(f)
    assert len(history) > 0
    assert history[-1]["score"] == evaluation["score"] 