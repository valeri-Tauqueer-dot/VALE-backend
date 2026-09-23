"""VALE Talking Brain integration layer.

The Talking Brain is intentionally a communication layer. It receives
information produced by the existing VALE brains and turns that information
into a natural-language response. It does not replace, register, or control
those specialized brains.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import torch

# step4_transformer.py in the existing Talking Brain project uses
# local absolute imports (for example: step3_big_text). Add its own
# directory to Python's import path without changing that existing file.
_PACKAGE_DIR = Path(__file__).resolve().parent
if str(_PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_DIR))

from .step4_transformer import TalkingBrain


class TalkingBrainConnector:
    """Load and run the standalone VALE Talking Brain checkpoint."""

    def __init__(self, model_path: Optional[str] = None):
        self.available = False
        self.error: Optional[str] = None
        self.model = None
        self.letters = []
        self.stoi: Dict[str, int] = {}
        self.itos: Dict[int, str] = {}
        self.model_path: Optional[Path] = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        try:
            base = Path(__file__).resolve().parent
            self.model_path = Path(
                model_path
                or os.getenv(
                    "VALE_TALKING_BRAIN_MODEL",
                    str(base / "transformer_brain_qa_v2.pt"),
                )
            )

            self._rebuild_if_needed()
            self._load()
            self.available = True
        except Exception as exc:
            # Never prevent the existing VALE system from starting.
            self.available = False
            self.error = f"{type(exc).__name__}: {exc}"

    def _rebuild_if_needed(self) -> None:
        """Ensure the real checkpoint exists, rebuilding it from split parts when needed."""
        assert self.model_path is not None

        stem = self.model_path.with_suffix("") if self.model_path.suffix == ".pt" else self.model_path
        part1 = Path(str(stem) + ".part1")
        part2 = Path(str(stem) + ".part2")

        # GitHub may contain a tiny placeholder .pt because the real
        # checkpoint is stored as two parts. Treat an unusually small
        # .pt file as a placeholder and rebuild it automatically.
        checkpoint_is_real = self.model_path.exists() and self.model_path.stat().st_size > 1_000_000

        if checkpoint_is_real:
            return

        if not part1.exists() or not part2.exists():
            if self.model_path.exists():
                return
            raise FileNotFoundError(
                f"Talking Brain model not found: {self.model_path}. "
                f"Expected either the .pt file or both {part1.name} and {part2.name}."
            )

        with part1.open("rb") as first, part2.open("rb") as second, self.model_path.open("wb") as output:
            output.write(first.read())
            output.write(second.read())

    def _load(self) -> None:
        assert self.model_path is not None

        try:
            checkpoint = torch.load(
                self.model_path,
                map_location=self.device,
                weights_only=False,
            )
        except Exception:
            # If the repository had a stale/tiny placeholder, rebuild once
            # from the split checkpoint parts and try again.
            self._rebuild_if_needed()
            checkpoint = torch.load(
                self.model_path,
                map_location=self.device,
                weights_only=False,
            )

        required = {
            "state_dict",
            "letters",
            "context",
            "embed_size",
            "n_head",
            "n_layer",
            "dropout",
        }
        missing = required.difference(checkpoint.keys())
        if missing:
            raise ValueError(
                f"Talking Brain checkpoint is missing keys: {sorted(missing)}"
            )

        self.letters = checkpoint["letters"]
        self.stoi = {char: i for i, char in enumerate(self.letters)}
        self.itos = {i: char for i, char in enumerate(self.letters)}

        self.model = TalkingBrain(
            vocab_size=len(self.letters),
            context=checkpoint["context"],
            embed_size=checkpoint["embed_size"],
            n_head=checkpoint["n_head"],
            n_layer=checkpoint["n_layer"],
            dropout=checkpoint["dropout"],
        )
        self.model.load_state_dict(checkpoint["state_dict"])
        self.model.to(self.device)
        self.model.eval()

    @staticmethod
    def _normalise(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            return str(value)

    def _flatten_brain_results(self, brain_results: Any) -> str:
        """Turn the network's result dictionary into readable source text."""
        if not isinstance(brain_results, dict):
            text = self._normalise(brain_results)
            return text

        chunks = []
        for brain_name, wrapper in brain_results.items():
            value = wrapper

            if isinstance(wrapper, dict) and "result" in wrapper:
                value = wrapper["result"]

            text = self._normalise(value)
            if text:
                chunks.append(f"{str(brain_name).upper()}: {text}")

        return "\n".join(chunks)

    @torch.no_grad()
    def respond(
        self,
        user_message: str,
        brain_results: Any,
        max_new_tokens: int = 220,
    ) -> Optional[str]:
        """Generate the user-facing response from existing brain output."""
        if not self.available or self.model is None:
            return None

        source_text = self._flatten_brain_results(brain_results)
        if not source_text:
            return None

        # Keep the source compact enough for the model's 128-character context.
        # The beginning contains the user's actual request; the source is then
        # trimmed to the remaining space.
        user_text = self._normalise(user_message)
        prefix = f"USER: {user_text}\nVALE: "
        suffix = "\nASSISTANT:"
        available_source = max(
            1,
            self.model.context - len(prefix) - len(suffix) - 1,
        )
        source_text = source_text[:available_source]
        prompt = prefix + source_text + suffix

        ids = [self.stoi[c] for c in prompt if c in self.stoi]
        if not ids:
            return None

        x = torch.tensor([ids], dtype=torch.long, device=self.device)
        generated = []

        for _ in range(max_new_tokens):
            x_cond = x[:, -self.model.context:]
            output = self.model(x_cond)
            scores = output[0] if isinstance(output, tuple) else output
            next_id = torch.argmax(scores[0, -1], dim=-1).item()
            char = self.itos[next_id]

            generated.append(char)
            x = torch.cat(
                [x, torch.tensor([[next_id]], dtype=torch.long, device=self.device)],
                dim=1,
            )

            current = "".join(generated)
            if current.endswith("\nUSER:"):
                generated = list(current[:-6])
                break

        answer = "".join(generated).strip()
        return answer or None

    def status(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "device": str(self.device),
            "model": str(self.model_path) if self.model_path else None,
            "error": self.error,
        }
