from enum import Enum, auto
from typing import Dict, List, Optional, Any, Set
from pydantic import BaseModel, Field
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

class ExecutionState(Enum):
    """タスク実行ループの状態を表す列挙型"""
    INITIALIZED = auto()  # 初期化済み
    SCHEDULING = auto()   # スケジューリング中
    EXECUTING = auto()    # 実行中
    COMPLETED = auto()    # 完了
    FAILED = auto()       # 失敗

@dataclass
class TaskDependency:
    """タスクの依存関係を表すデータクラス"""
    task_id: str
    depends_on: List[str]
    priority: int = 1  # 優先度（1が最高）

class ExecutionResult(BaseModel):
    """タスク実行結果を表すモデル"""
    task_id: str
    status: str  # "success", "failure", "partial"
    output: Any
    error: Optional[str] = None
    execution_time: float
    created_at: datetime = Field(default_factory=datetime.now)

class TaskExecutionLoop:
    """タスク実行ループを管理するクラス"""
    
    def __init__(self, subtasks: List[TaskDependency]):
        self.subtasks = subtasks
        self.state = ExecutionState.INITIALIZED
        self.execution_results: Dict[str, ExecutionResult] = {}
        self.dependency_graph = self._build_dependency_graph()
        self.execution_order = self._calculate_execution_order()
        
    def _build_dependency_graph(self) -> Dict[str, Set[str]]:
        """依存関係グラフを構築する"""
        graph = defaultdict(set)
        for task in self.subtasks:
            for dep in task.depends_on:
                graph[task.task_id].add(dep)
        return dict(graph)
    
    def _calculate_execution_order(self) -> List[str]:
        """トポロジカルソートを使用して実行順序を計算する"""
        visited = set()
        temp = set()
        order = []
        
        def visit(node: str):
            if node in temp:
                raise ValueError("循環依存が検出されました")
            if node in visited:
                return
                
            temp.add(node)
            for neighbor in self.dependency_graph.get(node, set()):
                visit(neighbor)
                
            temp.remove(node)
            visited.add(node)
            order.append(node)
        
        for task in self.subtasks:
            if task.task_id not in visited:
                visit(task.task_id)
                
        return list(reversed(order))
    
    def _check_dependencies_met(self, task_id: str) -> bool:
        """タスクの依存関係が満たされているかチェックする"""
        for dep in self.dependency_graph.get(task_id, set()):
            if dep not in self.execution_results:
                return False
            if self.execution_results[dep].status != "success":
                return False
        return True
    
    def execute_task(self, task_id: str) -> ExecutionResult:
        """個々のタスクを実行する"""
        # TODO: 実際のタスク実行ロジックを実装
        return ExecutionResult(
            task_id=task_id,
            status="success",
            output=f"Task {task_id} executed successfully",
            execution_time=1.0
        )
    
    def run(self) -> bool:
        """タスク実行ループを実行する"""
        try:
            self.state = ExecutionState.SCHEDULING
            
            for task_id in self.execution_order:
                if not self._check_dependencies_met(task_id):
                    continue
                    
                self.state = ExecutionState.EXECUTING
                result = self.execute_task(task_id)
                self.execution_results[task_id] = result
                
                if result.status == "failure":
                    self.state = ExecutionState.FAILED
                    return False
            
            self.state = ExecutionState.COMPLETED
            return True
            
        except Exception as e:
            self.state = ExecutionState.FAILED
            raise e 