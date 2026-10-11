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
from typing import Any, Dict, Optional

import os
import re

import torch
import torch.nn as nn
import torch.nn.functional as F

# Knowledge gate: builds the prompt in the format the model was trained on,
# decides whether the model knows a question, and checks its answer.
# If knowledge_gate.py is missing the server still starts; the Talking Brain
# just stays silent and VALE uses its normal fallback answer.
try:
    from .knowledge_gate import KnowledgeBase, build_prompt, extract_answer
except ImportError:  # running this file directly, not as part of the package
    try:
        from knowledge_gate import KnowledgeBase, build_prompt, extract_answer
    except Exception as _gate_import_error:
        KnowledgeBase = None
        build_prompt = None
        extract_answer = None
        print(
            "⚠️ knowledge_gate.py could not be loaded "
            f"({type(_gate_import_error).__name__}: {_gate_import_error}). "
            "Put it in the same folder as talking_brain_connector.py. "
            "The Talking Brain will stay silent until then.",
            flush=True,
        )


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

# A small free server has a very weak CPU. One thread is fastest there.
# On a bigger paid server, set the env variable VALE_TORCH_THREADS to a bigger number.
try:
    torch.set_num_threads(
        max(1, int(os.environ.get("VALE_TORCH_THREADS", "1")))
    )
