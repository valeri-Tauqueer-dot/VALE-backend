"""
VALE TALKING BRAIN V2 CONNECTOR
================================

Context-aware VALE Talking Brain V2.

Expected repository structure:

VALE-backend/
│
├── main.py
├── ...
│
└── talking_brain/
    ├── talking_brain_connector.py
    ├── transformer_brain_context_v2.part1
    └── transformer_brain_context_v2.part2

The connector reconstructs:

    transformer_brain_context_v2.pt

inside the SAME talking_brain directory.

IMPORTANT:
This file is itself inside talking_brain/.
Therefore we MUST NOT create:

    talking_brain/talking_brain/

"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import torch
import torch.nn as nn


# ============================================================
# PATHS
# ============================================================

# This file is located at:
#
#     VALE-backend/talking_brain/talking_brain_connector.py
#
# Therefore this is already the correct brain directory.

BRAIN_DIR = Path(__file__).resolve().parent

PART1 = BRAIN_DIR / "transformer_brain_context_v2.part1"
PART2 = BRAIN_DIR / "transformer_brain_context_v2.part2"

MODEL_PATH = BRAIN_DIR / "transformer_brain_context_v2.pt"


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


# ============================================================
# TRANSFORMER BLOCK
# ============================================================

class TransformerBlock(nn.Module):

    def __init__(
        self,
        embed_size: int,
        n_head: int,
        context: int,
        dropout: float,
    ):
        super().__init__()

        self.ln1 = nn.LayerNorm(
            embed_size
        )

        self.attn = nn.MultiheadAttention(
            embed_size,
            n_head,
            dropout=dropout,
            batch_first=True,
        )

        self.ln2 = nn.LayerNorm(
            embed_size
        )

        self.ff = nn.Sequential(
            nn.Linear(
                embed_size,
                embed_size * 4,
            ),
            nn.GELU(),
            nn.Linear(
                embed_size * 4,
                embed_size,
            ),
            nn.Dropout(
                dropout
            ),
        )

        self.context = context

    def forward(
        self,
        x: torch.Tensor,
    ) -> torch.Tensor:

        sequence_length = x.size(1)

        # Causal attention mask.
        # True means that the position is masked.

        mask = torch.triu(
            torch.ones(
                sequence_length,
                sequence_length,
                device=x.device,
                dtype=torch.bool,
            ),
            diagonal=1,
        )

        h = self.ln1(x)

        attn_out, _ = self.attn(
            h,
            h,
            h,
            attn_mask=mask,
            need_weights=False,
        )

        x = x + attn_out

        x = x + self.ff(
            self.ln2(x)
        )

        return x


# ============================================================
# TALKING BRAIN V2
# ============================================================

class TalkingBrainV2(nn.Module):

    def __init__(
        self,
        vocab_size: int,
        context: int,
        embed_size: int,
        n_head: int,
        n_layer: int,
        dropout: float = 0.1,
    ):
        super().__init__()

        self.context = context
        self.embed_size = embed_size

        self.token_embedding = nn.Embedding(
            vocab_size,
            embed_size,
        )

        # IMPORTANT:
        # This MUST be an nn.Embedding (not a bare nn.Parameter).
        # An nn.Embedding's state_dict key is "position_embedding.weight",
        # which is what the trained checkpoint actually contains. A raw
        # nn.Parameter would key as just "position_embedding" and fail
        # to load.

        self.position_embedding = nn.Embedding(
            context,
            embed_size,
        )

        self.blocks = nn.ModuleList()

        for _ in range(n_layer):

            self.blocks.append(
                TransformerBlock(
                    embed_size=embed_size,
                    n_head=n_head,
                    context=context,
                    dropout=dropout,
                )
            )

        self.ln = nn.LayerNorm(
            embed_size
        )

        self.head = nn.Linear(
            embed_size,
            vocab_size,
        )

    def forward(
        self,
        idx: torch.Tensor,
        targets: torch.Tensor | None = None,
    ):

        batch_size, sequence_length = idx.shape

        if sequence_length > self.context:

            idx = idx[
                :,
                -self.context:
            ]

            sequence_length = self.context

        x = self.token_embedding(
            idx
        )

        positions = torch.arange(
            sequence_length,
            device=idx.device,
        )

        x = (
            x
            + self.position_embedding(
                positions
            )
        )

        for block in self.blocks:

            x = block(x)

        x = self.ln(x)

        logits = self.head(x)

        loss = None

        if targets is not None:

            if targets.shape[1] > self.context:

                targets = targets[
                    :,
                    -self.context:
                ]

            loss = nn.functional.cross_entropy(
                logits.reshape(
                    -1,
                    logits.size(-1),
                ),
                targets.reshape(-1),
            )

        return logits, loss


# ============================================================
# CHECKPOINT RECONSTRUCTION
# ============================================================

def reconstruct_checkpoint() -> bool:
    """
    Reconstruct the V2 checkpoint from the two GitHub files.

    The files MUST be directly inside this directory:

        talking_brain/
            transformer_brain_context_v2.part1
            transformer_brain_context_v2.part2
    """

    # Already reconstructed.
    if MODEL_PATH.exists():

        print(
            f"✅ Talking Brain checkpoint already exists: "
            f"{MODEL_PATH}"
        )

        return True

    print("=" * 60)
    print("🧠 VALE TALKING BRAIN V2 FILE CHECK")
    print("=" * 60)

    print(
        "Brain directory:",
        BRAIN_DIR
    )

    print(
        "Part 1:",
        PART1
    )

    print(
        "Part 2:",
        PART2
    )

    print(
        "Model:",
        MODEL_PATH
    )

    print("=" * 60)

    # --------------------------------------------------------
    # PART 1
    # --------------------------------------------------------

    if not PART1.exists():

        print(
            "❌ Missing Talking Brain V2 part 1:"
        )

        print(
            PART1
        )

        return False

    # --------------------------------------------------------
    # PART 2
    # --------------------------------------------------------

    if not PART2.exists():

        print(
            "❌ Missing Talking Brain V2 part 2:"
        )

        print(
            PART2
        )

        return False

    # --------------------------------------------------------
    # RECONSTRUCT
    # --------------------------------------------------------

    print(
        "🔧 Reconstructing Talking Brain V2..."
    )

    try:

        with (
            open(PART1, "rb") as file1,
            open(PART2, "rb") as file2,
            open(MODEL_PATH, "wb") as output,
        ):

            while True:

                chunk = file1.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                output.write(chunk)

            while True:

                chunk = file2.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                output.write(chunk)

        print(
            "✅ Talking Brain V2 reconstructed:"
        )

        print(
            MODEL_PATH
        )

        print(
            "Checkpoint size:",
            MODEL_PATH.stat().st_size,
            "bytes",
        )

        return True

    except Exception as exc:

        print(
            "❌ Checkpoint reconstruction failed:"
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        # Remove incomplete checkpoint.

        try:

            if MODEL_PATH.exists():

                MODEL_PATH.unlink()

        except Exception:
            pass

        return False


# ============================================================
# CONNECTOR
# ============================================================

class TalkingBrainConnector:

    def __init__(self):

        self.available = False

        self.error = None

        self.model = None

        self.letters = []

        self.stoi: Dict[str, int] = {}

        self.itos: Dict[int, str] = {}

        self.context = 512

        self.version = None

        self.model_type = None

        self.embed_size = None

        self.n_head = None

        self.n_layer = None

        self.dropout = None

        self._initialize()

    # ========================================================
    # INITIALIZE
    # ========================================================

    def _initialize(self):

        try:

            if not reconstruct_checkpoint():

                self.error = (
                    "Talking Brain V2 checkpoint unavailable."
                )

                return

            print("=" * 60)
            print(
                "🧠 Loading VALE Talking Brain V2..."
            )
            print("=" * 60)

            checkpoint = torch.load(
                MODEL_PATH,
                map_location="cpu",
                weights_only=False,
            )

            if not isinstance(
                checkpoint,
                dict,
            ):

                raise RuntimeError(
                    "Talking Brain checkpoint is not a dictionary."
                )

            required_keys = [
                "model_type",
                "version",
                "state_dict",
                "letters",
                "context",
                "embed_size",
                "n_head",
                "n_layer",
                "dropout",
                "context_format",
            ]

            missing_keys = [
                key
                for key in required_keys
                if key not in checkpoint
            ]

            if missing_keys:

                raise RuntimeError(
                    "Checkpoint is missing required keys: "
                    + ", ".join(
                        missing_keys
                    )
                )

            # ------------------------------------------------
            # CHECKPOINT METADATA
            # ------------------------------------------------

            self.model_type = checkpoint[
                "model_type"
            ]

            self.version = checkpoint[
                "version"
            ]

            self.context = int(
                checkpoint[
                    "context"
                ]
            )

            self.embed_size = int(
                checkpoint[
                    "embed_size"
                ]
            )

            self.n_head = int(
                checkpoint[
                    "n_head"
                ]
            )

            self.n_layer = int(
                checkpoint[
                    "n_layer"
                ]
            )

            self.dropout = float(
                checkpoint[
                    "dropout"
                ]
            )

            # ------------------------------------------------
            # VOCABULARY
            # ------------------------------------------------

            self.letters = list(
                checkpoint[
                    "letters"
                ]
            )

            self.stoi = {
                token: index
                for index, token
                in enumerate(
                    self.letters
                )
            }

            self.itos = {
                index: token
                for index, token
                in enumerate(
                    self.letters
                )
            }

            # ------------------------------------------------
            # MODEL
            # ------------------------------------------------

            self.model = TalkingBrainV2(
                vocab_size=len(
                    self.letters
                ),
                context=self.context,
                embed_size=self.embed_size,
                n_head=self.n_head,
                n_layer=self.n_layer,
                dropout=self.dropout,
            )

            # ------------------------------------------------
            # LOAD TRAINED WEIGHTS
            # ------------------------------------------------

            result = self.model.load_state_dict(
                checkpoint[
                    "state_dict"
                ],
                strict=True,
            )

            # PyTorch normally returns an IncompatibleKeys
            # object. With strict=True both lists must be empty.

            if result.missing_keys:

                raise RuntimeError(
                    "Missing model weights: "
                    + ", ".join(
                        result.missing_keys
                    )
                )

            if result.unexpected_keys:

                raise RuntimeError(
                    "Unexpected model weights: "
                    + ", ".join(
                        result.unexpected_keys
                    )
                )

            # ------------------------------------------------
            # DEVICE
            # ------------------------------------------------

            self.model.to(
                DEVICE
            )

            self.model.eval()

            self.available = True

            # ------------------------------------------------
            # STATUS
            # ------------------------------------------------

            print("=" * 60)
            print(
                "🧠 VALE TALKING BRAIN V2 LOADED"
            )
            print("=" * 60)

            print(
                "Model:",
                self.model_type
            )

            print(
                "Version:",
                self.version
            )

            print(
                "Device:",
                DEVICE
            )

            print(
                "Vocabulary:",
                len(self.letters)
            )

            print(
                "Context:",
                self.context
            )

            print(
                "Embedding:",
                self.embed_size
            )

            print(
                "Heads:",
                self.n_head
            )

            print(
                "Layers:",
                self.n_layer
            )

            print(
                "Weights loaded: ✅"
            )

            print("=" * 60)

        except Exception as exc:

            self.available = False

            self.error = (
                f"{type(exc).__name__}: {exc}"
            )

            print("=" * 60)
            print(
                "❌ TALKING BRAIN V2 INITIALIZATION ERROR"
            )
            print(
                self.error
            )
            print("=" * 60)

    # ========================================================
    # ENCODE
    # ========================================================

    def encode(
        self,
        text: str,
    ):

        if not text:

            return []

        return [
            self.stoi[ch]
            for ch in text
            if ch in self.stoi
        ]

    # ========================================================
    # DECODE
    # ========================================================

    def decode(
        self,
        ids,
    ) -> str:

        return "".join(
            self.itos.get(
                int(token_id),
                "",
            )
            for token_id in ids
        )

    # ========================================================
    # GENERATE
    # ========================================================

    @torch.no_grad()
    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 120,
        temperature: float = 0.7,
    ) -> str:

        if not self.available:

            return ""

        encoded = self.encode(
            prompt
        )

        if not encoded:

            return ""

        x = torch.tensor(
            [encoded],
            dtype=torch.long,
            device=DEVICE,
        )

        for _ in range(
            max_new_tokens
        ):

            x_cond = x[
                :,
                -self.context:
            ]

            logits, _ = self.model(
                x_cond
            )

            logits = logits[
                :,
                -1,
                :,
            ]

            # ------------------------------------------------
            # GREEDY
            # ------------------------------------------------

            if temperature <= 0:

                next_token = torch.argmax(
                    logits,
                    dim=-1,
                    keepdim=True,
                )

            # ------------------------------------------------
            # SAMPLING
            # ------------------------------------------------

            else:

                scaled_logits = (
                    logits
                    / max(
                        temperature,
                        1e-5,
                    )
                )

                probabilities = torch.softmax(
                    scaled_logits,
                    dim=-1,
                )

                next_token = torch.multinomial(
                    probabilities,
                    num_samples=1,
                )

            x = torch.cat(
                [
                    x,
                    next_token,
                ],
                dim=1,
            )

        return self.decode(
            x[0].tolist()
        )

    # ========================================================
    # CLEAN RESPONSE
    # ========================================================

    @staticmethod
    def clean_response(
        text: str,
    ) -> str:

        if not text:

            return ""

        response = text

        # If generation contains the assistant marker,
        # keep only what follows it.

        if "<ASSISTANT>" in response:

            response = response.split(
                "<ASSISTANT>",
                1,
            )[1]

        markers = [
            "<USER>",
            "<CONTEXT>",
            "<UNITY>",
            "</UNITY>",
            "<HEROIC>",
            "</HEROIC>",
            "<ASSISTANT>",
            "</ASSISTANT>",
        ]

        for marker in markers:

            response = response.replace(
                marker,
                "",
            )

        return response.strip()

    # ========================================================
    # CHAT
    # ========================================================

    def chat(
        self,
        message: str,
        unity: str = "",
        heroic: str = "",
        context: str = "",
    ) -> str:

        if not self.available:

            return ""

        prompt = (
            "<USER>"
            + str(message)
            + "<CONTEXT>"
            + str(context)
            + "<UNITY>"
            + str(unity)
            + "</UNITY>"
            + "<HEROIC>"
            + str(heroic)
            + "</HEROIC>"
            + "<ASSISTANT>"
        )

        raw = self.generate(
            prompt=prompt,
            max_new_tokens=120,
            temperature=0.7,
        )

        return self.clean_response(
            raw
        )

    # ========================================================
    # STATUS
    # ========================================================

    def status(
        self,
    ) -> Dict[str, Any]:

        return {
            "available": self.available,
            "device": str(DEVICE),
            "model": str(MODEL_PATH),
            "model_exists": MODEL_PATH.exists(),
            "context": self.context,
            "vocabulary": len(self.letters),
            "version": self.version,
            "model_type": self.model_type,
            "embed_size": self.embed_size,
            "n_head": self.n_head,
            "n_layer": self.n_layer,
            "error": self.error,
        }


# ============================================================
# GLOBAL CONNECTOR
# ============================================================

talking_brain = TalkingBrainConnector()


# Compatibility aliases
vale_talking_brain = talking_brain
connector = talking_brain
