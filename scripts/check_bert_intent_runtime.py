"""Check local BERT intent runtime readiness without downloading models."""

from __future__ import annotations

import argparse
import importlib.util
from importlib import metadata
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from VitalAI.application import (  # noqa: E402
    BertIntentRecognizer,
    UserInteractionCommand,
    parse_bert_intent_label_map,
)


def main() -> int:
    """Validate dependencies, model path, label mapping, and one optional prediction."""
    parser = argparse.ArgumentParser(description="Check VitalAI BERT intent runtime readiness")
    parser.add_argument("--model-path", default=None, help="Local fine-tuned BERT model directory.")
    parser.add_argument(
        "--bert-labels",
        default=None,
        help="Ordered labels or explicit pairs, e.g. LABEL_0=health_alert,LABEL_1=unknown.",
    )
    parser.add_argument(
        "--sample-text",
        default="I fell and feel dizzy",
        help="Sample text used for a local prediction smoke test.",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.65,
        help="BERT confidence threshold used by the recognizer.",
    )
    args = parser.parse_args()

    model_path = Path(args.model_path).expanduser() if args.model_path else None
    torch_available = importlib.util.find_spec("torch") is not None
    transformers_available = importlib.util.find_spec("transformers") is not None
    model_path_exists = bool(model_path and model_path.exists())
    model_files = list(model_path.rglob("*")) if model_path_exists and model_path is not None else []
    model_file_count = sum(1 for item in model_files if item.is_file())
    has_config_json = bool(model_path and (model_path / "config.json").exists())
    model_config = _load_model_config(model_path / "config.json") if has_config_json and model_path else {}
    label_map = parse_bert_intent_label_map(args.bert_labels)

    report: dict[str, object] = {
        "python_executable": sys.executable,
        "torch_available": torch_available,
        "torch_version": _package_version("torch"),
        "transformers_available": transformers_available,
        "transformers_version": _package_version("transformers"),
        "numpy_version": _package_version("numpy"),
        "model_path": None if model_path is None else str(model_path),
        "model_path_exists": model_path_exists,
        "model_file_count": model_file_count,
        "has_config_json": has_config_json,
        "model_architectures": model_config.get("architectures", []),
        "model_num_labels": _configured_label_count(model_config),
        "model_id2label": model_config.get("id2label", {}),
        "label_map": label_map,
        "label_map_target_count": len(set(label_map.values())),
        "prediction": None,
        "ready": False,
        "issues": [],
    }

    issues = report["issues"]
    if not torch_available:
        issues.append("torch is not available in this Python environment")
    if not transformers_available:
        issues.append("transformers is not available in this Python environment")
    if not model_path_exists:
        issues.append("model path is missing or does not exist")
    elif model_file_count == 0:
        issues.append("model path exists but contains no files")
    elif not has_config_json:
        issues.append("model path exists but config.json is missing")
    else:
        _append_model_config_issues(issues, model_config=model_config, label_map=label_map)
    if _transformers_requires_torch_24(
        transformers_version=_package_version("transformers"),
        torch_version=_package_version("torch"),
    ):
        issues.append("torch version is lower than the installed transformers runtime expects")

    if not issues:
        result = BertIntentRecognizer(
            model_path=str(model_path),
            confidence_threshold=args.confidence_threshold,
            fallback=None,
            label_map=args.bert_labels,
        ).recognize(
            UserInteractionCommand(
                user_id="bert-runtime-check",
                channel="offline_check",
                message=args.sample_text,
            )
        )
        report["prediction"] = {
            "primary_intent": None if result.primary_intent is None else result.primary_intent.value,
            "confidence": result.confidence,
            "source": result.source,
            "requires_clarification": result.requires_clarification,
        }
        report["ready"] = result.source == "bert"
        if result.source != "bert":
            issues.append(f"bert recognizer did not return a direct model prediction: source={result.source}")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 1


def _package_version(package_name: str) -> str | None:
    """Return installed package version without importing heavy ML modules."""
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None


def _load_model_config(config_path: Path) -> dict[str, object]:
    """Read Hugging Face config.json without importing transformers."""
    try:
        content = config_path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _configured_label_count(model_config: dict[str, object]) -> int:
    """Return the number of labels declared by the model config."""
    id_to_label = model_config.get("id2label")
    if isinstance(id_to_label, dict) and id_to_label:
        return len(id_to_label)
    num_labels = model_config.get("num_labels")
    if isinstance(num_labels, int):
        return num_labels
    return 0


def _append_model_config_issues(
    issues: list[str],
    *,
    model_config: dict[str, object],
    label_map: dict[str, str],
) -> None:
    """Add actionable model-configuration issues to the readiness report."""
    architectures = model_config.get("architectures", [])
    if isinstance(architectures, list) and architectures:
        has_classifier = any("sequenceclassification" in str(item).lower() for item in architectures)
        if not has_classifier:
            issues.append("model config architecture is not a sequence classification model")

    configured_label_count = _configured_label_count(model_config)
    expected_label_count = len(set(label_map.values()))
    if expected_label_count and configured_label_count == 0:
        issues.append("model config does not declare classification labels")
    elif expected_label_count and configured_label_count != expected_label_count:
        issues.append(
            f"model label count {configured_label_count} does not match label map target count {expected_label_count}"
        )


def _version_less_than(version: str | None, minimum: str) -> bool:
    """Compare simple dotted versions without adding a runtime dependency."""
    if version is None:
        return False

    def parts(value: str) -> tuple[int, ...]:
        numbers: list[int] = []
        for chunk in value.split("."):
            digit = ""
            for char in chunk:
                if not char.isdigit():
                    break
                digit += char
            if digit:
                numbers.append(int(digit))
        return tuple(numbers)

    return parts(version) < parts(minimum)


def _transformers_requires_torch_24(
    *,
    transformers_version: str | None,
    torch_version: str | None,
) -> bool:
    """Flag the known Transformers 5.x / older PyTorch incompatibility."""
    if transformers_version is None or torch_version is None:
        return False
    major = _major_version(transformers_version)
    return major >= 5 and _version_less_than(torch_version, "2.4")


def _major_version(version: str) -> int:
    """Return the leading integer version component."""
    digit = ""
    for char in version:
        if not char.isdigit():
            break
        digit += char
    return int(digit or "0")


if __name__ == "__main__":
    raise SystemExit(main())
