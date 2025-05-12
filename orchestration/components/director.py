from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TYPE_CHECKING, Union, Protocol
from ..core.session import Session, SubTask, SessionStatus
from ..ai_types import TaskStatus, TaskStatusModel, OrchestrationMessage, MessageType, Component, TaskID, SubTask, FinalResult, TaskModel, TaskExecutionResult, SubtaskID
from ..ai_types import OrchestrationMessage, Component
from ..llm import LLMManager
from .base import BaseAIComponent
import json
import traceback
import asyncio
import uuid

class IDirectorAI(Protocol):
    """Director AIのインターフェース"""
    
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass
    
    @abstractmethod
    def get_task_status(self, task_id: str) -> Optional[TaskStatusModel]:
        """指定されたタスクの状態を取得する"""
        pass
    
    @abstractmethod
    def update_task_status(self, task_id: str, status: str, progress: Optional[float] = None, error: Optional[str] = None) -> None:
        """タスクの状態を更新する"""
        pass

class DirectorAI(BaseAIComponent):
    """DirectorAI コンポーネント"""
    component_type = Component.DIRECTOR
    
    def __init__(self, session: Session, llm_manager: LLMManager):
        """
        DirectorAI の初期化
        
        Args:
            session: セッションオブジェクト
            llm_manager: LLMマネージャー
        """
        super().__init__(session)
        self.llm_manager = llm_manager
        self.current_process = None
    
    def _process_command(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """
        コマンドメッセージを処理
        
        Args:
            message: 処理するコマンドメッセージ
            
        Returns:
            応答メッセージのリスト
        """
        content = message.content
        action = content.get("action")
        
        try:
            if action == "start_process":
                task_id = content.get("task_id")
                if not task_id:
                    return [self._create_error_response(
                        message.sender,
                        "task_id が指定されていません"
                    )]
                
                # プロセス開始
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(
                    self.execute_process(task_id)
                )
                
                return [self._create_response(
                    message.sender,
                    {"status": "process_started", "task_id": task_id},
                    "process_started"
                )]
                
            elif action == "integrate_results":
                results = content.get("results", [])
                if not results:
                    return [self._create_error_response(
                        message.sender,
                        "results が指定されていません"
                    )]
                
                # 結果統合
                loop = asyncio.get_event_loop()
                integrated_result = loop.run_until_complete(
                    self.integrate_results(results)
                )
                
                return [self._create_response(
                    message.sender,
                    {"integrated_result": integrated_result},
                    "integration_completed"
                )]
                
            else:
                return [self._create_error_response(
                    message.sender,
                    f"未対応のアクション: {action}"
                )]
        except Exception as e:
            traceback.print_exc()
            return [self._create_error_response(
                message.sender,
                f"コマンド処理中にエラーが発生しました: {str(e)}"
            )]
    
    async def execute_process(self, task_id: TaskID) -> None:
        """
        プロセス全体の実行を制御
        
        Args:
            task_id: メインタスクのID
        """
        print(f"[Director] Starting process for task: {task_id}")
        
        try:
            # セッション状態の更新
            self.session.status = SessionStatus.RUNNING
            
            # タスクオブジェクトを取得または新規作成
            task = self.session.get_subtask(task_id)
            if not task:
                # メインタスクが存在しない場合は新規作成
                task = TaskModel(
                    id=task_id,
                    title=f"タスク {task_id}",
                    description="タスク説明なし"
                )
            
            # タスクの状態を実行中に更新
            self._update_task_status(task_id, TaskStatus.EXECUTING)
            
            # 1. Plannerにタスク計画を依頼
            planner = self.session.get_component("planner")
            if not planner:
                raise ValueError("Plannerコンポーネントが見つかりません")
            
            print(f"[Director] Requesting plan for task: {task_id}")
            plan_result = await planner.plan_task(task)
            
            # 計画の検証
            if not await planner.validate_plan(plan_result):
                print(f"[Director] Plan validation failed for task: {task_id}")
                # 検証失敗時はフォールバック計画を使用
                fallback_plan = self._create_fallback_plan(task)
                print(f"[Director] Using fallback plan")
                plan_result = fallback_plan
            
            # 2. サブタスクの実行
            worker = self.session.get_component("worker")
            if not worker:
                raise ValueError("Workerコンポーネントが見つかりません")
            
            execution_results = []
            subtasks = plan_result.get("subtasks", [])
            dependencies = plan_result.get("dependencies", {})
            
            # 依存関係に基づく実行順序の決定
            execution_order = self._determine_execution_order(subtasks, dependencies)
            
            # サブタスクの順次実行
            for subtask_data in execution_order:
                subtask_id = subtask_data.get("id")
                
                # サブタスクオブジェクトの作成と登録
                subtask = SubTask(
                    id=subtask_id,
                    title=subtask_data.get("title", f"サブタスク {subtask_id}"),
                    description=subtask_data.get("description", ""),
                    requirements=subtask_data.get("requirements", [])
                )
                self.session.add_subtask(subtask)
                
                # サブタスクの実行
                print(f"[Director] Executing subtask: {subtask_id}")
                result = await worker.execute_task(subtask)
                execution_results.append(result)
                
                # 3. 実行結果の評価
                evaluator = self.session.get_component("evaluator")
                if evaluator:
                    print(f"[Director] Evaluating subtask: {subtask_id}")
                    evaluation = await evaluator.evaluate_task(subtask, result)
                    
                    # 評価結果に基づく修正判断
                    if isinstance(evaluation, dict) and evaluation.get("score", 0) < 0.7:
                        print(f"[Director] Low evaluation score, requesting improvements")
                        improvements = await evaluator.suggest_improvements(evaluation)
                        
                        # 改善提案に基づく再実行
                        if improvements and len(improvements) > 0:
                            # 改善情報を追加してタスクを再実行
                            improved_result = await self._reexecute_with_improvements(
                                worker, subtask, result, improvements
                            )
                            
                            # 結果を更新
                            execution_results[-1] = improved_result
            
            # 4. 全体の結果を統合
            print(f"[Director] Integrating results for task: {task_id}")
            final_result = await self.integrate_results(execution_results)
            
            # タスクの状態を完了に更新
            self._update_task_status(task_id, TaskStatus.COMPLETED)
            
            # セッション状態の更新
            self.session.status = SessionStatus.COMPLETED
            print(f"[Director] Process completed for task: {task_id}")
            
        except Exception as e:
            error_msg = f"プロセス実行中にエラーが発生しました: {str(e)}"
            print(f"[Director] {error_msg}")
            traceback.print_exc()
            
            # エラー状態に更新
            self._update_task_status(task_id, TaskStatus.FAILED)
            self.session.status = SessionStatus.FAILED
            
            raise
    
    async def integrate_results(
        self, 
        results: List[Union[TaskExecutionResult, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        実行結果を統合して最終結果を生成
        
        Args:
            results: 統合する実行結果のリスト
            
        Returns:
            統合された最終結果
        """
        print(f"[Director] Integrating {len(results)} results")
        
        # 結果の前処理
        processed_results = []
        for result in results:
            # TaskExecutionResultオブジェクトの場合
            if hasattr(result, 'model_dump'):
                processed_results.append(result.model_dump())
            # 辞書の場合
            elif isinstance(result, dict):
                processed_results.append(result)
            # その他の場合
            else:
                processed_results.append({"content": str(result)})
        
        # テンプレート変数の準備
        variables = {
            "results": processed_results,
            "session_id": self.session.id,
            "session_info": {
                "title": getattr(self.session, 'title', ''),
                "mode": getattr(self.session, 'mode', '')
            }
        }
        
        # セッションモードに応じたテンプレート選択
        mode = getattr(self.session, 'mode', 'generic')
        template_id = f"director/{mode}_integration"
        
        try:
            # LLMを使用して統合結果を生成
            integration_content = await self.llm_manager.generate_with_template(
                template_id, variables
            )
            
            # 結果の解析（JSONの抽出）
            try:
                parsed_result = await self.llm_manager.parse_json_response(integration_content)
            except ValueError:
                # JSON解析に失敗した場合はテキストとして扱う
                parsed_result = {
                    "integrated_content": integration_content,
                    "format": "text"
                }
            
            # 統合結果の構築
            integration_result = {
                "status": "completed",
                "successful_count": sum(1 for r in results if self._is_successful(r)),
                "failed_count": sum(1 for r in results if not self._is_successful(r)),
                "total_results": len(results),
                "integrated_content": parsed_result.get("integrated_content", integration_content),
                "format": parsed_result.get("format", "text"),
                "metadata": parsed_result.get("metadata", {})
            }
            
            print(f"[Director] Integration completed with status: {integration_result['status']}")
            return integration_result
            
        except Exception as e:
            error_msg = f"結果統合中にエラーが発生しました: {str(e)}"
            print(f"[Director] {error_msg}")
            traceback.print_exc()
            
            # エラー結果
            return {
                "status": "error",
                "error": error_msg,
                "successful_count": 0,
                "failed_count": 0,
                "total_results": len(results),
                "integrated_content": "結果統合に失敗しました。"
            }
    
    def _determine_execution_order(
        self, 
        subtasks: List[Dict[str, Any]],
        dependencies: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """
        依存関係に基づいて実行順序を決定
        
        Args:
            subtasks: サブタスクのリスト
            dependencies: 依存関係の辞書
            
        Returns:
            実行順序に並べられたサブタスクのリスト
        """
        # 依存関係グラフの構築
        dependency_graph = {}
        for subtask in subtasks:
            subtask_id = subtask.get("id")
            dependency_graph[subtask_id] = dependencies.get(subtask_id, [])
        
        # トポロジカルソート
        visited = set()
        temp_mark = set()
        order = []
        
        def visit(node):
            if node in temp_mark:
                # 循環依存を検出
                raise ValueError(f"循環依存が検出されました: {node}")
            
            if node not in visited:
                temp_mark.add(node)
                
                # 依存ノードを先に訪問
                for dep in dependency_graph.get(node, []):
                    visit(dep)
                
                temp_mark.remove(node)
                visited.add(node)
                order.append(node)
        
        # すべてのノードを訪問
        for subtask in subtasks:
            subtask_id = subtask.get("id")
            if subtask_id not in visited:
                visit(subtask_id)
        
        # 実行順序に対応するサブタスクリストを作成
        ordered_subtasks = []
        for subtask_id in order:
            for subtask in subtasks:
                if subtask.get("id") == subtask_id:
                    ordered_subtasks.append(subtask)
                    break
        
        return list(reversed(ordered_subtasks))
    
    def _update_task_status(self, task_id: TaskID, status: TaskStatus) -> None:
        """
        タスクの状態を更新
        
        Args:
            task_id: 更新するタスクのID
            status: 新しい状態
        """
        task = self.session.get_subtask(task_id)
        if task:
            task.status = status
            print(f"[Director] Updated task status: {task_id} -> {status}")
        else:
            print(f"[Director] Task not found for status update: {task_id}")
    
    def _is_successful(self, result: Union[TaskExecutionResult, Dict[str, Any]]) -> bool:
        """
        結果が成功かどうかを判定
        
        Args:
            result: 判定する結果
            
        Returns:
            成功ならTrue、失敗ならFalse
        """
        # TaskExecutionResultオブジェクトの場合
        if hasattr(result, 'status'):
            return result.status == TaskStatus.COMPLETED
        
        # 辞書の場合
        if isinstance(result, dict):
            status = result.get("status")
            # 文字列の場合
            if isinstance(status, str):
                return status.lower() in ["completed", "success", "successful"]
            # TaskStatusの場合
            elif status == TaskStatus.COMPLETED:
                return True
        
        # デフォルトは失敗
        return False
    
    def _create_fallback_plan(self, task: Union[TaskModel, SubTask]) -> Dict[str, Any]:
        """
        フォールバック計画を作成
        
        Args:
            task: 対象タスク
            
        Returns:
            フォールバック計画
        """
        task_id = task.id if hasattr(task, 'id') else str(uuid.uuid4())
        task_title = task.title if hasattr(task, 'title') else "タスク"
        task_description = task.description if hasattr(task, 'description') else ""
        
        # シンプルなサブタスク
        subtasks = [
            {
                "id": f"{task_id}-sub1",
                "title": f"{task_title} (単一ステップ)",
                "description": task_description,
                "requirements": task.requirements if hasattr(task, 'requirements') and task.requirements else []
            }
        ]
        
        # フォールバック計画
        return {
            "task_id": task_id,
            "subtasks": subtasks,
            "dependencies": {},
            "strategy": "単一ステップ実行",
            "estimated_steps": 1
        }
    
    async def _reexecute_with_improvements(
        self,
        worker,
        subtask: SubTask,
        result: Union[TaskExecutionResult, Dict[str, Any]],
        improvements: List[Dict[str, Any]]
    ) -> Union[TaskExecutionResult, Dict[str, Any]]:
        """
        改善提案に基づいてタスクを再実行
        
        Args:
            worker: WorkerAIコンポーネント
            subtask: 対象サブタスク
            result: 前回の実行結果
            improvements: 改善提案
            
        Returns:
            再実行結果
        """
        print(f"[Director] Re-executing subtask with improvements: {subtask.id}")
        
        # 改善情報の抽出
        improvement_descriptions = []
        for imp in improvements:
            if isinstance(imp, dict) and "description" in imp:
                improvement_descriptions.append(imp["description"])
            else:
                improvement_descriptions.append(str(imp))
        
        # コンテキスト情報の準備
        context = {
            "previous_result": result,
            "improvements": improvement_descriptions
        }
        
        # タスクの再実行
        improved_result = await worker.execute_task(
            subtask,
            context=context,
            style_guide={"improvement_focus": True}
        )
        
        return improved_result

class DefaultDirectorAI(DirectorAI):
    """デフォルトのDirectorAI実装"""
    
    async def execute_process(self, task_id: TaskID) -> None:
        """
        プロセス全体の実行を制御
        
        Args:
            task_id: メインタスクのID
        """
        await super().execute_process(task_id)
    
    async def integrate_results(
        self, 
        results: List[Union[TaskExecutionResult, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        実行結果を統合して最終結果を生成
        
        Args:
            results: 統合する実行結果のリスト
            
        Returns:
            統合された最終結果
        """
        return await super().integrate_results(results) 