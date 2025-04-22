import pytest
from typing import Dict, Any, List
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import Settings
from app.orchestration.core.session import Session, CreativeTask
from app.orchestration.components.director import DirectorAI
from app.orchestration.components.reviewer import ReviewerAI
from app.orchestration.components.planner import PlannerAI
from app.orchestration.components.worker import WorkerAI
from app.core.ai_components import DirectorAI as CoreDirectorAI, PlannerAI as CorePlannerAI, WorkerAI as CoreWorkerAI, ReviewerAI
from app.schemas.task import Task, TaskResult

class TestComponentIntegration:
    """コンポーネント間連携の統合テスト"""
    
    @pytest.fixture
    def components(self):
        return {
            "director": CoreDirectorAI(mode="control"),
            "planner": CorePlannerAI(),
            "worker": CoreWorkerAI(),
            "reviewer": ReviewerAI()
        }
    
    @pytest.fixture
    def sample_task(self):
        return Task(
            id="integration_test_task",
            description="Integration test task description",
            priority=1,
            status="pending"
        )
    
    async def test_director_planner_flow(self, components, sample_task):
        """DirectorとPlannerの連携テスト"""
        director = components["director"]
        planner = components["planner"]
        
        # DirectorがタスクをPlannerに委譲
        delegated_task = await director.delegate_to_planner(sample_task)
        assert delegated_task is not None
        
        # Plannerがタスクを分析
        analysis = await planner.analyze_task(delegated_task)
        assert analysis.is_complete()
        
        # Plannerがサブタスクを生成
        sub_tasks = await planner.generate_sub_tasks(analysis.components)
        assert len(sub_tasks) > 0
    
    async def test_worker_reviewer_flow(self, components):
        """WorkerとReviewerの連携テスト"""
        worker = components["worker"]
        reviewer = components["reviewer"]
        
        # テスト用のタスクを作成
        test_task = Task(
            id="worker_reviewer_test",
            description="Test task for worker and reviewer",
            priority=1,
            status="pending"
        )
        
        # Workerがタスクを実行
        result = await worker.execute(test_task)
        assert result.status == "success"
        
        # Reviewerが結果を評価
        evaluation = await reviewer.evaluate(result)
        assert evaluation.is_complete()
        assert evaluation.score >= 0
        
        # Reviewerが品質を評価
        quality = await reviewer.assess_quality(result)
        assert quality.score >= 0
        assert quality.feedback is not None

class TestProcessFlow:
    """プロセスフローの統合テスト"""
    
    @pytest.fixture
    def process_components(self):
        return {
            "director": CoreDirectorAI(mode="control"),
            "planner": CorePlannerAI(),
            "worker": CoreWorkerAI(),
            "reviewer": ReviewerAI()
        }
    
    async def test_complete_workflow(self, process_components):
        """完全なワークフローのテスト"""
        # テスト用のタスクを作成
        task = Task(
            id="complete_workflow_test",
            description="Complete workflow test task",
            priority=1,
            status="pending"
        )
        
        # Directorがタスクを処理
        director = process_components["director"]
        initial_result = await director.execute(task)
        assert initial_result.status == "success"
        
        # Plannerがタスクを分析
        planner = process_components["planner"]
        analysis = await planner.analyze_task(task)
        assert analysis.is_complete()
        
        # Workerがサブタスクを実行
        worker = process_components["worker"]
        sub_tasks = await planner.generate_sub_tasks(analysis.components)
        results = []
        for sub_task in sub_tasks:
            result = await worker.execute(sub_task)
            results.append(result)
            assert result.status == "success"
        
        # Reviewerが結果を評価
        reviewer = process_components["reviewer"]
        for result in results:
            evaluation = await reviewer.evaluate(result)
            assert evaluation.is_complete()
            quality = await reviewer.assess_quality(result)
            assert quality.score >= 0
        
        # Directorが結果を統合
        final_result = await director.integrate(results)
        assert final_result.is_valid()
        assert len(final_result.combined_output) > 0

