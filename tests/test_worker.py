import pytest
from typing import Dict, Any, List
from app.orchestration.core.message import OrchestrationMessage, MessageType, Component
from app.orchestration.core.session import SubTask, CreativeTask
from app.orchestration.components.worker import WorkerAI, WorkResult

def test_worker_initialization(worker: WorkerAI, test_session):
    """Worker AIの初期化テスト"""
    assert worker.session == test_session
    assert worker.llm_manager is not None

def test_execute_creative_task(worker: WorkerAI, test_session):
    """創作タスクの実行テスト"""
    task = SubTask(
        id="test_creative_task",
        title="キャラクター紹介文",
        description="主人公の詳細な紹介文を書く",
        requirements=[
            "性格描写を含める",
            "外見の特徴を描写",
            "趣味や特技を含める"
        ]
    )
    test_session.add_subtask(task)
    
    message = OrchestrationMessage(
        type=MessageType.COMMAND,
        sender=Component.DIRECTOR,
        receiver=Component.WORKER,
        content={
            "action": "execute_task",
            "task_id": "test_creative_task"
        },
        session_id=test_session.id
    )
    
    responses = worker.process_message(message)
    
    assert len(responses) == 1
    response = responses[0]
    assert response.type == MessageType.RESPONSE
    assert response.sender == Component.WORKER
    assert response.receiver == Component.DIRECTOR
    
    result = response.content["result"]
    assert isinstance(result, dict)
    assert "content" in result
    assert len(result["content"]) > 0
    assert "requirements_met" in result
    assert isinstance(result["requirements_met"], list)

def test_execute_task_with_context(worker: WorkerAI, test_session):
    """コンテキスト付きのタスク実行テスト"""
    context_task = SubTask(
        id="context_task",
        title="世界観設定",
        description="物語の世界観を設定する",
        result="魔法が日常的に使われる世界。魔法は5つの元素に分類され、各魔法使いは特定の元素との相性が強い。",
        status="completed"
    )
    test_session.add_subtask(context_task)
    
    task = SubTask(
        id="test_context_task",
        title="魔法システムの詳細",
        description="魔法の詳細な仕組みと制限を説明する",
        requirements=["5つの元素の特徴", "魔法の習得方法", "使用時の制限"]
    )
    test_session.add_subtask(task)
    
    message = OrchestrationMessage(
        type=MessageType.COMMAND,
        sender=Component.DIRECTOR,
        receiver=Component.WORKER,
        content={
            "action": "execute_task",
            "task_id": "test_context_task",
            "context": {
                "related_task_ids": ["context_task"]
            }
        },
        session_id=test_session.id
    )
    
    responses = worker.process_message(message)
    result = responses[0].content["result"]
    
    assert "content" in result
    assert "context_usage" in result
    assert isinstance(result["context_usage"], dict)

def test_execute_task_with_style_guide(worker: WorkerAI, test_session):
    """スタイルガイド付きのタスク実行テスト"""
    task = SubTask(
        id="test_style_task",
        title="戦闘シーン",
        description="魔法バトルのシーンを描写する",
        requirements=["臨場感のある描写", "魔法の視覚的な表現"],
        style_guide={
            "tone": "迫力のある",
            "perspective": "三人称視点",
            "tense": "現在形",
            "language_level": "中学生向け"
        }
    )
    test_session.add_subtask(task)
    
    message = OrchestrationMessage(
        type=MessageType.COMMAND,
        sender=Component.DIRECTOR,
        receiver=Component.WORKER,
        content={
            "action": "execute_task",
            "task_id": "test_style_task",
            "style_guide": task.style_guide
        },
        session_id=test_session.id
    )
    
    responses = worker.process_message(message)
    result = responses[0].content["result"]
    
    assert "style_compliance" in result
    assert all(style in result["style_compliance"] for style in task.style_guide)

def test_execute_task_error_handling(worker: WorkerAI, test_session):
    """タスク実行のエラーハンドリングテスト"""
    message = OrchestrationMessage(
        type=MessageType.COMMAND,
        sender=Component.DIRECTOR,
        receiver=Component.WORKER,
        content={
            "action": "execute_task",
            "task_id": "non_existent_task"
        },
        session_id=test_session.id
    )
    
    responses = worker.process_message(message)
    
    assert len(responses) == 1
    response = responses[0]
    assert response.type == MessageType.ERROR
    assert "タスクが見つかりません" in response.content["error"]

def test_execute_task_with_revision_history(worker: WorkerAI, test_session):
    """修正履歴付きのタスク実行テスト"""
    task = SubTask(
        id="test_revision_task",
        title="キャラクター性格描写",
        description="主人公の性格をより詳細に描写する",
        requirements=["具体的なエピソード", "一貫した性格"],
        revision_history=[
            {
                "version": 1,
                "content": "主人公は明るく活発な性格で、誰とでもすぐに仲良くなれる。",
                "feedback": "具体的なエピソードが不足しています。",
                "timestamp": "2024-01-01T10:00:00"
            }
        ]
    )
    test_session.add_subtask(task)
    
    message = OrchestrationMessage(
        type=MessageType.COMMAND,
        sender=Component.DIRECTOR,
        receiver=Component.WORKER,
        content={
            "action": "execute_task",
            "task_id": "test_revision_task",
            "consider_revision_history": True
        },
        session_id=test_session.id
    )
    
    responses = worker.process_message(message)
    result = responses[0].content["result"]
    
    assert "revision_analysis" in result
    assert "improvement_points" in result
