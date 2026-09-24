from __future__ import annotations

"""
VALE TALKING BRAIN CONNECTOR

Flow:

VALE Brain Network
        ↓
brain results
        ↓
Talking Brain
        ↓
natural language
        ↓
USER

The Talking Brain is NOT a specialist brain.

Supported model files:

1. transformer_brain_qa_v2.pt

OR

2. transformer_brain_qa_v2.pt.part1
   transformer_brain_qa_v2.pt.part2

OR

3. transformer_brain_qa_v2.part1
   transformer_brain_qa_v2.part2

The split files are never deleted.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import torch


# ============================================================
# TALKING BRAIN DIRECTORY
# ============================================================

HERE = Path(__file__).resolve().parent

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


# ============================================================
# IMPORT MODEL
# ============================================================

from step4_transformer import TalkingBrain


# ============================================================
# TALKING BRAIN CONNECTOR
# ============================================================

class TalkingBrainConnector:

    def __init__(
        self,
        model_path: Optional[str] = None,
    ):

        self.available = False

        self.error: Optional[str] = None

        self.model = None

        self.letters = []

        self.stoi: Dict[str, int] = {}

        self.itos: Dict[int, str] = {}

        # Render normally uses CPU.
        # If CUDA is available, use it.
        self.device = torch.device(
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        self.model_path = self._resolve_model_path(
            model_path
        )

        try:

            checkpoint = self._load_checkpoint()

            required_keys = {
                "state_dict",
                "letters",
                "context",
                "embed_size",
                "n_head",
                "n_layer",
                "dropout",
            }

            if not isinstance(
                checkpoint,
                dict,
            ):
                raise ValueError(
                    "Talking Brain checkpoint is not a dictionary."
                )

            missing = (
                required_keys
                - set(checkpoint.keys())
            )

            if missing:

                raise ValueError(
                    "Talking Brain checkpoint is missing keys: "
                    + ", ".join(
                        sorted(missing)
                    )
                )

            # --------------------------------------------------------
            # VOCABULARY
            # --------------------------------------------------------

            self.letters = list(
                checkpoint["letters"]
            )

            if not self.letters:

                raise ValueError(
                    "Talking Brain vocabulary is empty."
                )

            self.stoi = {
                char: index
                for index, char in enumerate(
                    self.letters
                )
            }

            self.itos = {
                index: char
                for index, char in enumerate(
                    self.letters
                )
            }

            # --------------------------------------------------------
            # CREATE MODEL
            # --------------------------------------------------------

            self.model = TalkingBrain(

                vocab_size=len(
                    self.letters
                ),

                context=int(
                    checkpoint["context"]
                ),

                embed_size=int(
                    checkpoint["embed_size"]
                ),

                n_head=int(
                    checkpoint["n_head"]
                ),

                n_layer=int(
                    checkpoint["n_layer"]
                ),

                dropout=float(
                    checkpoint["dropout"]
                ),
            )

            # --------------------------------------------------------
            # LOAD WEIGHTS
            # --------------------------------------------------------

            self.model.load_state_dict(
                checkpoint["state_dict"],
                strict=True,
            )

            self.model.to(
                self.device
            )

            self.model.eval()

            self.available = True

            self.error = None

            print(
                "============================================================",
                flush=True,
            )

            print(
                "🧠 TALKING BRAIN LOADED",
                flush=True,
            )

            print(
                f"Model: {self.model_path}",
                flush=True,
            )

            print(
                f"Device: {self.device}",
                flush=True,
            )

            print(
                f"Vocabulary: {len(self.letters)}",
                flush=True,
            )

            print(
                f"Context: {self.model.context}",
                flush=True,
            )

            print(
                "============================================================",
                flush=True,
            )

        except Exception as exc:

            self.available = False

            self.error = (
                f"{type(exc).__name__}: {exc}"
            )

            print(
                "============================================================",
                flush=True,
            )

            print(
                "❌ TALKING BRAIN FAILED TO LOAD",
                flush=True,
            )

            print(
                self.error,
                flush=True,
            )

            print(
                "============================================================",
                flush=True,
            )

    # ============================================================
    # RESOLVE MODEL PATH
    # ============================================================

    def _resolve_model_path(
        self,
        model_path: Optional[str],
    ) -> Path:

        # Explicit path supplied by code.
        if model_path:

            return Path(
                model_path
            )

        # Optional environment variable.
        env_path = os.getenv(
            "VALE_TALKING_BRAIN_MODEL",
            "",
        ).strip()

        if env_path:

            return Path(
                env_path
            )

        # Default Render/GitHub location.
        return (
            HERE
            / "transformer_brain_qa_v2.pt"
        )

    # ============================================================
    # VALIDATE COMPLETE CHECKPOINT
    # ============================================================

    @staticmethod
    def _load_file(
        path: Path,
    ) -> Optional[Dict[str, Any]]:

        if not path.exists():

            return None

        if not path.is_file():

            return None

        # Your real brain is ~43 MB.
        # This prevents Git LFS pointer files or tiny placeholders
        # from being treated as the actual model.
        if path.stat().st_size < (
            1024 * 1024
        ):

            return None

        try:

            checkpoint = torch.load(
                path,
                map_location="cpu",
                weights_only=False,
            )

            if not isinstance(
                checkpoint,
                dict,
            ):

                return None

            required_keys = {
                "state_dict",
                "letters",
                "context",
                "embed_size",
                "n_head",
                "n_layer",
                "dropout",
            }

            if not required_keys.issubset(
                checkpoint.keys()
            ):

                return None

            return checkpoint

        except Exception:

            return None

    # ============================================================
    # FIND SPLIT FILES
    # ============================================================

    def _split_candidates(
        self,
    ) -> Tuple[
        Tuple[Path, Path],
        ...
    ]:

        path = self.model_path

        candidates = []

        # --------------------------------------------------------
        # FORMAT 1
        #
        # transformer_brain_qa_v2.pt.part1
        # transformer_brain_qa_v2.pt.part2
        # --------------------------------------------------------

        candidates.append(
            (
                Path(
                    str(path)
                    + ".part1"
                ),

                Path(
                    str(path)
                    + ".part2"
                ),
            )
        )

        # --------------------------------------------------------
        # FORMAT 2
        #
        # transformer_brain_qa_v2.part1
        # transformer_brain_qa_v2.part2
        #
        # THIS IS THE FORMAT YOU CURRENTLY HAVE.
        # --------------------------------------------------------

        if path.suffix == ".pt":

            base = path.with_suffix("")

            candidates.append(
                (
                    Path(
                        str(base)
                        + ".part1"
                    ),

                    Path(
                        str(base)
                        + ".part2"
                    ),
                )
            )

        # Remove duplicate pairs.
        unique = []

        seen = set()

        for first, second in candidates:

            key = (
                str(first),
                str(second),
            )

            if key in seen:
                continue

            seen.add(key)

            unique.append(
                (
                    first,
                    second,
                )
            )

        return tuple(
            unique
        )

    # ============================================================
    # RECONSTRUCT MODEL
    # ============================================================

    def _reconstruct(
        self,
        part1: Path,
        part2: Path,
    ) -> Dict[str, Any]:

        if not part1.exists():

            raise FileNotFoundError(
                f"Missing Talking Brain part 1: {part1}"
            )

        if not part2.exists():

            raise FileNotFoundError(
                f"Missing Talking Brain part 2: {part2}"
            )

        if part1.stat().st_size == 0:

            raise ValueError(
                f"Talking Brain part 1 is empty: {part1}"
            )

        if part2.stat().st_size == 0:

            raise ValueError(
                f"Talking Brain part 2 is empty: {part2}"
            )

        output = self.model_path

        temporary = Path(
            str(output)
            + ".rebuilding"
        )

        print(
            "🔧 Reconstructing Talking Brain...",
            flush=True,
        )

        print(
            f"Part 1: {part1.name} "
            f"({part1.stat().st_size:,} bytes)",
            flush=True,
        )

        print(
            f"Part 2: {part2.name} "
            f"({part2.stat().st_size:,} bytes)",
            flush=True,
        )

        try:

            # ----------------------------------------------------
            # WRITE PART 1 + PART 2
            # ----------------------------------------------------

            with open(
                temporary,
                "wb",
            ) as output_file:

                with open(
                    part1,
                    "rb",
                ) as first:

                    while True:

                        chunk = first.read(
                            1024 * 1024
                        )

                        if not chunk:
                            break

                        output_file.write(
                            chunk
                        )

                with open(
                    part2,
                    "rb",
                ) as second:

                    while True:

                        chunk = second.read(
                            1024 * 1024
                        )

                        if not chunk:
                            break

                        output_file.write(
                            chunk
                        )

                output_file.flush()

                try:

                    os.fsync(
                        output_file.fileno()
                    )

                except OSError:

                    pass

            combined_size = (
                temporary.stat().st_size
            )

            print(
                f"Combined size: "
                f"{combined_size:,} bytes",
                flush=True,
            )

            # ----------------------------------------------------
            # VERIFY RECONSTRUCTED MODEL
            # ----------------------------------------------------

            checkpoint = self._load_file(
                temporary
            )

            if checkpoint is None:

                raise ValueError(
                    "The reconstructed Talking Brain "
                    "checkpoint failed validation."
                )

            # ----------------------------------------------------
            # ATOMICALLY MOVE INTO FINAL LOCATION
            # ----------------------------------------------------

            os.replace(
                temporary,
                output,
            )

            print(
                f"✅ Talking Brain reconstructed: "
                f"{output}",
                flush=True,
            )

            return checkpoint

        except Exception:

            try:

                if temporary.exists():

                    temporary.unlink()

            except OSError:

                pass

            raise

    # ============================================================
    # LOAD CHECKPOINT
    # ============================================================

    def _load_checkpoint(
        self,
    ) -> Dict[str, Any]:

        # --------------------------------------------------------
        # FIRST: COMPLETE .PT FILE
        # --------------------------------------------------------

        checkpoint = self._load_file(
            self.model_path
        )

        if checkpoint is not None:

            print(
                f"✅ Complete Talking Brain found: "
                f"{self.model_path}",
                flush=True,
            )

            return checkpoint

        # --------------------------------------------------------
        # SECOND: SPLIT FILES
        # --------------------------------------------------------

        for part1, part2 in (
            self._split_candidates()
        ):

            if (
                part1.exists()
                and part2.exists()
            ):

                return self._reconstruct(
                    part1,
                    part2,
                )

        # --------------------------------------------------------
        # NOTHING FOUND
        # --------------------------------------------------------

        names = []

        for part1, part2 in (
            self._split_candidates()
        ):

            names.append(
                f"{part1.name} + {part2.name}"
            )

        raise FileNotFoundError(
            "Talking Brain checkpoint is unavailable.\n"
            f"Expected complete file:\n"
            f"  {self.model_path}\n"
            "or one of these split pairs:\n  "
            + "\n  ".join(names)
        )

    # ============================================================
    # CONVERT BRAIN RESULT TO TEXT
    # ============================================================

    @staticmethod
    def _text(
        value: Any,
    ) -> str:

        if value is None:

            return ""

        if isinstance(
            value,
            str,
        ):

            return value.strip()

        try:

            return json.dumps(
                value,
                ensure_ascii=False,
                default=str,
            )

        except Exception:

            return str(value)

    # ============================================================
    # GENERATE RESPONSE
    # ============================================================

    def respond(
        self,
        user_message: str,
        brain_results: Dict[str, Any],
        max_new_tokens: int = 220,
    ) -> Optional[str]:

        if not self.available:

            print(
                "⚠️ Talking Brain unavailable:",
                self.error,
                flush=True,
            )

            return None

        if self.model is None:

            return None

        if not isinstance(
            brain_results,
            dict,
        ):

            return None

        # --------------------------------------------------------
        # COMBINE SPECIALIST BRAIN RESULTS
        # --------------------------------------------------------

        sections = []

        for name, result in (
            brain_results.items()
        ):

            text = self._text(
                result
            )

            if not text:

                continue

            # The trained model has context=128.
            # Keep specialist output compact.
            text = text[:500]

            sections.append(
                f"{name}: {text}"
            )

        if not sections:

            return None

        compact_results = "\n".join(
            sections
        )

        # --------------------------------------------------------
        # TALKING BRAIN PROMPT
        # --------------------------------------------------------

        prompt = (
            "USER: "
            + (
                user_message
                or ""
            ).strip()
            + "\n"
            + compact_results
            + "\nASSISTANT:"
        )

        context = int(
            self.model.context
        )

        # Keep only the model's available context.
        prompt = prompt[
            -context:
        ]

        # --------------------------------------------------------
        # CHARACTER ENCODING
        # --------------------------------------------------------

        ids = []

        for char in prompt:

            if char in self.stoi:

                ids.append(
                    self.stoi[char]
                )

        if not ids:

            return None

        x = torch.tensor(
            [ids],
            dtype=torch.long,
            device=self.device,
        )

        generated = []

         # --------------------------------------------------------
        # GENERATE
        # --------------------------------------------------------

        try:

            with torch.no_grad():

                for _ in range(
                    max(
                        1,
                        int(
                            max_new_tokens
                        ),
                    )
                ):

                    output = self.model(
                        x[:, -context:]
                    )

                    # Your TalkingBrain returns:
                    #
                    # (logits, attention)
                    #
                    # So take output[0].
                    if isinstance(
                        output,
                        tuple,
                    ):

                        logits = output[0]

                    else:

                        logits = output

                    next_id = int(
                        torch.argmax(
                            logits[
                                0,
                                -1
                            ],
                            dim=-1,
                        ).item()
                    )

                    char = self.itos.get(
                        next_id,
                        "",
                    )

                    if not char:

                        break

                    generated.append(
                        char
                    )

                    next_tensor = torch.tensor(
                        [[next_id]],
                        dtype=torch.long,
                        device=self.device,
                    )

                    x = torch.cat(
                        [
                            x,
                            next_tensor,
                        ],
                        dim=1,
                    )

                    current = "".join(
                        generated
                    )

                    # Stop when the model starts another example.
                    if (
                        current.endswith(
                            "\nUSER:"
                        )
                        or current.endswith(
                            "\nQ:"
                        )
                    ):

                        break

            answer = "".join(
                generated
            ).strip()

            # Remove accidental training prefixes.
            for prefix in (
                "ASSISTANT:",
                "A:",
            ):

                if answer.startswith(
                    prefix
                ):

                    answer = answer[
                        len(prefix):
                    ].strip()

            return (
                answer
                if answer
                else None
            )

        except Exception as exc:

            print(
                "❌ TALKING BRAIN INFERENCE ERROR:",
                type(exc).__name__,
                str(exc),
                flush=True,
            )

            return None

    # ============================================================
    # STATUS
    # ============================================================

    def status(
        self,
    ) -> Dict[str, Any]:

        return {

            "available":
                self.available,

            "device":
                str(self.device),

            "model":
                str(self.model_path),

            "model_exists":
                self.model_path.exists(),

            "error":
                self.error,
        }