def test_creative_session_flow(
    client: TestClient,
    test_session: Session,
    evaluator: ReviewerAI,
    planner: PlannerAI,
    worker: WorkerAI
):
    """創作セッションの統合フローテスト"""
    # 1. セッションの作成
    response = client.post(
        "/api/v1/sessions/",
        json={
            "title": "ファンタジー小説創作",
            "description": "魔法学校を舞台にした冒険ファンタジー小説",
            "type": "creative",
            "requirements": [
                "主人公は魔法の才能を持つ少年/少女",
                "学校生活と冒険のバランス",
                "独創的な魔法システム"
            ]
        }
    )
    assert response.status_code == 200
    session_data = response.json()
    session_id = session_data["id"]

    # 2. タスクの計画
    response = client.post(
        f"/api/v1/sessions/{session_id}/plan",
        json={
            "task_type": "creative",
            "requirements": [
                "キャラクター設定",
                "世界観設定",
                "ストーリー概要"
            ]
        }
    )
    assert response.status_code == 200
    plan_data = response.json()
    assert "subtasks" in plan_data
    subtasks = plan_data["subtasks"]
    assert len(subtasks) > 0

    # 3. 最初のサブタスクの実行
    first_task = subtasks[0]
    response = client.post(
        f"/api/v1/sessions/{session_id}/tasks/{first_task['id']}/execute",
        json={
            "context": {},
            "style_guide": {
                "tone": "フレンドリー",
                "perspective": "三人称"
            }
        }
    )
    assert response.status_code == 200
    task_result = response.json()
    assert "content" in task_result
    assert len(task_result["content"]) > 0

    # 4. タスク結果の評価
    response = client.post(
        f"/api/v1/sessions/{session_id}/tasks/{first_task['id']}/evaluate",
        json={
            "evaluation_criteria": {
                "completeness": "要件を満たしているか",
                "creativity": "独創的な要素があるか",
                "consistency": "設定に矛盾がないか"
            }
        }
    )
    assert response.status_code == 200
    evaluation = response.json()
    assert "score" in evaluation
    assert "feedback" in evaluation

    # 5. フィードバックを基にした修正
    response = client.post(
        f"/api/v1/sessions/{session_id}/tasks/{first_task['id']}/revise",
        json={
            "feedback": evaluation["feedback"],
            "focus_points": evaluation.get("improvement_points", [])
        }
    )
    assert response.status_code == 200
    revision = response.json()
    assert "content" in revision
    assert len(revision["content"]) > 0

def test_creative_session_error_handling(client: TestClient):
    """創作セッションのエラーハンドリングテスト"""
    # 1. 無効なセッションID
    response = client.get("/api/v1/sessions/invalid-id")
    assert response.status_code == 404

    # 2. 無効なタスクID
    response = client.post(
        "/api/v1/sessions/test-session/tasks/invalid-task/execute",
        json={"context": {}}
    )
    assert response.status_code == 404

    # 3. 無効なリクエストボディ
    response = client.post(
        "/api/v1/sessions/",
        json={
            "title": "Invalid Session",
            "type": "invalid_type"
        }
    )
    assert response.status_code == 422

def test_creative_session_concurrent_tasks(
    client: TestClient,
    test_session: Session
):
    """創作セッションの並列タスク実行テスト"""
    async def execute_task(task_id: str):
        response = client.post(
            f"/api/v1/sessions/{test_session.id}/tasks/{task_id}/execute",
            json={"context": {}}
        )
        assert response.status_code == 200
        return response.json()
    
    async def run_concurrent_tasks():
        # 複数のタスクを並列で実行
        tasks = [
            {"id": "task1", "type": "character"},
            {"id": "task2", "type": "world"},
            {"id": "task3", "type": "story"}
        ]
        
        results = []
        for task in tasks:
            result = await execute_task(task["id"])
            results.append(result)
        
        return results
    
    # 並列タスクの実行
    results = run_concurrent_tasks()
    assert len(results) == 3
    for result in results:
        assert "content" in result
        assert len(result["content"]) > 0

def test_creative_session_state_management(
    client: TestClient,
    test_session: Session
):
    """創作セッションの状態管理テスト"""
    # 1. セッションの状態を確認
    response = client.get(f"/api/v1/sessions/{test_session.id}/state")
    assert response.status_code == 200
    state = response.json()
    assert "status" in state
    assert "current_task" in state
    
    # 2. タスクの状態を更新
    response = client.put(
        f"/api/v1/sessions/{test_session.id}/tasks/task1/state",
        json={"status": "in_progress"}
    )
    assert response.status_code == 200
    
    # 3. 更新された状態を確認
    response = client.get(f"/api/v1/sessions/{test_session.id}/state")
    assert response.status_code == 200
    updated_state = response.json()
    assert updated_state["current_task"]["status"] == "in_progress"

def test_creative_session_context_management(
    client: TestClient,
    test_session: Session
):
    """創作セッションのコンテキスト管理テスト"""
    # 1. コンテキストの設定
    context = {
        "theme": "魔法学校",
        "genre": "ファンタジー",
        "target_audience": "若年層"
    }
    
    response = client.put(
        f"/api/v1/sessions/{test_session.id}/context",
        json=context
    )
    assert response.status_code == 200
    
    # 2. コンテキストの取得
    response = client.get(f"/api/v1/sessions/{test_session.id}/context")
    assert response.status_code == 200
    retrieved_context = response.json()
    assert retrieved_context == context
    
    # 3. コンテキストの更新
    updated_context = {
        "theme": "魔法学校",
        "genre": "ファンタジー",
        "target_audience": "若年層",
        "tone": "明るく楽しい"
    }
    
    response = client.put(
        f"/api/v1/sessions/{test_session.id}/context",
        json=updated_context
    )
    assert response.status_code == 200
    
    # 4. 更新されたコンテキストを確認
    response = client.get(f"/api/v1/sessions/{test_session.id}/context")
    assert response.status_code == 200
    final_context = response.json()
    assert final_context == updated_context
