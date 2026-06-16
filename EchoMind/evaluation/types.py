"""评测数据结构（无 LLM 依赖）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class IntentTestCase:
    message: str
    expected_intent: str
    context: Optional[Dict[str, Any]] = None
    history: Optional[List[Dict[str, str]]] = None


@dataclass
class EvalResult:
    test_id: str
    passed: bool
    scores: Dict[str, float]
    detail: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalReport:
    """评测报告。"""
    timestamp: str
    total: int
    passed: int
    pass_rate: float
    avg_scores: Dict[str, float]
    regressions: List[str]
    recommendations: List[str]
    results: List[EvalResult]
    intent_metrics: Optional[Dict[str, Any]] = None
    dataset_stats: Optional[Dict[str, Any]] = None
