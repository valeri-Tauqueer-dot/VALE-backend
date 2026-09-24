from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import torch


# step4_transformer.py uses absolute imports such as
# `from step3_big_text import read_files`. Add the Talking Brain
# directory to sys.path so the existing file can be reused unchanged.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from step4_transformer import TalkingBrain  # noqa: E402


class TalkingBrainConnector:
    """Connect VALE's existing brain results to the Talking Brain model.

    The connector is deliberately non-authoritative. It only receives
    results produced by the existing VALE brain network and turns those
    results into natural-language output. Any failure returns None so the
    original VALE response pipeline can continue.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.available = False
        self.error: Optional[str] = None
        self.model = None
        self.letters = []
        self.stoi: Dict[str, int] = {}
        self.itos: Dict[int, str] = {}
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        try:
            default_path = _HERE / "transformer_brain_qa_v2.pt"
            self.model_path = Path(
                model_path
                or os.getenv("VALE_TALKING_BRAIN_MODEL", str(default_path))
            )

            checkpoint = self._load_checkpoint()

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
                    "Talking Brain checkpoint is missing keys: "
                    + ", ".join(sorted(missing))
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
            self.available = True

        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            self.available = False

    def _load_checkpoint(self) -> Dict[str, Any]:
        """Load the full checkpoint, rebuilding it from split files when needed."""
        path = self.model_path

        def valid_checkpoint(candidate: Path) -> Optional[Dict[str, Any]]:
            if not candidate.exists() or candidate.stat().st_size < 1024:
                return None
            try:
                value = torch.load(
                    candidate,
                    map_location="cpu",
                    weights_only=False,
                )
                if isinstance(value, dict) and "state_dict" in value:
                    return value
            except Exception:
                return None
            return None

        checkpoint = valid_checkpoint(path)
        if checkpoint is not None:
            return checkpoint

        part1 = Path(str(path) + ".part1")
        part2 = Path(str(path) + ".part2")

        if not part1.exists() or not part2.exists():
            raise FileNotFoundError(
                "Talking Brain checkpoint is unavailable. Expected either "
                f"{path} or both {part1.name} and {part2.name}."
            )

        temp_path = Path(str(path) + ".rebuilding")
        with open(part1, "rb") as first, open(part2, "rb") as second, open(
            temp_path, "wb"
        ) as output:
            while True:
                chunk = first.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
            while True:
                chunk = second.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)

        rebuilt = valid_checkpoint(temp_path)
        if rebuilt is None:
            try:
                temp_path.unlink()
            except OSError:
                pass
            raise ValueError("The two Talking Brain model parts could not be reconstructed into a valid checkpoint.")

        os.replace(temp_path, path)
        return rebuilt

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

    def respond(
        self,
        user_message: str,
        brain_results: Dict[str, Any],
        max_new_tokens: int = 220,
    ) -> Optional[str]:
        if not self.available or self.model is None:
            return None
        if not isinstance(brain_results, dict) or not brain_results:
            return None

        sections = []
        for name, result in brain_results.items():
            text = self._normalise(result)
            if text:
                sections.append(f"{name}:\n{text}")

        if not sections:
            return None

        prompt = (
            "USER: "
            + (user_message or "").strip()
            + "\nVALE BRAIN RESULTS:\n"
            + "\n\n".join(sections)
            + "\nASSISTANT:"
        )

        context = int(self.model.context)
        ids = [self.stoi[c] for c in prompt[-context:] if c in self.stoi]
        if not ids:
            return None

        x = torch.tensor([ids], dtype=torch.long, device=self.device)
        generated = []

        with torch.no_grad():
            for _ in range(max_new_tokens):
                scores, _ = self.model(x[:, -context:])
                next_id = torch.argmax(scores[0, -1], dim=-1).item()
                char = self.itos[next_id]
                generated.append(char)
                next_tensor = torch.tensor([[next_id]], dtype=torch.long, device=self.device)
                x = torch.cat([x, next_tensor], dim=1)

                text = "".join(generated)
                if text.endswith("\nUSER:"):
                    generated = generated[:-6]
                    break

        answer = "".join(generated).strip()
        return answer or None

    def status(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "device": str(self.device),
            "model": str(getattr(self, "model_path", "")),
            "error": self.error,
        }
