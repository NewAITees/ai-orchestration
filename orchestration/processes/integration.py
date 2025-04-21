from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import difflib
from collections import defaultdict

class IntegrationResult(BaseModel):
    """統合結果を表すモデル"""
    content: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

class ContentSimilarity(BaseModel):
    """コンテンツの類似性を表すモデル"""
    source_id: str
    target_id: str
    similarity_score: float
    overlapping_content: List[str]

class ResultIntegrator:
    """タスク実行結果を統合するクラス"""
    
    def __init__(self, execution_results: Dict[str, Any]):
        self.execution_results = execution_results
        self.similarity_threshold = 0.8  # 類似性の閾値
        self.integrated_result: Optional[IntegrationResult] = None
        
    def _calculate_similarity(self, content1: str, content2: str) -> float:
        """2つのコンテンツ間の類似性を計算する"""
        return difflib.SequenceMatcher(None, content1, content2).ratio()
    
    def _find_similar_content(self) -> List[ContentSimilarity]:
        """類似したコンテンツを検出する"""
        similarities = []
        results = list(self.execution_results.items())
        
        for i, (id1, result1) in enumerate(results):
            for id2, result2 in results[i+1:]:
                if isinstance(result1, str) and isinstance(result2, str):
                    score = self._calculate_similarity(result1, result2)
                    if score >= self.similarity_threshold:
                        similarities.append(ContentSimilarity(
                            source_id=id1,
                            target_id=id2,
                            similarity_score=score,
                            overlapping_content=self._find_overlapping_content(result1, result2)
                        ))
        
        return similarities
    
    def _find_overlapping_content(self, content1: str, content2: str) -> List[str]:
        """重複するコンテンツを検出する"""
        # TODO: より洗練された重複検出アルゴリズムを実装
        return []
    
    def _check_consistency(self, integrated_content: Any) -> List[str]:
        """統合されたコンテンツの整合性をチェックする"""
        warnings = []
        # TODO: 整合性チェックロジックを実装
        return warnings
    
    def _format_output(self, content: Any) -> Any:
        """出力を適切な形式に整形する"""
        # TODO: フォーマット整形ロジックを実装
        return content
    
    def integrate(self) -> IntegrationResult:
        """実行結果を統合する"""
        # 類似コンテンツの検出
        similarities = self._find_similar_content()
        
        # 重複の排除と統合
        integrated_content = self._merge_results(similarities)
        
        # 整合性チェック
        warnings = self._check_consistency(integrated_content)
        
        # 出力の整形
        formatted_content = self._format_output(integrated_content)
        
        # 統合結果の作成
        self.integrated_result = IntegrationResult(
            content=formatted_content,
            metadata={
                "similarities_detected": len(similarities),
                "warnings_count": len(warnings)
            },
            warnings=warnings
        )
        
        return self.integrated_result
    
    def _merge_results(self, similarities: List[ContentSimilarity]) -> Any:
        """実行結果を統合する"""
        # TODO: より洗練された統合ロジックを実装
        # 現状は単純に全ての結果を結合
        if isinstance(next(iter(self.execution_results.values())), str):
            return "\n".join(str(r) for r in self.execution_results.values())
        else:
            # その他の型の場合は、適切な統合方法を実装
            return list(self.execution_results.values()) 