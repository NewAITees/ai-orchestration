from typing import List, Dict, Any
from ..core.message import OrchestrationMessage
from ..types import Component
from .base import BaseAIComponent

class EvaluatorAI(BaseAIComponent):
    """EvaluatorAI"""
    component_type = Component.EVALUATOR
    
    def _process_command(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """コマンド処理"""
        content = message.content
        action = content.get("action")
        
        try:
            if action == "evaluate_task":
                task_id = content.get("task_id")
                if not task_id:
                    return [self._create_error_response(
                        message.sender,
                        "task_id が指定されていません"
                    )]
                
                # タスク評価
                task = self.session.get_subtask(task_id)
                if not task:
                    return [self._create_error_response(
                        message.sender,
                        f"タスクが見つかりません: {task_id}"
                    )]
                
                evaluation = self.evaluate_task(task)
                
                return [self._create_response(
                    message.sender,
                    {"result": evaluation},
                    "task_evaluated"
                )]
            elif action == "suggest_improvements":
                evaluation = content.get("evaluation")
                if not evaluation:
                    return [self._create_error_response(
                        message.sender,
                        "evaluation が指定されていません"
                    )]
                
                improvements = self.suggest_improvements(evaluation)
                
                return [self._create_response(
                    message.sender,
                    {"improvements": improvements},
                    "improvements_suggested"
                )]
            else:
                return [self._create_error_response(
                    message.sender,
                    f"未対応のアクション: {action}"
                )]
        except Exception as e:
            return [self._create_error_response(
                message.sender,
                f"コマンド処理中にエラーが発生しました: {str(e)}"
            )]
    
    def evaluate_task(self, task) -> Dict[str, Any]:
        """タスク評価"""
        # LLMを使用した評価
        if self.llm_manager and task.result:
            prompt = f"""
            以下のタスク結果を評価してください:
            タイトル: {task.title}
            説明: {task.description}
            要件: {', '.join(task.requirements) if task.requirements else 'なし'}
            結果: {task.result}
            
            以下の観点で評価してください:
            1. 要件を満たしているか
            2. 質の高い結果になっているか
            3. 改善点はあるか
            """
            # 実際のLLM呼び出しはここで行う
        
        # サンプルの評価結果（実際はLLMの出力を解析）
        return {
            "score": 0.8,
            "feedback": "良好な結果ですが、改善の余地があります。",
            "metrics": {
                "quality": 0.8,
                "completeness": 0.9,
                "relevance": 0.7
            }
        }
    
    def suggest_improvements(self, evaluation) -> List[Dict[str, Any]]:
        """改善提案"""
        # 評価結果に基づく改善提案
        return [
            {"description": "より具体的な例を追加する", "priority": "high"},
            {"description": "構成をより明確にする", "priority": "medium"}
        ] 