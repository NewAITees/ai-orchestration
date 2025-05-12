"""
Agnoフレームワークを活用したWorkerAIコンポーネント

WorkerAIは、オーケストレーションシステムにおいて実際のタスクを実行する役割を担います。
LLMを活用してコンテンツ生成や問題解決を行い、要件に基づく結果の検証も行います。
"""
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json
import traceback
import asyncio

from ..ai_types import (
    TaskStatus, TaskExecutionResult, SubTask, 
    IWorkerAI, BaseAIComponent, Component,
    MessageType, OrchestrationMessage
)
from ..llm.llm_manager import LLMManager
from ..core.session import Session

class WorkerAI(BaseAIComponent):
    """WorkerAI コンポーネント"""
    component_type = Component.WORKER
    
    def __init__(self, session: Session, llm_manager: LLMManager):
        """
        WorkerAI の初期化
        
        Args:
            session: セッションオブジェクト
            llm_manager: LLMマネージャー
        """
        super().__init__(session)
        self.llm_manager = llm_manager
    
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """
        メッセージを処理し、応答メッセージのリストを返す
        
        Args:
            message: 処理するメッセージ
            
        Returns:
            応答メッセージのリスト
        """
        if message.type != MessageType.COMMAND:
            return [self._create_error_message(
                message.sender,
                f"サポートされていないメッセージタイプ: {message.type}"
            )]
        
        content = message.content
        action = content.get("action")
        
        try:
            if action == "execute_task":
                task_id = content.get("task_id")
                if not task_id:
                    return [self._create_error_message(
                        message.sender,
                        "task_id が指定されていません"
                    )]
                
                # タスク実行
                task = self.session.get_subtask(task_id)
                if not task:
                    return [self._create_error_message(
                        message.sender,
                        f"タスクが見つかりません: {task_id}"
                    )]
                
                context = content.get("context", {})
                style_guide = content.get("style_guide", {})
                execution_params = content.get("execution_params", {})
                
                # 非同期処理を同期的に実行
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(
                    self.execute_task(
                        task, 
                        context=context, 
                        style_guide=style_guide,
                        **execution_params
                    )
                )
                
                # 結果をレスポンスに変換
                return [self._create_message(
                    message.sender,
                    MessageType.RESPONSE,
                    {"result": result.model_dump() if hasattr(result, 'model_dump') else result}
                )]
            elif action == "stop_execution":
                task_id = content.get("task_id")
                if not task_id:
                    return [self._create_error_message(
                        message.sender,
                        "task_id が指定されていません"
                    )]
                
                # 実行停止
                self.stop_execution(task_id)
                
                return [self._create_message(
                    message.sender,
                    MessageType.RESPONSE,
                    {"task_id": task_id, "status": "stopped"}
                )]
            else:
                return [self._create_error_message(
                    message.sender,
                    f"未対応のアクション: {action}"
                )]
        except Exception as e:
            traceback.print_exc()
            return [self._create_error_message(
                message.sender,
                f"コマンド処理中にエラーが発生しました: {str(e)}"
            )]
    
    async def execute_task(
        self, 
        task: SubTask, 
        context: Optional[Dict[str, Any]] = None,
        style_guide: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> TaskExecutionResult:
        """
        タスクを実行
        
        Args:
            task: 実行するサブタスク
            context: 実行コンテキスト（オプション）
            style_guide: スタイルガイド（オプション）
            **kwargs: 追加パラメータ
            
        Returns:
            タスク実行結果
        """
        print(f"[Worker] Executing task: {task.id} - {task.title}")
        context = context or {}
        style_guide = style_guide or {}
        
        # タスクタイプに応じたテンプレート選択
        task_type = self._determine_task_type(task)
        template_id = f"worker/{task_type}_execution"
        print(f"[Worker] Using template: {template_id}")
        
        # テンプレート変数の準備
        variables = {
            "task_id": task.id,
            "task_title": task.title,
            "task_description": task.description,
            "requirements": task.requirements if hasattr(task, 'requirements') and task.requirements else [],
            "context": context,
            "style_guide": style_guide
        }
        
        start_time = datetime.now()
        
        try:
            # LLMを使用して実行結果を生成
            task.status = "executing"  # 状態更新
            
            # コンテキスト情報の収集
            context_data = await self._gather_context_data(task, context)
            if context_data:
                variables["context_data"] = context_data
            
            # タスク履歴情報の収集
            task_history = await self._gather_task_history(task)
            if task_history:
                variables["task_history"] = task_history
            
            # LLMによる生成
            print(f"[Worker] Generating content for task: {task.id}")
            result_content = await self.llm_manager.generate_with_template(
                template_id, variables, **kwargs
            )
            
            # 結果の検証
            requirements_met = await self._validate_requirements(
                result_content, task.requirements if hasattr(task, 'requirements') and task.requirements else []
            )
            
            # 実行結果の構造化
            task.result = result_content
            task.status = "completed"
            
            execution_time = datetime.now() - start_time
            
            # 結果オブジェクトの作成
            result = TaskExecutionResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                result={
                    "content": result_content,
                    "requirements_met": requirements_met,
                    "execution_time_ms": execution_time.total_seconds() * 1000
                },
                created_at=datetime.now()
            )
            
            print(f"[Worker] Task completed: {task.id}")
            return result
            
        except Exception as e:
            execution_time = datetime.now() - start_time
            error_msg = f"タスク実行中にエラーが発生しました: {str(e)}"
            print(f"[Worker] {error_msg}")
            
            # エラー状態に更新
            task.status = "failed"
            
            # エラー結果の作成
            result = TaskExecutionResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                result={
                    "error": error_msg,
                    "execution_time_ms": execution_time.total_seconds() * 1000
                },
                created_at=datetime.now()
            )
            
            return result
    
    def stop_execution(self, task_id: str) -> None:
        """
        タスクの実行を停止
        
        Args:
            task_id: 停止するタスクのID
        """
        task = self.session.get_subtask(task_id)
        if task and task.status == "executing":
            task.status = "stopped"
            print(f"[Worker] Task execution stopped: {task_id}")
    
    async def _gather_context_data(
        self, 
        task: SubTask, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        コンテキスト情報を収集
        
        Args:
            task: 実行するタスク
            context: 実行コンテキスト
            
        Returns:
            収集されたコンテキスト情報
        """
        context_data = {}
        
        # 関連タスクの結果を収集
        related_task_ids = context.get("related_task_ids", [])
        if related_task_ids:
            related_results = {}
            for related_id in related_task_ids:
                related_task = self.session.get_subtask(related_id)
                if related_task and related_task.result:
                    related_results[related_id] = {
                        "title": related_task.title,
                        "result": related_task.result
                    }
            
            if related_results:
                context_data["related_results"] = related_results
        
        # セッション情報を収集
        context_data["session_info"] = {
            "id": self.session.id,
            "title": getattr(self.session, 'title', ''),
            "mode": getattr(self.session, 'mode', '')
        }
        
        return context_data
    
    async def _gather_task_history(self, task: SubTask) -> List[Dict[str, Any]]:
        """
        タスクの履歴情報を収集
        
        Args:
            task: 対象タスク
            
        Returns:
            タスク履歴情報
        """
        history = []
        
        # 修正履歴の収集
        if hasattr(task, 'revision_history') and task.revision_history:
            history.extend(task.revision_history)
        
        # フィードバック履歴の収集
        if hasattr(task, 'feedback_history') and task.feedback_history:
            history.extend(task.feedback_history)
        
        return history
    
    async def _validate_requirements(
        self, 
        result_content: str, 
        requirements: List[str]
    ) -> List[str]:
        """
        要件の充足度を検証
        
        Args:
            result_content: 生成された結果
            requirements: 要件リスト
            
        Returns:
            満たされた要件のリスト
        """
        if not requirements:
            return []
        
        try:
            # LLMを使用して要件の充足度を検証
            template_id = "worker/requirements_validation"
            variables = {
                "result_content": result_content,
                "requirements": requirements
            }
            
            validation_result = await self.llm_manager.generate_with_template(
                template_id, variables
            )
            
            # 結果の解析（JSONの抽出）
            parsed_result = await self.llm_manager.parse_json_response(validation_result)
            requirements_met = parsed_result.get("requirements_met", [])
            
            return requirements_met
            
        except Exception as e:
            print(f"[Worker] Error validating requirements: {e}")
            return []
    
    def _determine_task_type(self, task: SubTask) -> str:
        """
        タスクタイプを判定
        
        Args:
            task: 判定するタスク
            
        Returns:
            タスクタイプ
        """
        # タスクタイプの明示的な指定があれば使用
        if hasattr(task, 'task_type') and task.task_type:
            return task.task_type
        
        # タイトルと説明から判定
        title = task.title.lower()
        description = task.description.lower()
        
        # 創作系
        if any(keyword in title or keyword in description for keyword in 
              ["創作", "小説", "物語", "キャラクター", "ストーリー", "シナリオ", "creative", "story", "character"]):
            return "creative"
        
        # コーディング系
        if any(keyword in title or keyword in description for keyword in 
              ["コード", "プログラム", "実装", "code", "programming", "implementation"]):
            return "coding"
        
        # 分析系
        if any(keyword in title or keyword in description for keyword in 
              ["分析", "調査", "研究", "analysis", "research"]):
            return "analysis"
        
        # デフォルト
        return "generic"


class DefaultWorkerAI(WorkerAI):
    """デフォルトのWorkerAI実装"""
    
    async def execute_task(
        self, 
        task: SubTask, 
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> TaskExecutionResult:
        """
        タスクを実行
        
        Args:
            task: 実行するサブタスク
            context: 実行コンテキスト（オプション）
            **kwargs: 追加パラメータ
            
        Returns:
            タスク実行結果
        """
        return await super().execute_task(task, context, **kwargs) 