from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Protocol
from pydantic import BaseModel, Field
from ..core.message import OrchestrationMessage, MessageType, Component
from ..core.session import Session, SubTask
from .llm_manager import LLMManager

class TaskAnalysisResult(BaseModel):
    """タスク分析結果のモデル"""
    
    main_task: str = Field(..., description="分析対象のメインタスク")
    task_type: str = Field(..., description="タスクのタイプ")
    complexity: int = Field(ge=1, le=10, description="タスクの複雑さ (1-10)")
    estimated_steps: int = Field(..., description="推定されるステップ数")
    subtasks: List[Dict[str, Any]] = Field(..., description="サブタスクのリスト")
    requirements: List[str] = Field(default_factory=list, description="タスクの要件")
    constraints: List[str] = Field(default_factory=list, description="タスクの制約")

class IPlannerAI(Protocol):
    """Planner AIのインターフェース"""
    
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass
    
    @abstractmethod
    def analyze_task(self, task: str) -> TaskAnalysisResult:
        """タスクを分析し、構造化された結果を返す"""
        pass

class BasePlannerAI(ABC):
    """Planner AIの抽象基底クラス"""
    
    def __init__(self, session: Session, llm_manager: LLMManager):
        """
        初期化
        
        Args:
            session: 関連付けられたセッション
            llm_manager: LLMマネージャー
        """
        self.session = session
        self.llm_manager = llm_manager
    
    @abstractmethod
    def process_message(self, message: OrchestrationMessage) -> List[OrchestrationMessage]:
        """メッセージを処理し、応答メッセージのリストを返す"""
        pass
    
    @abstractmethod
    def analyze_task(self, task: str) -> TaskAnalysisResult:
        """タスクを分析し、構造化された結果を返す"""
        pass
    
    def _create_message(
        self,
        receiver: Component,
        message_type: MessageType,
        content: Dict[str, Any]
    ) -> OrchestrationMessage:
        """
        メッセージを作成する
        
        Args:
            receiver: メッセージの受信者
            message_type: メッセージのタイプ
            content: メッセージの内容
            
        Returns:
            作成されたメッセージ
        """
        return OrchestrationMessage(
            type=message_type,
            sender=Component.PLANNER,
            receiver=receiver,
            content=content,
            session_id=self.session.id
        )
    
    def _create_error_message(
        self,
        receiver: Component,
        error_message: str
    ) -> OrchestrationMessage:
        """
        エラーメッセージを作成する
        
        Args:
            receiver: メッセージの受信者
            error_message: エラーメッセージ
            
        Returns:
            作成されたエラーメッセージ
        """
        return self._create_message(
            receiver,
            MessageType.ERROR,
            {"error": error_message}
        )

class DefaultPlannerAI(BasePlannerAI):
    """デフォルトのPlanner AI実装"""
    
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
            if action == "analyze_task":
                return self._handle_analyze_task(content.get("task", ""))
            else:
                return [self._create_error_message(
                    message.sender,
                    f"サポートされていないアクション: {action}"
                )]
        except Exception as e:
            return [self._create_error_message(
                message.sender,
                f"メッセージ処理中にエラーが発生しました: {str(e)}"
            )]
    
    def _handle_analyze_task(self, task: str) -> List[OrchestrationMessage]:
        """
        タスクを分析し、サブタスクに分解
        
        Args:
            task: 分析対象のタスク
            
        Returns:
            応答メッセージのリスト
        """
        try:
            # タスクの前処理と検証
            if not task or len(task.strip()) == 0:
                return [self._create_error_message(
                    Component.DIRECTOR,
                    "タスクが空です"
                )]
            
            # タスク分析の実行
            analysis_result = self.analyze_task(task)
            
            # 分析結果をJSONに変換
            result_json = analysis_result.dict()
            
            # レスポンスメッセージを作成
            return [self._create_message(
                Component.DIRECTOR,
                MessageType.RESPONSE,
                {
                    "action": "task_analyzed",
                    "result": result_json
                }
            )]
        
        except Exception as e:
            return [self._create_error_message(
                Component.DIRECTOR,
                f"タスク分析中にエラーが発生しました: {str(e)}"
            )]
    
    def analyze_task(self, task: str) -> TaskAnalysisResult:
        """
        タスクを分析し、構造化された結果を返す
        
        Args:
            task: 分析対象のタスク
            
        Returns:
            分析結果
        """
        try:
            # LLMを使用してタスクを分析
            prompt = f"""
            以下のタスクを分析し、必要な情報を抽出してください：
            
            タスク: {task}
            
            1. タスクの種類を判定
            2. 複雑さを1-10で評価
            3. 必要なステップ数を推定
            4. サブタスクを特定
            5. 要件と制約を抽出
            """
            
            response = self.llm_manager.get_completion(prompt)
            
            # 現在はダミーの実装を提供
            # 実際の実装では、LLMの応答を解析して適切な値を設定
            return TaskAnalysisResult(
                main_task=task,
                task_type="creative_writing",
                complexity=5,
                estimated_steps=3,
                subtasks=[
                    {
                        "title": "キャラクター設定",
                        "description": "物語の主要キャラクターの設定を作成",
                        "dependencies": []
                    },
                    {
                        "title": "プロット作成",
                        "description": "物語の基本的なプロットを構築",
                        "dependencies": ["キャラクター設定"]
                    },
                    {
                        "title": "本文執筆",
                        "description": "実際の物語を執筆",
                        "dependencies": ["プロット作成"]
                    }
                ],
                requirements=["魅力的なキャラクター", "一貫したストーリー"],
                constraints=["適切な長さ", "ターゲット読者層に適した内容"]
            )
        except Exception as e:
            raise Exception(f"タスク分析中にエラーが発生しました: {str(e)}") 