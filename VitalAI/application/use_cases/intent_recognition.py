"""Minimal intent recognition use case for backend-only interactions."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
import json
from pathlib import Path
from typing import Any, Protocol

from VitalAI.application.commands import UserInteractionCommand, UserInteractionEventType


class IntentRecognizerMode(str, Enum):
    """Configured first-layer intent recognizer mode."""

    RULE_BASED = "rule_based"
    BERT = "bert"
    HYBRID = "hybrid"


@dataclass(frozen=True, slots=True)
class IntentDatasetExample:
    """Stable training/evaluation example for future intent models."""

    text: str
    intent: UserInteractionEventType | None
    requires_decomposition: bool = False
    language: str = "zh"
    urgency: str = "normal"
    slots: dict[str, object] = field(default_factory=dict)
    source: str = "manual"
    split: str = "train"
    notes: str = ""

    def to_record(self) -> dict[str, object]:
        """Serialize the example as JSON-compatible training/evaluation data."""
        return {
            "text": self.text,
            "intent": self.expected_intent_label,
            "requires_decomposition": self.requires_decomposition,
            "language": self.language,
            "urgency": self.urgency,
            "slots": dict(self.slots),
            "source": self.source,
            "split": self.split,
            "notes": self.notes,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "IntentDatasetExample":
        """Parse one dataset record into the typed schema."""
        slots = record.get("slots", {})
        if not isinstance(slots, dict):
            slots = {}
        return cls(
            text=str(record["text"]),
            intent=_parse_dataset_intent(record.get("intent")),
            requires_decomposition=_parse_requires_decomposition(record),
            language=str(record.get("language", "zh")),
            urgency=str(record.get("urgency", "normal")),
            slots=slots,
            source=str(record.get("source", "manual")),
            split=str(record.get("split", "train")),
            notes=str(record.get("notes", "")),
        )

    @property
    def expected_intent_label(self) -> str:
        """Return the expected label used in evaluation output."""
        if self.requires_decomposition:
            return "needs_decomposition"
        return "unknown" if self.intent is None else self.intent.value


@dataclass(frozen=True, slots=True)
class UserIntentCandidate:
    """One possible intent recognized from a user interaction."""

    intent: UserInteractionEventType
    confidence: float
    reason: str
    context_updates: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class UserIntentResult:
    """Intent recognition result consumed by the central interaction dispatcher."""

    primary_intent: UserInteractionEventType | None
    candidates: list[UserIntentCandidate] = field(default_factory=list)
    confidence: float = 0.0
    source: str = "rule_based"
    requires_clarification: bool = False
    clarification_prompt: str | None = None
    requires_decomposition: bool = False
    decomposition_prompt: str | None = None
    context_updates: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BertIntentPrediction:
    """Raw prediction returned by a BERT intent backend."""

    label: str
    confidence: float


@dataclass(frozen=True, slots=True)
class IntentEvaluationCaseResult:
    """Offline evaluation result for one intent dataset example."""

    text: str
    expected_intent: str
    predicted_intent: str
    split: str
    dataset_source: str
    passed: bool
    confidence: float
    source: str
    requires_clarification: bool
    requires_decomposition: bool
    reason: str = ""


@dataclass(frozen=True, slots=True)
class IntentEvaluationIntentMetrics:
    """Aggregated offline evaluation metrics for one expected intent label."""

    expected_intent: str
    total: int
    passed: int
    failed: int
    accuracy: float


@dataclass(frozen=True, slots=True)
class IntentEvaluationSummary:
    """Offline evaluation summary for one recognizer against a dataset."""

    total: int
    passed: int
    failed: int
    accuracy: float
    by_intent: dict[str, IntentEvaluationIntentMetrics]
    by_source: dict[str, dict[str, int | float]]
    fallback: dict[str, int | float]
    clarification: dict[str, int | float]
    failures: list[IntentEvaluationCaseResult] = field(default_factory=list)

    def to_report(self) -> dict[str, object]:
        """Serialize the summary into a compact report payload."""
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "accuracy": self.accuracy,
            "by_intent": {
                intent: {
                    "total": metrics.total,
                    "passed": metrics.passed,
                    "failed": metrics.failed,
                    "accuracy": metrics.accuracy,
                }
                for intent, metrics in self.by_intent.items()
            },
            "by_source": self.by_source,
            "fallback": self.fallback,
            "clarification": self.clarification,
            "failures": [
                {
                    "text": failure.text,
                    "expected_intent": failure.expected_intent,
                    "predicted_intent": failure.predicted_intent,
                    "split": failure.split,
                    "dataset_source": failure.dataset_source,
                    "confidence": failure.confidence,
                    "source": failure.source,
                    "requires_clarification": failure.requires_clarification,
                    "requires_decomposition": failure.requires_decomposition,
                    "reason": failure.reason,
                }
                for failure in self.failures
            ],
        }


class IntentRecognizer(Protocol):
    """Pluggable intent recognizer contract.

    A future BertIntentRecognizer should implement this protocol without changing
    the interaction workflow or API route.
    """

    def recognize(self, command: UserInteractionCommand) -> UserIntentResult:
        """Recognize intent candidates from one user interaction."""


class BertIntentBackend(Protocol):
    """Backend contract for a local fine-tuned BERT intent model."""

    def predict(self, text: str) -> BertIntentPrediction:
        """Predict one intent label and confidence for text."""


BERT_INTENT_LABEL_ENV_HELP = (
    "health_alert,daily_life_checkin,mental_care_checkin,"
    "profile_memory_update,profile_memory_query,unknown"
)


@dataclass(slots=True)
class RuleBasedIntentRecognizer:
    """Deterministic first-layer recognizer used before a fine-tuned BERT adapter exists."""

    def recognize(self, command: UserInteractionCommand) -> UserIntentResult:
        """Recognize a primary interaction intent from message keywords."""
        text = _normalized_text(command.message)
        decomposition_result = _complex_decomposition_result(text)
        if decomposition_result is not None:
            return decomposition_result
        candidates = [
            candidate
            for candidate in (
                _health_candidate(text),
                _profile_memory_query_candidate(text),
                _profile_memory_update_candidate(command, text),
                _mental_care_candidate(text),
                _daily_life_candidate(command, text),
            )
            if candidate is not None
        ]
        if not candidates:
            return UserIntentResult(
                primary_intent=None,
                candidates=[],
                confidence=0.0,
                requires_clarification=True,
                clarification_prompt="我还不能确定你想让我处理健康、日常、心理陪护还是记忆问题，可以再说具体一点吗？",
            )

        candidates.sort(key=lambda item: item.confidence, reverse=True)
        primary = candidates[0]
        requires_clarification = primary.confidence < 0.55
        return UserIntentResult(
            primary_intent=primary.intent,
            candidates=candidates,
            confidence=primary.confidence,
            requires_clarification=requires_clarification,
            clarification_prompt=None
            if not requires_clarification
            else "我大概理解了，但还需要你确认一下这是哪类问题。",
            context_updates=dict(primary.context_updates),
        )


@dataclass(slots=True)
class RunUserIntentRecognitionUseCase:
    """Run the configured first-layer user intent recognizer."""

    recognizer: IntentRecognizer = field(default_factory=RuleBasedIntentRecognizer)

    def run(self, command: UserInteractionCommand) -> UserIntentResult:
        """Return the recognized intent result."""
        return self.recognizer.recognize(command)


@dataclass(slots=True)
class RunIntentRecognitionEvaluationUseCase:
    """Evaluate an intent recognizer against typed dataset examples."""

    recognizer: IntentRecognizer = field(default_factory=RuleBasedIntentRecognizer)

    def run(self, examples: list[IntentDatasetExample]) -> IntentEvaluationSummary:
        """Evaluate the recognizer and return aggregate metrics."""
        results = [self._evaluate_one(example) for example in examples]
        passed = sum(1 for result in results if result.passed)
        failed = len(results) - passed
        return IntentEvaluationSummary(
            total=len(results),
            passed=passed,
            failed=failed,
            accuracy=_safe_ratio(passed, len(results)),
            by_intent=_build_intent_metrics(results),
            by_source=_build_source_metrics(results),
            fallback=_build_source_family_metrics(results, pattern="fallback"),
            clarification=_build_clarification_metrics(results),
            failures=[result for result in results if not result.passed],
        )

    def _evaluate_one(self, example: IntentDatasetExample) -> IntentEvaluationCaseResult:
        command = UserInteractionCommand(
            user_id="intent-eval-user",
            channel="offline_eval",
            message=example.text,
        )
        result = self.recognizer.recognize(command)
        predicted_intent = "unknown" if result.primary_intent is None else result.primary_intent.value
        if example.requires_decomposition:
            predicted_intent = "needs_decomposition" if result.requires_decomposition else predicted_intent
            passed = result.requires_decomposition
        elif example.intent is None:
            passed = result.primary_intent is None and result.requires_clarification
        else:
            passed = (
                result.primary_intent == example.intent
                and not result.requires_clarification
                and not result.requires_decomposition
            )
        reason = "" if passed else _evaluation_failure_reason(example, result)
        return IntentEvaluationCaseResult(
            text=example.text,
            expected_intent=example.expected_intent_label,
            predicted_intent=predicted_intent,
            split=example.split,
            dataset_source=example.source,
            passed=passed,
            confidence=result.confidence,
            source=result.source,
            requires_clarification=result.requires_clarification,
            requires_decomposition=result.requires_decomposition,
            reason=reason,
        )


@dataclass(slots=True)
class BertIntentRecognizer:
    """BERT adapter with lazy local-model loading and deterministic fallback behavior.

    The adapter never downloads a model. It only attempts local inference when a
    model path is configured and exists.
    """

    model_path: str | None = None
    confidence_threshold: float = 0.65
    fallback: IntentRecognizer | None = field(default_factory=RuleBasedIntentRecognizer)
    backend: BertIntentBackend | None = None
    label_map: dict[str, str] | str | None = None

    def __post_init__(self) -> None:
        """Normalize optional BERT label mapping once for stable inference."""
        self.label_map = _coerce_bert_intent_label_map(self.label_map)

    def recognize(self, command: UserInteractionCommand) -> UserIntentResult:
        """Recognize intent with BERT when available, otherwise fallback safely."""
        text = _normalized_text(command.message)
        decomposition_result = _complex_decomposition_result(text)
        if decomposition_result is not None:
            return replace(decomposition_result, source="needs_decomposition_detector")
        hard_case_result = _bert_hard_case_guard_result(command, text)
        if hard_case_result is not None:
            return hard_case_result
        backend = self._resolve_backend()
        if backend is None:
            return self._fallback(command, source="bert_model_missing_fallback")

        try:
            prediction = backend.predict(command.message)
        except Exception:
            return self._fallback(command, source="bert_inference_error_fallback")

        intent = _label_to_intent(prediction.label, label_map=self.label_map)
        if prediction.confidence < self.confidence_threshold:
            return self._fallback(command, source="bert_low_confidence_fallback")
        if intent is None:
            return UserIntentResult(
                primary_intent=None,
                candidates=[],
                confidence=prediction.confidence,
                source="bert",
                requires_clarification=True,
                clarification_prompt="我还不能确定你想让我处理哪类问题，可以再说具体一点吗？",
            )

        candidate = UserIntentCandidate(
            intent=intent,
            confidence=prediction.confidence,
            reason=f"bert_label:{prediction.label}",
            context_updates=_default_context_updates_for_intent(intent, command),
        )
        return UserIntentResult(
            primary_intent=intent,
            candidates=[candidate],
            confidence=prediction.confidence,
            source="bert",
            context_updates=dict(candidate.context_updates),
        )

    def _resolve_backend(self) -> BertIntentBackend | None:
        """Return the configured BERT backend when local inference is possible."""
        if self.backend is not None:
            return self.backend
        if self.model_path is None or not str(self.model_path).strip():
            return None
        model_path = Path(self.model_path)
        if not model_path.exists():
            return None
        self.backend = TransformersBertIntentBackend(model_path=model_path)
        return self.backend

    def _fallback(self, command: UserInteractionCommand, source: str) -> UserIntentResult:
        """Run fallback recognizer or return a stable clarification result."""
        if self.fallback is None:
            return UserIntentResult(
                primary_intent=None,
                candidates=[],
                confidence=0.0,
                source="bert_unavailable",
                requires_clarification=True,
                clarification_prompt="当前意图识别模型不可用，请再说明你想处理哪类问题。",
            )
        return replace(self.fallback.recognize(command), source=source)


@dataclass(slots=True)
class TransformersBertIntentBackend:
    """Local transformers-based BERT backend loaded lazily from disk."""

    model_path: str | Path
    _tokenizer: Any | None = field(default=None, init=False, repr=False)
    _model: Any | None = field(default=None, init=False, repr=False)
    _torch: Any | None = field(default=None, init=False, repr=False)
    _id_to_label: dict[int, str] = field(default_factory=dict, init=False, repr=False)

    def predict(self, text: str) -> BertIntentPrediction:
        """Run one local BERT inference and return the predicted label."""
        self._load()
        inputs = self._tokenizer(text, return_tensors="pt", truncation=True)
        with self._torch.no_grad():
            outputs = self._model(**inputs)
            probabilities = self._torch.softmax(outputs.logits, dim=-1)[0]
            confidence_tensor, index_tensor = self._torch.max(probabilities, dim=0)
        label_index = int(index_tensor.item())
        return BertIntentPrediction(
            label=self._id_to_label.get(label_index, str(label_index)),
            confidence=float(confidence_tensor.item()),
        )

    def _load(self) -> None:
        """Load tokenizer/model from local path exactly once."""
        if self._tokenizer is not None and self._model is not None and self._torch is not None:
            return
        model_path = Path(self.model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"BERT intent model path does not exist: {model_path}")
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "BERT intent inference requires local torch and transformers dependencies."
            ) from exc

        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
        self._model = AutoModelForSequenceClassification.from_pretrained(
            str(model_path),
            local_files_only=True,
        )
        self._model.eval()
        config = getattr(self._model, "config", None)
        id_to_label = getattr(config, "id2label", None)
        if isinstance(id_to_label, dict):
            self._id_to_label = {int(key): str(value) for key, value in id_to_label.items()}


@dataclass(slots=True)
class HybridIntentRecognizer:
    """Hybrid recognizer boundary that prefers BERT and keeps rule-based fallback."""

    bert_recognizer: BertIntentRecognizer = field(default_factory=BertIntentRecognizer)

    def recognize(self, command: UserInteractionCommand) -> UserIntentResult:
        """Recognize intent through the configured BERT shell plus fallback."""
        return self.bert_recognizer.recognize(command)


def build_intent_recognizer(
    mode: str | IntentRecognizerMode | None = None,
    bert_model_path: str | None = None,
    bert_confidence_threshold: float = 0.65,
    bert_label_map: dict[str, str] | str | None = None,
) -> IntentRecognizer:
    """Build the configured intent recognizer without coupling workflow to implementation."""
    resolved_mode = _resolve_intent_recognizer_mode(mode)
    if resolved_mode is IntentRecognizerMode.RULE_BASED:
        return RuleBasedIntentRecognizer()
    if resolved_mode is IntentRecognizerMode.BERT:
        return BertIntentRecognizer(
            model_path=bert_model_path,
            confidence_threshold=bert_confidence_threshold,
            label_map=bert_label_map,
        )
    return HybridIntentRecognizer(
        bert_recognizer=BertIntentRecognizer(
            model_path=bert_model_path,
            confidence_threshold=bert_confidence_threshold,
            fallback=RuleBasedIntentRecognizer(),
            label_map=bert_label_map,
        )
    )


def build_intent_recognition_use_case(
    mode: str | IntentRecognizerMode | None = None,
    bert_model_path: str | None = None,
    bert_confidence_threshold: float = 0.65,
    bert_label_map: dict[str, str] | str | None = None,
) -> RunUserIntentRecognitionUseCase:
    """Build an intent recognition use case from environment-level configuration."""
    return RunUserIntentRecognitionUseCase(
        recognizer=build_intent_recognizer(
            mode=mode,
            bert_model_path=bert_model_path,
            bert_confidence_threshold=bert_confidence_threshold,
            bert_label_map=bert_label_map,
        )
    )


def parse_bert_intent_label_map(value: str | None) -> dict[str, str]:
    """Parse a comma-separated BERT label mapping from configuration.

    Supported forms:
    - ordered labels: ``health_alert,daily_life_checkin,...``
    - explicit pairs: ``LABEL_0=health_alert,LABEL_1=daily_life_checkin``
    """
    if value is None or not value.strip():
        return {}
    mapping: dict[str, str] = {}
    for index, raw_part in enumerate(value.split(",")):
        part = raw_part.strip()
        if not part:
            continue
        if "=" in part:
            raw_key, raw_label = part.split("=", 1)
            _add_bert_label_map_entry(mapping, raw_key, raw_label)
        else:
            _add_bert_label_map_entry(mapping, str(index), part)
    return mapping


def load_intent_dataset_examples_from_jsonl(path: str | Path) -> list[IntentDatasetExample]:
    """Load typed intent dataset examples from a JSONL file."""
    dataset_path = Path(path)
    examples: list[IntentDatasetExample] = []
    for line_number, line in enumerate(dataset_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at line {line_number}: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"Invalid intent dataset record at line {line_number}: expected object")
        examples.append(IntentDatasetExample.from_record(record))
    return examples


def filter_intent_dataset_examples_by_splits(
    examples: list[IntentDatasetExample],
    splits: set[str] | None,
) -> list[IntentDatasetExample]:
    """Return examples matching the selected split names."""
    if splits is None:
        return list(examples)
    normalized_splits = {split.strip().lower() for split in splits if split.strip()}
    return [example for example in examples if example.split.lower() in normalized_splits]


def explicit_event_type_intent_result(
    event_type: UserInteractionEventType,
) -> UserIntentResult:
    """Build an intent result when a request explicitly supplies event_type."""
    candidate = UserIntentCandidate(
        intent=event_type,
        confidence=1.0,
        reason="explicit_event_type",
    )
    return UserIntentResult(
        primary_intent=event_type,
        candidates=[candidate],
        confidence=1.0,
        source="explicit_event_type",
    )


def intent_result_payload(result: UserIntentResult) -> dict[str, object]:
    """Serialize an intent result for API diagnostics and manual verification."""
    return {
        "primary_intent": None if result.primary_intent is None else result.primary_intent.value,
        "confidence": result.confidence,
        "source": result.source,
        "requires_clarification": result.requires_clarification,
        "requires_decomposition": result.requires_decomposition,
        "clarification_prompt": result.clarification_prompt,
        "decomposition_prompt": result.decomposition_prompt,
        "candidates": [
            {
                "intent": candidate.intent.value,
                "confidence": candidate.confidence,
                "reason": candidate.reason,
            }
            for candidate in result.candidates
        ],
    }


def _resolve_intent_recognizer_mode(
    mode: str | IntentRecognizerMode | None,
) -> IntentRecognizerMode:
    """Return a supported recognizer mode, defaulting safely to rule-based."""
    if isinstance(mode, IntentRecognizerMode):
        return mode
    if mode is None or not str(mode).strip():
        return IntentRecognizerMode.RULE_BASED
    normalized = str(mode).strip().lower().replace("-", "_")
    for candidate in IntentRecognizerMode:
        if normalized == candidate.value:
            return candidate
    return IntentRecognizerMode.RULE_BASED


def _parse_dataset_intent(value: object) -> UserInteractionEventType | None:
    """Parse a dataset intent label, allowing unknown/clarification examples."""
    label = "" if value is None else str(value).strip().lower()
    if label in {"", "unknown", "clarification_needed", "none", "needs_decomposition", "complex_multi"}:
        return None
    return UserInteractionEventType(label)


def _parse_requires_decomposition(record: dict[str, Any]) -> bool:
    """Return whether one dataset record expects second-layer decomposition."""
    raw_value = record.get("requires_decomposition", False)
    if isinstance(raw_value, bool):
        return raw_value
    normalized_value = str(raw_value).strip().lower()
    if normalized_value in {"1", "true", "yes", "y"}:
        return True
    label = str(record.get("intent", "")).strip().lower()
    return label in {"needs_decomposition", "complex_multi"}


def _label_to_intent(
    label: object,
    *,
    label_map: dict[str, str] | str | None = None,
) -> UserInteractionEventType | None:
    """Normalize model labels into known interaction intent values."""
    normalized = _normalize_model_label(label)
    resolved_label_map = _coerce_bert_intent_label_map(label_map)
    mapped = resolved_label_map.get(normalized)
    if mapped is None and normalized.startswith("label_"):
        mapped = resolved_label_map.get(normalized.removeprefix("label_"))
    if mapped is not None:
        normalized = _normalize_model_label(mapped)
    if normalized in {"", "unknown", "clarification_needed", "none", "label_unknown"}:
        return None
    if normalized.startswith("label_"):
        normalized = normalized.removeprefix("label_")
    normalized = _BERT_INTENT_ALIASES.get(normalized, normalized)
    try:
        return UserInteractionEventType(normalized)
    except ValueError:
        return None


def _coerce_bert_intent_label_map(
    value: dict[str, str] | str | None,
) -> dict[str, str]:
    """Normalize label maps so model labels can be matched consistently."""
    if value is None:
        return {}
    if isinstance(value, str):
        return parse_bert_intent_label_map(value)
    mapping: dict[str, str] = {}
    for raw_key, raw_label in value.items():
        _add_bert_label_map_entry(mapping, raw_key, raw_label)
    return mapping


def _add_bert_label_map_entry(
    mapping: dict[str, str],
    raw_key: object,
    raw_label: object,
) -> None:
    """Add one normalized BERT label-map entry, including numeric aliases."""
    key = _normalize_model_label(raw_key)
    label = _normalize_model_label(raw_label)
    if not key or not label:
        return
    mapping[key] = label
    if key.startswith("label_"):
        mapping[key.removeprefix("label_")] = label
    elif key.isdigit():
        mapping[f"label_{key}"] = label


def _normalize_model_label(value: object) -> str:
    """Normalize raw model labels for comparison."""
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


_BERT_INTENT_ALIASES = {
    "health": UserInteractionEventType.HEALTH_ALERT.value,
    "medical": UserInteractionEventType.HEALTH_ALERT.value,
    "daily": UserInteractionEventType.DAILY_LIFE_CHECKIN.value,
    "daily_life": UserInteractionEventType.DAILY_LIFE_CHECKIN.value,
    "life": UserInteractionEventType.DAILY_LIFE_CHECKIN.value,
    "mental": UserInteractionEventType.MENTAL_CARE_CHECKIN.value,
    "mental_care": UserInteractionEventType.MENTAL_CARE_CHECKIN.value,
    "emotion": UserInteractionEventType.MENTAL_CARE_CHECKIN.value,
    "profile_update": UserInteractionEventType.PROFILE_MEMORY_UPDATE.value,
    "memory_update": UserInteractionEventType.PROFILE_MEMORY_UPDATE.value,
    "remember": UserInteractionEventType.PROFILE_MEMORY_UPDATE.value,
    "profile_query": UserInteractionEventType.PROFILE_MEMORY_QUERY.value,
    "memory_query": UserInteractionEventType.PROFILE_MEMORY_QUERY.value,
    "recall": UserInteractionEventType.PROFILE_MEMORY_QUERY.value,
}


_COMPLEX_GROUP_TO_INTENT = {
    "health": UserInteractionEventType.HEALTH_ALERT,
    "daily": UserInteractionEventType.DAILY_LIFE_CHECKIN,
    "mental": UserInteractionEventType.MENTAL_CARE_CHECKIN,
    "memory": UserInteractionEventType.PROFILE_MEMORY_QUERY,
    "medicine": UserInteractionEventType.HEALTH_ALERT,
    "family": UserInteractionEventType.MENTAL_CARE_CHECKIN,
}


_COMPLEX_GROUP_KEYWORDS: dict[str, tuple[str, ...]] = {
    "health": (
        "头晕",
        "头有点晕",
        "晕",
        "腰不舒服",
        "没力气",
        "胃口不好",
        "膝盖疼",
        "眼睛模糊",
        "胸口",
        "胸闷",
        "手脚发麻",
        "浑身不得劲",
        "哪里难受",
        "脑子不好使",
        "不太舒服",
        "不舒服",
        "疼",
        "痛",
        "dizzy",
        "pain",
        "blood",
        "nauseous",
    ),
    "daily": (
        "买菜",
        "擦桌子",
        "做饭",
        "带孙子",
        "粥",
        "下楼",
        "扔垃圾",
        "看手机",
        "看时间",
        "吃药",
        "收拾屋子",
        "坐久",
        "饭",
        "钥匙",
        "煤气",
        "医院",
        "shopping",
        "dinner",
        "medicine",
        "appointment",
    ),
    "mental": (
        "心里",
        "慌慌",
        "着急",
        "睡不着",
        "担心",
        "心烦",
        "害怕",
        "心情很差",
        "堵得慌",
        "不想跟家里人说",
        "lonely",
        "anxious",
    ),
    "memory": (
        "记不住",
        "忘事",
        "忘了",
        "记不得",
        "想不起来",
        "找不到",
        "记性",
        "刚想说的话",
    ),
    "medicine": (
        "那个药",
        "医生开的药",
        "药加",
        "药吃",
        "药要不要",
        "少吃点药",
        "药停了",
        "这个药",
        "medicine",
    ),
    "family": (
        "儿子",
        "女儿",
        "家里人",
        "朋友",
        "家里的事",
        "daughter",
    ),
}


_COMPOUND_LANGUAGE_MARKERS = (
    "不知道是不是",
    "不知道",
    "是不是",
    "要不要",
    "到底",
    "好像",
    "怎么",
    "一下子",
    "就记得",
    "可是",
    "又要",
    "又不",
    "但是",
    "但",
    "可",
    "又",
    "还是",
    "可是每天",
    "可能是",
    "也说不清楚",
    "说不上来",
    "一会儿",
    "又不想",
    "怕",
    "没人",
    "同时",
    "顺便",
    "but",
)


_VAGUE_DECOMPOSITION_MARKERS = (
    "说好不好说坏不坏",
    "该咋办",
    "说不清楚",
    "说不上来",
    "浑身不得劲",
    "一会儿这疼一会儿那疼",
    "也不是一直疼",
    "好像忘了一件",
    "怎么想都想不起来",
)


_MEDICATION_TERMS = (
    "\u836f",
    "\u5403\u836f",
    "\u836f\u4ee5\u540e",
    "\u521a\u5403\u5b8c\u836f",
    "medicine",
    "medication",
)

_ADVERSE_HEALTH_TERMS = (
    "\u6076\u5fc3",
    "\u60f3\u5410",
    "\u5934\u6655",
    "\u4e0d\u8212\u670d",
    "\u96be\u53d7",
    "nauseous",
    "nausea",
    "dizzy",
    "unwell",
)

_MEMORY_UPDATE_HARD_CASE_TERMS = (
    "\u4ee5\u540e\u63d0\u9192\u6211",
    "\u5e2e\u6211\u8bb0\u4f4f",
    "\u8bb0\u4f4f",
    "remind me",
    "remember that",
    "remember i",
    "i usually",
    "my routine",
    "my habit",
)

_MEMORY_QUERY_HARD_CASE_TERMS = (
    "\u6211\u4ee5\u524d\u8bf4\u8fc7\u4ec0\u4e48",
    "\u6211\u8bf4\u8fc7\u4ec0\u4e48",
    "\u8bb0\u5f97\u6211\u8bf4\u8fc7",
    "\u4f60\u8bb0\u5f97\u6211",
    "what did i say",
    "did i tell you",
    "what do you remember",
    "do you remember",
)


def _default_context_updates_for_intent(
    intent: UserInteractionEventType,
    command: UserInteractionCommand,
) -> dict[str, object]:
    """Provide minimal context updates for model-predicted intents."""
    if intent is UserInteractionEventType.HEALTH_ALERT:
        return {"risk_level": "high"}
    if intent is UserInteractionEventType.DAILY_LIFE_CHECKIN:
        return {"need": command.message, "urgency": "normal"}
    if intent is UserInteractionEventType.MENTAL_CARE_CHECKIN:
        return {"mood_signal": command.message, "support_need": "companionship"}
    if intent is UserInteractionEventType.PROFILE_MEMORY_UPDATE:
        return {"memory_key": "general_note", "memory_value": command.message}
    return {}


def _bert_hard_case_guard_result(
    command: UserInteractionCommand,
    text: str,
) -> UserIntentResult | None:
    """Catch known high-confidence BERT confusions with auditable rules."""
    candidate = _bert_hard_case_candidate(command, text)
    if candidate is None:
        return None
    return UserIntentResult(
        primary_intent=candidate.intent,
        candidates=[candidate],
        confidence=candidate.confidence,
        source="bert_hard_case_guard",
        context_updates=dict(candidate.context_updates),
    )


def _bert_hard_case_candidate(
    command: UserInteractionCommand,
    text: str,
) -> UserIntentCandidate | None:
    """Return a deterministic candidate for high-value BERT hard cases."""
    if _has_medication_adverse_signal(text):
        return UserIntentCandidate(
            intent=UserInteractionEventType.HEALTH_ALERT,
            confidence=0.9,
            reason="hard_case_guard:medication_adverse_signal",
            context_updates={"risk_level": "high"},
        )
    if _has_memory_query_signal(text):
        return UserIntentCandidate(
            intent=UserInteractionEventType.PROFILE_MEMORY_QUERY,
            confidence=0.88,
            reason="hard_case_guard:memory_query_signal",
        )
    if _has_memory_update_signal(text):
        return UserIntentCandidate(
            intent=UserInteractionEventType.PROFILE_MEMORY_UPDATE,
            confidence=0.87,
            reason="hard_case_guard:memory_update_signal",
            context_updates={
                "memory_key": "general_note",
                "memory_value": command.message,
            },
        )
    return None


def _has_medication_adverse_signal(text: str) -> bool:
    """Return whether medication plus discomfort should be health-first."""
    return (
        _match_any(text, _MEDICATION_TERMS) is not None
        and _match_any(text, _ADVERSE_HEALTH_TERMS) is not None
    )


def _has_memory_update_signal(text: str) -> bool:
    """Return whether the text asks VitalAI to remember a future habit/reminder."""
    return _match_any(text, _MEMORY_UPDATE_HARD_CASE_TERMS) is not None


def _has_memory_query_signal(text: str) -> bool:
    """Return whether the text asks what VitalAI remembers from prior input."""
    return _match_any(text, _MEMORY_QUERY_HARD_CASE_TERMS) is not None


def _build_intent_metrics(
    results: list[IntentEvaluationCaseResult],
) -> dict[str, IntentEvaluationIntentMetrics]:
    """Aggregate evaluation results by expected intent label."""
    labels = sorted({result.expected_intent for result in results})
    metrics: dict[str, IntentEvaluationIntentMetrics] = {}
    for label in labels:
        label_results = [result for result in results if result.expected_intent == label]
        passed = sum(1 for result in label_results if result.passed)
        failed = len(label_results) - passed
        metrics[label] = IntentEvaluationIntentMetrics(
            expected_intent=label,
            total=len(label_results),
            passed=passed,
            failed=failed,
            accuracy=_safe_ratio(passed, len(label_results)),
        )
    return metrics


def _build_source_metrics(
    results: list[IntentEvaluationCaseResult],
) -> dict[str, dict[str, int | float]]:
    """Aggregate evaluation results by recognizer source."""
    sources = sorted({result.source for result in results})
    return {
        source: _build_result_bucket_metrics(
            [result for result in results if result.source == source]
        )
        for source in sources
    }


def _build_source_family_metrics(
    results: list[IntentEvaluationCaseResult],
    *,
    pattern: str,
) -> dict[str, int | float]:
    """Aggregate results whose source contains a family marker."""
    normalized_pattern = pattern.strip().lower()
    matching = [
        result
        for result in results
        if normalized_pattern and normalized_pattern in result.source.lower()
    ]
    return _build_result_bucket_metrics(matching)


def _build_clarification_metrics(
    results: list[IntentEvaluationCaseResult],
) -> dict[str, int | float]:
    """Aggregate results that asked the user for clarification."""
    return _build_result_bucket_metrics(
        [result for result in results if result.requires_clarification]
    )


def _complex_decomposition_result(text: str) -> UserIntentResult | None:
    """Detect compound inputs that should go to a second-layer decomposer later."""
    matched_groups = _matched_intent_groups(text)
    if not _has_compound_language_signal(text) and not _has_vague_decomposition_signal(text):
        return None
    if len(matched_groups) < 2 and not _has_vague_decomposition_signal(text):
        return None
    candidates = [
        UserIntentCandidate(
            intent=_COMPLEX_GROUP_TO_INTENT[group],
            confidence=0.62,
            reason=f"compound_signal:{group}",
        )
        for group in sorted(matched_groups)
    ]
    if not candidates:
        candidates = [
            UserIntentCandidate(
                intent=UserInteractionEventType.HEALTH_ALERT,
                confidence=0.55,
                reason="compound_signal:vague_elder_expression",
            )
        ]
    return UserIntentResult(
        primary_intent=None,
        candidates=candidates,
        confidence=0.62,
        source="needs_decomposition_detector",
        requires_decomposition=True,
        decomposition_prompt=(
            "这句话里可能同时包含多个事情，需要进入第二层意图拆分后再执行。"
        ),
    )


def _matched_intent_groups(text: str) -> set[str]:
    """Return coarse semantic groups matched by one input."""
    groups: set[str] = set()
    for group, keywords in _COMPLEX_GROUP_KEYWORDS.items():
        if _match_any(text, keywords) is not None:
            groups.add(group)
    return groups


def _has_compound_language_signal(text: str) -> bool:
    """Return whether text looks like a compound or ambiguous multi-task input."""
    return _match_any(text, _COMPOUND_LANGUAGE_MARKERS) is not None


def _has_vague_decomposition_signal(text: str) -> bool:
    """Return whether text is vague enough to require second-layer interpretation."""
    return _match_any(text, _VAGUE_DECOMPOSITION_MARKERS) is not None


def _build_result_bucket_metrics(
    results: list[IntentEvaluationCaseResult],
) -> dict[str, int | float]:
    """Return shared totals for a result bucket."""
    passed = sum(1 for result in results if result.passed)
    failed = len(results) - passed
    return {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "accuracy": _safe_ratio(passed, len(results)),
    }


def _evaluation_failure_reason(
    example: IntentDatasetExample,
    result: UserIntentResult,
) -> str:
    """Return a concise explanation for one failed evaluation case."""
    if result.requires_decomposition:
        predicted = "needs_decomposition"
    else:
        predicted = "unknown" if result.primary_intent is None else result.primary_intent.value
    return (
        f"expected={example.expected_intent_label}; "
        f"predicted={predicted}; "
        f"clarification={result.requires_clarification}; "
        f"decomposition={result.requires_decomposition}"
    )


def _safe_ratio(numerator: int, denominator: int) -> float:
    """Return a stable ratio rounded for reports."""
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _health_candidate(text: str) -> UserIntentCandidate | None:
    matched = _match_any(
        text,
        (
            "摔倒",
            "跌倒",
            "头晕",
            "胸口疼",
            "胸痛",
            "呼吸困难",
            "不舒服",
            "晕倒",
            "发烧",
            "心慌",
            "血压",
            "血糖",
            "疼",
            "痛",
            "恶心",
            "走不稳",
            "站不稳",
            "fall",
            "fell",
            "dizzy",
            "chest pain",
            "breathless",
            "fever",
            "pain",
            "blood pressure",
            "blood sugar",
            "nauseous",
        ),
    )
    if matched is None:
        return None
    confidence = 0.92 if matched in {"摔倒", "跌倒", "晕倒", "fall", "fell", "chest pain"} else 0.88
    return UserIntentCandidate(
        intent=UserInteractionEventType.HEALTH_ALERT,
        confidence=confidence,
        reason=f"health_keyword:{matched}",
        context_updates={"risk_level": "critical" if confidence >= 0.9 else "high"},
    )


def _profile_memory_query_candidate(text: str) -> UserIntentCandidate | None:
    matched = _match_any(
        text,
        (
            "你还记得",
            "还记得我",
            "我以前说过",
            "我的偏好",
            "记得什么",
            "查一下我的",
            "我之前说过",
            "我平时喜欢",
            "以前记过",
            "what do you remember",
            "do you remember",
            "my preference",
            "did i tell you",
            "what did i say",
            "my usual",
        ),
    )
    if matched is None:
        return None
    return UserIntentCandidate(
        intent=UserInteractionEventType.PROFILE_MEMORY_QUERY,
        confidence=0.86,
        reason=f"profile_memory_query_keyword:{matched}",
    )


def _profile_memory_update_candidate(
    command: UserInteractionCommand,
    text: str,
) -> UserIntentCandidate | None:
    matched = _match_any(
        text,
        (
            "帮我记住",
            "记住",
            "我喜欢",
            "我不喜欢",
            "我常去",
            "我的习惯",
            "我习惯",
            "我每天",
            "我常吃",
            "我常喝",
            "我的生日",
            "我的过敏",
            "以后提醒我",
            "remember",
            "i like",
            "i dislike",
            "my habit",
            "my routine",
            "i usually",
            "remind me",
        ),
    )
    if matched is None:
        return None
    return UserIntentCandidate(
        intent=UserInteractionEventType.PROFILE_MEMORY_UPDATE,
        confidence=0.84,
        reason=f"profile_memory_update_keyword:{matched}",
        context_updates={
            "memory_key": "general_note",
            "memory_value": command.message,
        },
    )


def _mental_care_candidate(text: str) -> UserIntentCandidate | None:
    matched = _match_any(
        text,
        (
            "孤单",
            "孤独",
            "难过",
            "伤心",
            "睡不着",
            "焦虑",
            "没人说话",
            "害怕",
            "心烦",
            "想聊天",
            "陪我",
            "没意思",
            "失落",
            "lonely",
            "sad",
            "anxious",
            "cannot sleep",
            "can't sleep",
            "scared",
            "upset",
            "talk to me",
            "keep me company",
        ),
    )
    if matched is None:
        return None
    return UserIntentCandidate(
        intent=UserInteractionEventType.MENTAL_CARE_CHECKIN,
        confidence=0.82,
        reason=f"mental_care_keyword:{matched}",
        context_updates={"mood_signal": matched, "support_need": "companionship"},
    )


def _daily_life_candidate(
    command: UserInteractionCommand,
    text: str,
) -> UserIntentCandidate | None:
    matched = _match_any(
        text,
        (
            "买菜",
            "吃饭",
            "晚饭",
            "做饭",
            "出门",
            "缴费",
            "账单",
            "购物",
            "买药",
            "早餐",
            "午饭",
            "药",
            "水电费",
            "快递",
            "打车",
            "叫车",
            "预约",
            "家里",
            "电饭锅",
            "grocery",
            "meal",
            "bill",
            "shopping",
            "go out",
            "breakfast",
            "lunch",
            "dinner",
            "medicine",
            "delivery",
            "taxi",
            "appointment",
        ),
    )
    if matched is None:
        return None
    urgency = "high" if _match_any(text, ("马上", "紧急", "现在", "urgent", "right now")) else "normal"
    return UserIntentCandidate(
        intent=UserInteractionEventType.DAILY_LIFE_CHECKIN,
        confidence=0.78,
        reason=f"daily_life_keyword:{matched}",
        context_updates={"need": command.message, "urgency": urgency},
    )


def _normalized_text(text: str) -> str:
    """Normalize text for deterministic keyword matching."""
    return text.strip().lower()


def _match_any(text: str, keywords: tuple[str, ...]) -> str | None:
    """Return the first keyword contained in text."""
    for keyword in keywords:
        if keyword in text:
            return keyword
    return None
