"""Run offline evaluation for VitalAI intent recognizers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from VitalAI.application import (  # noqa: E402
    RunIntentRecognitionEvaluationUseCase,
    build_intent_recognizer,
    filter_intent_dataset_examples_by_splits,
    load_intent_dataset_examples_from_jsonl,
    parse_bert_intent_label_map,
)


BASELINE_SPLITS = {"train", "dev", "test"}


def main() -> int:
    """Evaluate one configured intent recognizer against a JSONL dataset."""
    parser = argparse.ArgumentParser(description="Evaluate VitalAI intent recognition dataset")
    parser.add_argument(
        "--dataset",
        default="docs/intent_dataset_examples.jsonl",
        help="Path to an intent dataset JSONL file.",
    )
    parser.add_argument(
        "--recognizer",
        default="rule_based",
        choices=("rule_based", "bert", "hybrid"),
        help="Intent recognizer mode to evaluate.",
    )
    parser.add_argument(
        "--bert-model-path",
        default=None,
        help="Optional BERT model path. Current adapter shell falls back when unavailable.",
    )
    parser.add_argument(
        "--bert-labels",
        default=None,
        help=(
            "Optional BERT labels, either ordered labels or explicit pairs, "
            "for example: LABEL_0=health_alert,LABEL_1=daily_life_checkin"
        ),
    )
    parser.add_argument(
        "--splits",
        default="all",
        help=(
            "Comma-separated splits to evaluate. Special values: all, baseline "
            "(train/dev/test), holdout."
        ),
    )
    parser.add_argument(
        "--group-by-split",
        action="store_true",
        help="Include a per-split evaluation report in addition to the selected summary.",
    )
    args = parser.parse_args()

    all_examples = load_intent_dataset_examples_from_jsonl(args.dataset)
    selected_splits = _parse_splits(args.splits)
    examples = filter_intent_dataset_examples_by_splits(all_examples, selected_splits)
    recognizer = build_intent_recognizer(
        mode=args.recognizer,
        bert_model_path=args.bert_model_path,
        bert_label_map=parse_bert_intent_label_map(args.bert_labels),
    )
    evaluator = RunIntentRecognitionEvaluationUseCase(recognizer=recognizer)
    summary = evaluator.run(examples)

    report = summary.to_report()
    if args.group_by_split:
        report = {
            "selected_splits": "all" if selected_splits is None else sorted(selected_splits),
            "summary": report,
            "by_split": _build_split_reports(evaluator, examples),
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if summary.failed == 0 else 1


def _parse_splits(value: str) -> set[str] | None:
    """Parse split filter shortcuts used by the CLI."""
    normalized = {part.strip().lower() for part in value.split(",") if part.strip()}
    if not normalized or "all" in normalized:
        return None
    if "baseline" in normalized:
        normalized.remove("baseline")
        normalized.update(BASELINE_SPLITS)
    return normalized


def _build_split_reports(
    evaluator: RunIntentRecognitionEvaluationUseCase,
    examples: list[object],
) -> dict[str, object]:
    """Build one evaluation report per split."""
    split_names = sorted({getattr(example, "split") for example in examples})
    return {
        split: evaluator.run(
            [example for example in examples if getattr(example, "split") == split]
        ).to_report()
        for split in split_names
    }


if __name__ == "__main__":
    raise SystemExit(main())
