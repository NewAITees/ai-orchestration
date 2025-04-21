import pytest
from typing import Dict, Any, List
from app.orchestration.core.message import OrchestrationMessage, MessageType, Component
from app.orchestration.core.session import SubTask, CreativeTask
from app.orchestration.components.planner import PlannerAI, PlanningResult

def test_planner_initialization(planner: PlannerAI, test_session):
    """Planner AIの初期化テスト"""
    assert planner.session == test_session
    assert planner.llm_manager is not None

def test_plan_creative_task(planner: PlannerAI, test_session):
    """創作タスクの計画生成テスト"""
    task = CreativeTask(
        id="test_creative_task",
        title="ファンタジー小説",
        description="魔法学校を舞台にした冒険ファンタジー小説を書く",
        requirements=[
            "主人公は10代の少年/少女",
            "魔法の種類は5種類以上",
            "学校生活と冒険のバランスを取る"
        ]
    )
    test_session.set_main_task(task)
    
    message = OrchestrationMessage(
        type=MessageType.COMMAND,
        sender=Component.DIRECTOR,
        receiver=Component.PLANNER,
        content={
            "action": "plan_task",
            "task_id": "test_creative_task"
        },
        session_id=test_session.id
    )
    
    responses = planner.process_message(message)
    
    assert len(responses) == 1
    response = responses[0]
    assert response.type == MessageType.RESPONSE
    assert response.sender == Component.PLANNER
    assert response.receiver == Component.DIRECTOR
    
    result = response.content["result"]
    assert isinstance(result, dict)
    assert "subtasks" in result
    subtasks = result["subtasks"]
    assert len(subtasks) > 0
    assert all(isinstance(task, dict) for task in subtasks)
    assert all("id" in task and "title" in task and "description" in task for task in subtasks)

def test_plan_task_with_dependencies(planner: PlannerAI, test_session):
    """依存関係のあるタスクの計画生成テスト"""
    task = CreativeTask(
        id="test_dependency_task",
        title="キャラクターと世界観の構築",
        description="物語の主要キャラクターと世界観を設定する",
        requirements=[
            "主要キャラクター3人以上",
            "魔法システムの詳細な設定",
            "学校の基本設定"
        ]
    )
    test_session.set_main_task(task)
    
    message = OrchestrationMessage(
        type=MessageType.COMMAND,
        sender=Component.DIRECTOR,
        receiver=Component.PLANNER,
        content={
            "action": "plan_task",
            "task_id": "test_dependency_task",
            "require_dependencies": True
        },
        session_id=test_session.id
    )
    
    responses = planner.process_message(message)
    result = responses[0].content["result"]
    
    assert "dependencies" in result
    dependencies = result["dependencies"]
    assert isinstance(dependencies, dict)
    assert all(isinstance(dep, list) for dep in dependencies.values())

def test_plan_task_with_constraints(planner: PlannerAI, test_session):
    """制約条件付きのタスク計画生成テスト"""
    task = CreativeTask(
        id="test_constraint_task",
        title="魔法バトルシーン",
        description="学校での魔法バトルシーンを描写する",
        requirements=["迫力のある描写", "魔法の詳細な説明"],
        constraints={
            "word_count": "2000文字以内",
            "violence_level": "中学生向け",
            "magic_types": ["火", "水", "風", "土", "光"]
        }
    )
    test_session.set_main_task(task)
    
    message = OrchestrationMessage(
        type=MessageType.COMMAND,
        sender=Component.DIRECTOR,
        receiver=Component.PLANNER,
        content={
            "action": "plan_task",
            "task_id": "test_constraint_task",
            "constraints": task.constraints
        },
        session_id=test_session.id
    )
    
    responses = planner.process_message(message)
    result = responses[0].content["result"]
    
    assert "constraint_compliance" in result
    assert all(constraint in result["constraint_compliance"] for constraint in task.constraints)

def test_plan_task_error_handling(planner: PlannerAI, test_session):
    """タスク計画のエラーハンドリングテスト"""
    message = OrchestrationMessage(
        type=MessageType.COMMAND,
        sender=Component.DIRECTOR,
        receiver=Component.PLANNER,
        content={
            "action": "plan_task",
            "task_id": "non_existent_task"
        },
        session_id=test_session.id
    )
    
    responses = planner.process_message(message)
    
    assert len(responses) == 1
    response = responses[0]
    assert response.type == MessageType.ERROR
    assert "タスクが見つかりません" in response.content["error"]

def test_plan_task_with_previous_results(planner: PlannerAI, test_session):
    """前回の結果を考慮したタスク計画生成テスト"""
    previous_task = SubTask(
        id="previous_task",
        title="キャラクター設定",
        description="主人公の設定を作成する",
        result="主人公は魔法学校の新入生で、特殊な魔法の才能を持つ。",
        status="completed"
    )
    test_session.add_subtask(previous_task)
    
    current_task = CreativeTask(
        id="test_continuation_task",
        title="ストーリー展開",
        description="主人公の魔法の才能に関連したストーリーを展開する",
        requirements=["前回の設定を活かす", "魔法の才能の具体的な描写"]
    )
    test_session.set_main_task(current_task)
    
    message = OrchestrationMessage(
        type=MessageType.COMMAND,
        sender=Component.DIRECTOR,
        receiver=Component.PLANNER,
        content={
            "action": "plan_task",
            "task_id": "test_continuation_task",
            "consider_previous_results": True
        },
        session_id=test_session.id
    )
    
    responses = planner.process_message(message)
    result = responses[0].content["result"]
    
    assert "previous_task_analysis" in result
    assert "continuation_strategy" in result
