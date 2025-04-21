import pytest
from typing import Dict, Any
from app.orchestration.core.message import OrchestrationMessage, MessageType, Component
from app.orchestration.core.session import SubTask
from app.orchestration.components.evaluator import EvaluatorAI, EvaluationResult

def test_evaluator_initialization(evaluator: EvaluatorAI, test_session):
    """Evaluator AIの初期化テスト"""
    assert evaluator.session == test_session
    assert evaluator.llm_manager is not None

def test_evaluate_creative_task(evaluator: EvaluatorAI, test_session):
    """創作タスクの評価テスト"""
    # テスト用のタスクを作成
    task = SubTask(
        id="test_creative_task",
        title="キャラクター設定",
        description="主人公の性格と背景を設定する",
        result="主人公は勇敢で正義感が強く、幼少期に両親を失った過去を持つ。"
    )
    test_session.add_subtask(task)
    
    # 評価メッセージの作成
    message = OrchestrationMessage(
        type=MessageType.COMMAND,
        sender=Component.DIRECTOR,
        receiver=Component.EVALUATOR,
        content={"action": "evaluate_task", "task_id": "test_creative_task"},
        session_id=test_session.id
    )
    
    # メッセージの処理
    responses = evaluator.process_message(message)
    
    # レスポンスの検証
    assert len(responses) == 1
    response = responses[0]
    assert response.type == MessageType.RESPONSE
    assert response.sender == Component.EVALUATOR
    assert response.receiver == Component.DIRECTOR
    
    # 評価結果の検証
    result = response.content["result"]
    assert isinstance(result, dict)
    assert result["task_id"] == "test_creative_task"
    assert "score" in result
    assert "feedback" in result
    assert "metrics" in result
    assert "suggestions" in result

def test_evaluate_task_with_criteria(evaluator: EvaluatorAI, test_session):
    """評価基準付きのタスク評価テスト"""
    task = SubTask(
        id="test_criteria_task",
        title="ストーリー展開",
        description="物語の展開を考える",
        result="主人公は古い遺跡で不思議な本を見つけ、その本に書かれた謎を解き明かしていく。",
        criteria={
            "originality": "独創的なアイデアが含まれているか",
            "consistency": "設定に矛盾がないか",
            "engagement": "読者を引き込む展開になっているか"
        }
    )
    test_session.add_subtask(task)
    
    message = OrchestrationMessage(
        type=MessageType.COMMAND,
        sender=Component.DIRECTOR,
        receiver=Component.EVALUATOR,
        content={
            "action": "evaluate_task", 
            "task_id": "test_criteria_task",
            "evaluation_criteria": task.criteria
        },
        session_id=test_session.id
    )
    
    responses = evaluator.process_message(message)
    result = responses[0].content["result"]
    
    assert "metrics" in result
    for criterion in task.criteria.keys():
        assert criterion in result["metrics"]

def test_evaluate_task_error_handling(evaluator: EvaluatorAI, test_session):
    """タスク評価のエラーハンドリングテスト"""
    # 存在しないタスクIDで評価を試みる
    message = OrchestrationMessage(
        type=MessageType.COMMAND,
        sender=Component.DIRECTOR,
        receiver=Component.EVALUATOR,
        content={"action": "evaluate_task", "task_id": "non_existent_task"},
        session_id=test_session.id
    )
    
    responses = evaluator.process_message(message)
    
    assert len(responses) == 1
    response = responses[0]
    assert response.type == MessageType.ERROR
    assert "タスクが見つかりません" in response.content["error"]

def test_invalid_message_type(evaluator: EvaluatorAI):
    """無効なメッセージタイプのテスト"""
    message = OrchestrationMessage(
        type=MessageType.RESPONSE,  # 無効なメッセージタイプ
        sender=Component.DIRECTOR,
        receiver=Component.EVALUATOR,
        content={"action": "evaluate_task", "task_id": "test_task"},
        session_id="test_session"
    )
    
    responses = evaluator.process_message(message)
    
    assert len(responses) == 1
    response = responses[0]
    assert response.type == MessageType.ERROR
    assert "サポートされていないメッセージタイプ" in response.content["error"]

def test_evaluate_task_with_feedback_history(evaluator: EvaluatorAI, test_session):
    """フィードバック履歴を考慮したタスク評価テスト"""
    task = SubTask(
        id="test_feedback_task",
        title="キャラクター設定の改善",
        description="前回のフィードバックを基にキャラクター設定を改善する",
        result="主人公は勇敢で正義感が強く、幼少期に両親を失った過去を持つ。その経験から、弱者を守ることを誓い、魔法学校で修行を積んでいる。",
        feedback_history=[
            {
                "timestamp": "2024-01-01T10:00:00",
                "feedback": "キャラクターの動機が不明確です。",
                "score": 0.7
            }
        ]
    )
    test_session.add_subtask(task)
    
    message = OrchestrationMessage(
        type=MessageType.COMMAND,
        sender=Component.DIRECTOR,
        receiver=Component.EVALUATOR,
        content={
            "action": "evaluate_task", 
            "task_id": "test_feedback_task",
            "consider_feedback_history": True
        },
        session_id=test_session.id
    )
    
    responses = evaluator.process_message(message)
    result = responses[0].content["result"]
    
    assert "previous_feedback_analysis" in result
    assert "improvement_score" in result
