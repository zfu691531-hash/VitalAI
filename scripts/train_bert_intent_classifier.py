"""Fine-tune a local BERT model for VitalAI intent classification."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import random
import sys
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import torch  # noqa: E402
from torch.utils.data import DataLoader, Dataset  # noqa: E402
from transformers import (  # noqa: E402
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)


DEFAULT_LABELS = [
    "health_alert",
    "daily_life_checkin",
    "mental_care_checkin",
    "profile_memory_update",
    "profile_memory_query",
    "unknown",
]


@dataclass(frozen=True, slots=True)
class IntentTrainingExample:
    """One supervised intent training example."""

    text: str
    label: str
    split: str


class IntentDataset(Dataset[dict[str, torch.Tensor]]):
    """Torch dataset that tokenizes intent examples lazily."""

    def __init__(
        self,
        examples: list[IntentTrainingExample],
        *,
        tokenizer: object,
        label_to_id: dict[str, int],
        max_length: int,
    ) -> None:
        self._examples = examples
        self._tokenizer = tokenizer
        self._label_to_id = label_to_id
        self._max_length = max_length

    def __len__(self) -> int:
        return len(self._examples)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        example = self._examples[index]
        encoded = self._tokenizer(
            example.text,
            truncation=True,
            padding="max_length",
            max_length=self._max_length,
            return_tensors="pt",
        )
        item = {key: value.squeeze(0) for key, value in encoded.items()}
        item["labels"] = torch.tensor(self._label_to_id[example.label], dtype=torch.long)
        return item


def main() -> int:
    """Train and export a local BERT sequence classifier."""
    parser = argparse.ArgumentParser(description="Train VitalAI BERT intent classifier")
    parser.add_argument("--dataset", default="docs/intent_dataset_examples.jsonl")
    parser.add_argument("--base-model-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--labels", default=",".join(DEFAULT_LABELS))
    parser.add_argument("--train-splits", default="train,dev,test")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=96)
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--freeze-base", action="store_true")
    parser.add_argument(
        "--precompute-frozen-base",
        action="store_true",
        help="When the base is frozen, precompute BERT embeddings and train only the classifier head.",
    )
    args = parser.parse_args()

    labels = [label.strip() for label in args.labels.split(",") if label.strip()]
    label_to_id = {label: index for index, label in enumerate(labels)}
    id_to_label = {index: label for label, index in label_to_id.items()}
    train_splits = {split.strip() for split in args.train_splits.split(",") if split.strip()}

    _seed_everything(args.seed)
    examples = _load_examples(Path(args.dataset), labels=labels, splits=train_splits)
    if not examples:
        raise ValueError("No training examples matched the requested labels and splits.")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model_path, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model_path,
        num_labels=len(labels),
        id2label=id_to_label,
        label2id=label_to_id,
        ignore_mismatched_sizes=True,
        local_files_only=True,
    )
    model.config.architectures = ["BertForSequenceClassification"]
    model.config.num_labels = len(labels)
    model.config.id2label = id_to_label
    model.config.label2id = label_to_id

    if args.freeze_base:
        for name, parameter in model.named_parameters():
            if not name.startswith("classifier."):
                parameter.requires_grad = False

    model.to(device)
    dataset = IntentDataset(
        examples,
        tokenizer=tokenizer,
        label_to_id=label_to_id,
        max_length=args.max_length,
    )
    generator = torch.Generator()
    generator.manual_seed(args.seed)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, generator=generator)

    if args.freeze_base and args.precompute_frozen_base:
        _train_classifier_from_precomputed_embeddings(
            model=model,
            loader=loader,
            epochs=args.epochs,
            learning_rate=args.learning_rate,
            device=device,
            examples=len(examples),
        )
    else:
        optimizer = torch.optim.AdamW(
            [parameter for parameter in model.parameters() if parameter.requires_grad],
            lr=args.learning_rate,
        )
        total_steps = max(1, len(loader) * args.epochs)
        warmup_steps = int(total_steps * args.warmup_ratio)
        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=warmup_steps,
            num_training_steps=total_steps,
        )

        for epoch in range(1, args.epochs + 1):
            loss = _train_one_epoch(model, loader, optimizer, scheduler, device)
            accuracy = _evaluate_accuracy(model, loader, device)
            print(
                json.dumps(
                    {
                        "epoch": epoch,
                        "loss": round(loss, 6),
                        "train_accuracy": round(accuracy, 4),
                        "examples": len(examples),
                        "device": str(device),
                        "mode": "standard",
                    },
                    ensure_ascii=False,
                )
            )

    output_path = Path(args.output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(output_path), safe_serialization=True)
    tokenizer.save_pretrained(str(output_path))
    print(
        json.dumps(
            {
                "output_path": str(output_path),
                "labels": labels,
                "saved": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


def _load_examples(
    dataset_path: Path,
    *,
    labels: Iterable[str],
    splits: set[str],
) -> list[IntentTrainingExample]:
    """Load JSONL examples used for supervised training."""
    allowed_labels = set(labels)
    examples: list[IntentTrainingExample] = []
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        label = str(record.get("intent", "unknown"))
        split = str(record.get("split", "train"))
        if label not in allowed_labels or split not in splits:
            continue
        examples.append(
            IntentTrainingExample(
                text=str(record["text"]),
                label=label,
                split=split,
            )
        )
    return examples


def _train_one_epoch(
    model: torch.nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scheduler: object,
    device: torch.device,
) -> float:
    """Run one training epoch and return average loss."""
    model.train()
    total_loss = 0.0
    for batch in loader:
        batch = {key: value.to(device) for key, value in batch.items()}
        optimizer.zero_grad(set_to_none=True)
        outputs = model(**batch)
        loss = outputs.loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        scheduler.step()
        total_loss += float(loss.item())
    return total_loss / max(1, len(loader))


def _evaluate_accuracy(
    model: torch.nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> float:
    """Evaluate accuracy on the training loader for bootstrap diagnostics."""
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for batch in loader:
            labels = batch["labels"].to(device)
            inputs = {key: value.to(device) for key, value in batch.items() if key != "labels"}
            logits = model(**inputs).logits
            predictions = torch.argmax(logits, dim=-1)
            correct += int((predictions == labels).sum().item())
            total += int(labels.numel())
    return correct / total if total else 0.0


def _train_classifier_from_precomputed_embeddings(
    *,
    model: torch.nn.Module,
    loader: DataLoader,
    epochs: int,
    learning_rate: float,
    device: torch.device,
    examples: int,
) -> None:
    """Train the classifier head quickly using frozen BERT embeddings."""
    model.eval()
    embeddings: list[torch.Tensor] = []
    labels: list[torch.Tensor] = []
    with torch.no_grad():
        for batch in loader:
            batch_labels = batch["labels"]
            inputs = {key: value.to(device) for key, value in batch.items() if key != "labels"}
            base_outputs = model.bert(**inputs)
            pooled = getattr(base_outputs, "pooler_output", None)
            if pooled is None:
                pooled = base_outputs.last_hidden_state[:, 0]
            embeddings.append(pooled.detach().cpu())
            labels.append(batch_labels.detach().cpu())

    features = torch.cat(embeddings).to(device)
    targets = torch.cat(labels).to(device)
    classifier = model.classifier.to(device)
    classifier.train()
    optimizer = torch.optim.AdamW(classifier.parameters(), lr=learning_rate)
    loss_fn = torch.nn.CrossEntropyLoss()

    for epoch in range(1, epochs + 1):
        optimizer.zero_grad(set_to_none=True)
        logits = classifier(features)
        loss = loss_fn(logits, targets)
        loss.backward()
        optimizer.step()
        with torch.no_grad():
            predictions = torch.argmax(classifier(features), dim=-1)
            accuracy = float((predictions == targets).float().mean().item())
        print(
            json.dumps(
                {
                    "epoch": epoch,
                    "loss": round(float(loss.item()), 6),
                    "train_accuracy": round(accuracy, 4),
                    "examples": examples,
                    "device": str(device),
                    "mode": "precomputed_frozen_base",
                },
                ensure_ascii=False,
            )
        )


def _seed_everything(seed: int) -> None:
    """Make the small bootstrap training run repeatable."""
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


if __name__ == "__main__":
    raise SystemExit(main())
