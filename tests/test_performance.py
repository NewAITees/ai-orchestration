import pytest
import time
import asyncio
from datetime import datetime, timedelta
from app.core.ai_components import DirectorAI, PlannerAI, WorkerAI, ReviewerAI
from app.schemas.task import Task, TaskResult

class TestPerformance:
    """パフォーマンステスト"""
    
    MAX_RESPONSE_TIME = 5.0  # 秒
    MAX_CONCURRENT_TASKS = 10
    
    @pytest.fixture
    def components(self):
        return {
            "director": DirectorAI(mode="control"),
            "planner": PlannerAI(),
            "worker": WorkerAI(),
            "reviewer": ReviewerAI()
        }
    
    @pytest.fixture
    def sample_tasks(self):
        return [
            Task(
                id=f"performance_test_{i}",
                description=f"Performance test task {i}",
                priority=1,
                status="pending"
            )
            for i in range(self.MAX_CONCURRENT_TASKS)
        ]
    
    async def measure_response_time(self, func, *args, **kwargs):
        """レスポンス時間を測定するヘルパー関数"""
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time
    
    async def test_response_time(self, components, sample_tasks):
        """レスポンス時間のテスト"""
        director = components["director"]
        response_times = []
        
        for task in sample_tasks:
            _, response_time = await self.measure_response_time(
                director.execute, task
            )
            response_times.append(response_time)
        
        max_response_time = max(response_times)
        assert max_response_time < self.MAX_RESPONSE_TIME, \
            f"最大レスポンス時間 {max_response_time}秒が許容値 {self.MAX_RESPONSE_TIME}秒を超えています"
    
    async def test_concurrent_processing(self, components, sample_tasks):
        """並行処理のテスト"""
        director = components["director"]
        start_time = time.time()
        
        # 並行してタスクを実行
        tasks = [
            director.execute(task)
            for task in sample_tasks
        ]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # すべてのタスクが成功したことを確認
        assert all(result.status == "success" for result in results)
        
        # 並行処理の効率性を確認
        avg_time_per_task = total_time / len(sample_tasks)
        assert avg_time_per_task < self.MAX_RESPONSE_TIME, \
            f"タスクあたりの平均処理時間 {avg_time_per_task}秒が許容値 {self.MAX_RESPONSE_TIME}秒を超えています"
    
    async def test_resource_usage(self, components):
        """リソース使用量のテスト"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # 初期リソース使用量を記録
        initial_memory = process.memory_info().rss
        initial_cpu = process.cpu_percent()
        
        # 負荷をかける
        director = components["director"]
        tasks = [
            Task(
                id=f"resource_test_{i}",
                description=f"Resource test task {i}",
                priority=1,
                status="pending"
            )
            for i in range(100)
        ]
        
        # タスクを実行
        for task in tasks:
            await director.execute(task)
        
        # 最終リソース使用量を記録
        final_memory = process.memory_info().rss
        final_cpu = process.cpu_percent()
        
        # メモリリークがないことを確認
        memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB
        assert memory_increase < 100, f"メモリ使用量が100MB以上増加しています: {memory_increase}MB"
        
        # CPU使用率が許容範囲内であることを確認
        assert final_cpu < 90, f"CPU使用率が90%を超えています: {final_cpu}%"
    
    async def test_scalability(self, components):
        """スケーラビリティのテスト"""
        director = components["director"]
        batch_sizes = [10, 50, 100]
        results = []
        
        for batch_size in batch_sizes:
            tasks = [
                Task(
                    id=f"scalability_test_{i}",
                    description=f"Scalability test task {i}",
                    priority=1,
                    status="pending"
                )
                for i in range(batch_size)
            ]
            
            start_time = time.time()
            results = await asyncio.gather(*[director.execute(task) for task in tasks])
            end_time = time.time()
            
            total_time = end_time - start_time
            avg_time_per_task = total_time / batch_size
            
            results.append({
                "batch_size": batch_size,
                "total_time": total_time,
                "avg_time_per_task": avg_time_per_task
            })
        
        # バッチサイズが大きくなっても、タスクあたりの処理時間が線形に増加しないことを確認
        for i in range(1, len(results)):
            prev_result = results[i-1]
            curr_result = results[i]
            
            # バッチサイズの増加率
            size_increase = curr_result["batch_size"] / prev_result["batch_size"]
            # 処理時間の増加率
            time_increase = curr_result["avg_time_per_task"] / prev_result["avg_time_per_task"]
            
            # 処理時間の増加率がバッチサイズの増加率より小さいことを確認
            assert time_increase < size_increase, \
                f"バッチサイズ {curr_result['batch_size']} でスケーラビリティの問題が発生しています" 