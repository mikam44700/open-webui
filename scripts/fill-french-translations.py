#!/usr/bin/env python3
"""Fill empty fr-FR Open WebUI translations with a local Marian model."""

from __future__ import annotations

import json
import re
from pathlib import Path

import torch
from transformers import MarianMTModel, MarianTokenizer


ROOT = Path(__file__).resolve().parents[1]
TRANSLATION_FILE = ROOT / "src/lib/i18n/locales/fr-FR/translation.json"
MODEL_NAME = "Helsinki-NLP/opus-mt-en-fr"
BATCH_SIZE = 12

PROTECTED = re.compile(
    r"\{\{[^{}]+\}\}|\$\{[^{}]+\}|https?://\S+|`[^`]+`|<[^<>]+>"
)
PLURAL_SUFFIX = re.compile(r"_(one|many|other)$")


def mask_tokens(text: str) -> tuple[str, list[str]]:
    tokens: list[str] = []

    def replace(match: re.Match[str]) -> str:
        tokens.append(match.group(0))
        return f" ZXQPH{len(tokens) - 1}QXZ "

    return PROTECTED.sub(replace, text), tokens


def restore_tokens(text: str, tokens: list[str]) -> str:
    for index, token in enumerate(tokens):
        marker = f"ZXQPH{index}QXZ"
        text = re.sub(rf"\s*{re.escape(marker)}\s*", token, text)
    return text.strip()


def main() -> None:
    translations: dict[str, str] = json.loads(TRANSLATION_FILE.read_text())
    missing = [key for key, value in translations.items() if value == ""]
    print(f"Traductions manquantes: {len(missing)}")

    tokenizer = MarianTokenizer.from_pretrained(MODEL_NAME, local_files_only=True)
    model = MarianMTModel.from_pretrained(MODEL_NAME, local_files_only=True)
    model.eval()

    prepared: list[tuple[str, str, list[str]]] = []
    for key in missing:
        source = PLURAL_SUFFIX.sub("", key)
        masked, protected = mask_tokens(source)
        prepared.append((key, masked, protected))

    for offset in range(0, len(prepared), BATCH_SIZE):
        batch = prepared[offset : offset + BATCH_SIZE]
        encoded = tokenizer(
            [item[1] for item in batch],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )
        with torch.inference_mode():
            generated = model.generate(
                **encoded,
                max_new_tokens=512,
                num_beams=4,
                early_stopping=True,
            )
        translated = tokenizer.batch_decode(generated, skip_special_tokens=True)

        for (key, _masked, protected), value in zip(batch, translated, strict=True):
            restored = restore_tokens(value, protected)
            translations[key] = restored or key

        completed = min(offset + BATCH_SIZE, len(prepared))
        print(f"{completed}/{len(prepared)}", flush=True)

    TRANSLATION_FILE.write_text(
        json.dumps(translations, ensure_ascii=False, indent="\t") + "\n"
    )

    remaining = sum(value == "" for value in translations.values())
    print(f"Valeurs encore vides: {remaining}")


if __name__ == "__main__":
    main()
