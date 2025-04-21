import pytest
from app.core.ai_components import DirectorAI, PlannerAI, WorkerAI, ReviewerAI
from app.schemas.task import Task, TaskResult

class TestDirectorAI:
    """Director AIの単体テスト"""
    
    @pytest.fixture
    def director(self):
        return DirectorAI(mode="control")
    
    @pytest.fixture
    def sample_task(self):
        return Task(
            id="test_task",
            description="Test task description",
            priority=1,
            status="pending"
        )
    
    async def test_control_mode(self, director, sample_task):
        """制御モードの機能テスト"""
        result = await director.execute(sample_task)
        assert result.status == "success"
        assert result.task_id == sample_task.id
    
    async def test_integration_mode(self, director):
        """統合モードの機能テスト"""
        results = [
            TaskResult(task_id="task1", status="success", output="result1"),
            TaskResult(task_id="task2", status="success", output="result2")
        ]
        integrated_result = await director.integrate(results)
        assert integrated_result.is_valid()
        assert len(integrated_result.combined_output) > 0

class TestPlannerAI:
    """Planner AIの単体テスト"""
    
    @pytest.fixture
    def planner(self):
        return PlannerAI()
    
    async def test_task_analysis(self, planner, sample_task):
        """タスク分析のテスト"""
        analysis = await planner.analyze_task(sample_task)
        assert analysis.is_complete()
        assert len(analysis.subtasks) > 0
    
    async def test_subtask_generation(self, planner):
        """サブタスク生成のテスト"""
        components = ["component1", "component2"]
        sub_tasks = await planner.generate_sub_tasks(components)
        assert len(sub_tasks) > 0
        assert all(isinstance(task, Task) for task in sub_tasks)

class TestWorkerAI:
    """Worker AIの単体テスト"""
    
    @pytest.fixture
    def worker(self):
        return WorkerAI()
    
    async def test_task_execution(self, worker, sample_task):
        """タスク実行のテスト"""
        result = await worker.execute(sample_task)
        assert result.status == "success"
        assert result.task_id == sample_task.id
    
    async def test_error_handling(self, worker):
        """エラーハンドリングのテスト"""
        invalid_task = Task(
            id="invalid_task",
            description="",
            priority=1,
            status="pending"
        )
        result = await worker.execute(invalid_task)
        assert result.status == "error"
        assert result.error_message is not None

class TestReviewerAI:
    """Reviewer AIの単体テスト"""
    
    @pytest.fixture
    def reviewer(self):
        return ReviewerAI()
    
    async def test_result_evaluation(self, reviewer):
        """結果評価のテスト"""
        result = TaskResult(
            task_id="test_task",
            status="success",
            output="Test output"
        )
        evaluation = await reviewer.evaluate(result)
        assert evaluation.is_complete()
        assert evaluation.score >= 0
    
    async def test_quality_assessment(self, reviewer):
        """品質評価のテスト"""
        result = TaskResult(
            task_id="test_task",
            status="success",
            output="High quality output"
        )
        quality = await reviewer.assess_quality(result)
        assert quality.score >= 0
        assert quality.feedback is not None 