except Exception:
    pass


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

        # Q&A knowledge used to decide whether the model knows a question.
        self.knowledge = None  # a KnowledgeBase once loaded

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
            # KNOWLEDGE (decides what the model is allowed to answer)
            # ------------------------------------------------

            try:

                if KnowledgeBase is None:

                    raise RuntimeError(
                        "knowledge_gate.py is missing"
                    )

                self.knowledge = KnowledgeBase()

                if len(self.knowledge) == 0:

                    print(
                        "⚠️ Knowledge gate found 0 Q&A pairs. "
                        "Keep the Q&A .txt files in talking_brain/ "
                        "(or talking_brain/data/). Talking Brain stays silent.",
                        flush=True,
                    )

                    self.knowledge = None

                else:

                    print(
                        "📚 Knowledge gate loaded:",
                        len(self.knowledge),
                        "known questions",
                        flush=True,
                    )

            except Exception as knowledge_error:

                self.knowledge = None

                print(
                    "⚠️ Knowledge gate failed to load:",
                    f"{type(knowledge_error).__name__}: {knowledge_error}",
                    flush=True,
                )

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

        # Fast path (remembers old work, stops early).
        # If anything goes wrong, use the old slow path.
        try:

            return self._generate_fast(
                encoded,
                max_new_tokens,
                temperature,
            )

        except Exception as error:

            print(
                "⚠️ Fast generation failed, using slow path:",
                error,
            )

            return self._generate_slow(
                encoded,
                max_new_tokens,
                temperature,
            )

    # ========================================================
    # FAST GENERATE (key/value cache)
    # ========================================================

    def _forward_cached(
        self,
        idx: torch.Tensor,
        caches: list,
        start_pos: int,
    ) -> torch.Tensor:

        m = self.model

        batch_size, steps = idx.shape

        positions = torch.arange(
            start_pos,
            start_pos + steps,
            device=idx.device,
        )

        x = (
            m.token_embedding(idx)
            + m.position_embedding(positions)
        )

        for i, block in enumerate(m.blocks):

            h = block.ln1(x)

            attn = block.attn

            embed = attn.embed_dim

            heads = attn.num_heads

            head_dim = embed // heads

            qkv = F.linear(
                h,
                attn.in_proj_weight,
                attn.in_proj_bias,
            )

            q, k, v = qkv.split(
                embed,
                dim=-1,
            )

            q = q.view(
                batch_size, steps, heads, head_dim
            ).transpose(1, 2)

            k = k.view(
                batch_size, steps, heads, head_dim
            ).transpose(1, 2)

            v = v.view(
                batch_size, steps, heads, head_dim
            ).transpose(1, 2)

            if caches[i] is not None:

                k = torch.cat(
                    [caches[i][0], k],
                    dim=2,
                )

                v = torch.cat(
                    [caches[i][1], v],
                    dim=2,
                )

            caches[i] = (k, v)

            out = F.scaled_dot_product_attention(
                q,
                k,
                v,
                is_causal=(steps > 1),
            )

            out = out.transpose(1, 2).reshape(
                batch_size, steps, embed
            )

            out = F.linear(
                out,
                attn.out_proj.weight,
                attn.out_proj.bias,
            )

            x = x + out

            x = x + block.ff(
                block.ln2(x)
            )

        x = m.ln(x)

        return m.head(
            x[:, -1, :]
        )

    def _generate_fast(
        self,
        encoded,
        max_new_tokens: int,
        temperature: float,
    ) -> str:

        # Keep prompt + new letters inside the model context.
        room = self.context - max_new_tokens

        if room < 1:

            raise ValueError("max_new_tokens too large")

        encoded = list(encoded[-room:])

        ids = torch.tensor(
            [encoded],
            dtype=torch.long,
            device=DEVICE,
        )

        caches = [None] * len(self.model.blocks)

        logits = self._forward_cached(
            ids,
            caches,
            0,
        )

        position = len(encoded)

        out_ids = list(encoded)

        generated = ""

        for _ in range(max_new_tokens):

            if temperature <= 0:

                next_token = torch.argmax(
                    logits,
                    dim=-1,
                    keepdim=True,
                )

            else:

                probabilities = torch.softmax(
                    logits / max(temperature, 1e-5),
                    dim=-1,
                )

                next_token = torch.multinomial(
                    probabilities,
                    num_samples=1,
                )

            token_id = int(next_token.item())

            out_ids.append(token_id)

            generated += self.itos.get(
                token_id,
                "",
            )

            # Stop when the answer is finished.
            if (
                generated.endswith("<END>")
                or generated.endswith("</ASSISTANT>")
                or generated.endswith("<USER>")
            ):

                break

            logits = self._forward_cached(
                next_token,
                caches,
                position,
            )

            position += 1

        return self.decode(
            out_ids
        )

    # ========================================================
    # SLOW GENERATE (old method, kept as a safe backup)
    # ========================================================

    def _generate_slow(
        self,
        encoded,
        max_new_tokens: int,
        temperature: float,
    ) -> str:

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

        # Cut at the FIRST tag. The old version kept the text that came
        # after a stray <USER>/<CONTEXT> tag, which glued a second,
        # unrelated memorised answer onto the reply.

        if extract_answer is None:

            return str(text or "").strip()

        return extract_answer(
            text
        )

    # ========================================================
    # CHAT
    # ========================================================

    MEDIA_MARKER = "=== VALE MEDIA CONTEXT ==="

    MEDIA_REPLY = (
        "I received your file, but I can't read or describe files yet - "
        "my talking brain is too small for that. "
        "Ask me a text question instead."
    )

    def _question_from(
        self,
        message: str,
    ) -> Optional[str]:
        """
        Return the question the user typed.

        /chat-media wraps the upload in a long "=== VALE MEDIA CONTEXT ==="
        block. The model must never see that block. Returns None when the
        message is only a file with no typed question.
        """

        text = str(message or "")

        if self.MEDIA_MARKER not in text:

            return text.strip()[:300]

        found = re.search(
            r"USER QUESTION:\s*(.+?)\s*(?:\n\s*\n|" + re.escape(self.MEDIA_MARKER) + r"|$)",
            text,
            re.S,
        )

        if found and found.group(1).strip():

            return found.group(1).strip()[:300]

        return None

    def chat(
        self,
        message: str,
        unity: str = "",
        heroic: str = "",
        context: str = "",
    ) -> str:

        if not self.available:

            return ""

        # unity / heroic / context are accepted so ai_core.py does not need
        # to change, but they are NOT sent to the model for now: the UNITY
        # and HEROIC brains return status dictionaries (no sentences), so
        # those slots were always empty. Feed them to the model only when
        # those brains return real text.

        question = self._question_from(
            message
        )

        if question is None:

            return self.MEDIA_REPLY

        knowledge = self.knowledge

        if knowledge is None or not question:

            return ""

        # ----------------------------------------------------
        # GATE: does the model know this question?
        # ----------------------------------------------------

        match = knowledge.lookup(
            question
        )

        print(
            f"🧠 TALKING BRAIN GATE | {match.kind} "
            f"score={match.score:.2f} "
            f"matched={(match.entry.question if match.entry else None)!r}",
            flush=True,
        )

        if match.kind != "known":

            return knowledge.fallback_text(
                match
            )

        # ----------------------------------------------------
        # ASK THE MODEL in the format it was trained on
        # ----------------------------------------------------

        entry = match.entry

        prompt = build_prompt(
            entry.question
        )

        budget = max(
            40,
            min(
                entry.longest_answer + 30,
                self.context - len(prompt) - 8,
            ),
        )

        raw = self.generate(
            prompt=prompt,
            max_new_tokens=budget,
            temperature=0.2,
        )

        answer = extract_answer(
            raw
        )

        # ----------------------------------------------------
        # CHECK the model's text against the stored answer
        # ----------------------------------------------------

        good, ratio, stored = knowledge.verify(
            answer,
            entry,
        )

        print(
            f"🧠 TALKING BRAIN ANSWER | similarity={ratio:.2f} | "
            + ("model text accepted" if good else "model garbled it, stored answer used"),
            flush=True,
        )

        return answer if good else stored

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
            "knowledge_entries": len(self.knowledge) if self.knowledge else 0,
            "error": self.error,
        }


# ============================================================
# GLOBAL CONNECTOR
# ============================================================

talking_brain = TalkingBrainConnector()


# Compatibility aliases
vale_talking_brain = talking_brain
connector = talking_brain
