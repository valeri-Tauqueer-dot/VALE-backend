"""
VALE Talking Brain V2 Connector
================================

Loads the trained VALE_TALKING_BRAIN_CONTEXT_V2 checkpoint.

Expected files:

talking_brain/
    transformer_brain_context_v2.part1
    transformer_brain_context_v2.part2

The two parts are reconstructed automatically into:

talking_brain/
    transformer_brain_context_v2.pt
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import torch
import torch.nn as nn


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

BRAIN_DIR = BASE_DIR / "talking_brain"

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
# MODEL
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
            embed_size
        )

        self.position_embedding = nn.Parameter(
            torch.zeros(
                context,
                embed_size
            )
        )

        self.blocks = nn.ModuleList()

        for _ in range(n_layer):

            self.blocks.append(
                TransformerBlock(
                    embed_size,
                    n_head,
                    context,
                    dropout
                )
            )

        self.ln_f = nn.LayerNorm(
            embed_size
        )

        self.head = nn.Linear(
            embed_size,
            vocab_size,
            bias=False
        )

    def forward(
        self,
        idx,
        targets=None
    ):

        B, T = idx.shape

        if T > self.context:
            idx = idx[:, -self.context:]
            T = self.context

        x = self.token_embedding(idx)

        x = x + self.position_embedding[:T]

        for block in self.blocks:
            x = block(x)

        x = self.ln_f(x)

        logits = self.head(x)

        loss = None

        if targets is not None:

            if targets.shape[1] > self.context:
                targets = targets[:, -self.context:]

            loss = nn.functional.cross_entropy(
                logits.reshape(-1, logits.size(-1)),
                targets.reshape(-1)
            )

        return logits, loss


class TransformerBlock(nn.Module):

    def __init__(
        self,
        embed_size,
        n_head,
        context,
        dropout
    ):
        super().__init__()

        self.ln1 = nn.LayerNorm(
            embed_size
        )

        self.attn = nn.MultiheadAttention(
            embed_size,
            n_head,
            dropout=dropout,
            batch_first=True
        )

        self.ln2 = nn.LayerNorm(
            embed_size
        )

        self.ff = nn.Sequential(
            nn.Linear(
                embed_size,
                embed_size * 4
            ),

            nn.GELU(),

            nn.Linear(
                embed_size * 4,
                embed_size
            ),

            nn.Dropout(dropout)
        )

        self.context = context

    def forward(self, x):

        T = x.size(1)

        mask = torch.triu(
            torch.ones(
                T,
                T,
                device=x.device,
                dtype=torch.bool
            ),
            diagonal=1
        )

        h = self.ln1(x)

        attn_out, _ = self.attn(
            h,
            h,
            h,
            attn_mask=mask,
            need_weights=False
        )

        x = x + attn_out

        x = x + self.ff(
            self.ln2(x)
        )

        return x


# ============================================================
# RECONSTRUCT CHECKPOINT
# ============================================================

def reconstruct_checkpoint() -> bool:

    if MODEL_PATH.exists():
        return True

    if not PART1.exists():
        print(
            f"❌ Missing Talking Brain part 1: {PART1}"
        )
        return False

    if not PART2.exists():
        print(
            f"❌ Missing Talking Brain part 2: {PART2}"
        )
        return False

    print("🔧 Reconstructing Talking Brain V2...")

    try:

        with open(PART1, "rb") as f1, \
             open(PART2, "rb") as f2, \
             open(MODEL_PATH, "wb") as out:

            while True:

                chunk = f1.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                out.write(chunk)

            while True:

                chunk = f2.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                out.write(chunk)

        print(
            f"✅ Talking Brain reconstructed: {MODEL_PATH}"
        )

        return True

    except Exception as exc:

        print(
            "❌ Talking Brain reconstruction failed:",
            repr(exc)
        )

        return False


# ============================================================
# LOAD MODEL
# ============================================================

class TalkingBrainConnector:

    def __init__(self):

        self.available = False
        self.error = None
        self.model = None
        self.letters = []
        self.stoi = {}
        self.itos = {}
        self.context = 512

        try:

            if not reconstruct_checkpoint():

                self.error = (
                    "Talking Brain V2 checkpoint unavailable."
                )

                return

            checkpoint = torch.load(
                MODEL_PATH,
                map_location="cpu",
                weights_only=False
            )

            self.letters = checkpoint[
                "letters"
            ]

            self.stoi = {
                ch: i
                for i, ch in enumerate(
                    self.letters
                )
            }

            self.itos = {
                i: ch
                for i, ch in enumerate(
                    self.letters
                )
            }

            self.context = int(
                checkpoint["context"]
            )

            self.model = TalkingBrainV2(
                vocab_size=len(
                    self.letters
                ),
                context=self.context,
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
                )
            )

            self.model.load_state_dict(
                checkpoint["state_dict"],
                strict=True
            )

            self.model.to(DEVICE)
            self.model.eval()

            self.available = True

            print("=" * 60)
            print("🧠 VALE TALKING BRAIN V2 LOADED")
            print(
                "Model:",
                checkpoint["model_type"]
            )
            print(
                "Version:",
                checkpoint["version"]
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
            print("=" * 60)

        except Exception as exc:

            self.error = (
                f"{type(exc).__name__}: {exc}"
            )

            print(
                "❌ TALKING BRAIN V2 ERROR:",
                self.error
            )

    # ========================================================
    # ENCODE
    # ========================================================

    def encode(self, text: str):

        return [
            self.stoi[ch]
            for ch in text
            if ch in self.stoi
        ]

    # ========================================================
    # DECODE
    # ========================================================

    def decode(self, ids):

        return "".join(
            self.itos.get(
                int(i),
                ""
            )
            for i in ids
        )

    # ========================================================
    # GENERATE
    # ========================================================

    @torch.no_grad()
    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 120,
        temperature: float = 0.8
    ) -> str:

        if not self.available:

            return ""

        ids = self.encode(prompt)

        if not ids:

            return ""

        x = torch.tensor(
            [ids],
            dtype=torch.long,
            device=DEVICE
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
                :, -1, :
            ]

            if temperature <= 0:

                next_token = torch.argmax(
                    logits,
                    dim=-1,
                    keepdim=True
                )

            else:

                logits = (
                    logits / temperature
                )

                probabilities = torch.softmax(
                    logits,
                    dim=-1
                )

                next_token = torch.multinomial(
                    probabilities,
                    num_samples=1
                )

            x = torch.cat(
                [x, next_token],
                dim=1
            )

        return self.decode(
            x[0].tolist()
        )

    # ========================================================
    # CLEAN RESPONSE
    # ========================================================

    @staticmethod
    def clean_response(text: str) -> str:

        if not text:
            return ""

        response = text

        if "<ASSISTANT>" in response:

            response = response.split(
                "<ASSISTANT>",
                1
            )[1]

        for marker in [
            "<USER>",
            "<CONTEXT>",
            "<UNITY>",
            "</UNITY>",
            "<HEROIC>",
            "</HEROIC>",
            "<ASSISTANT>",
            "</ASSISTANT>",
        ]:

            response = response.replace(
                marker,
                ""
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
        context: str = ""
    ) -> str:

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
            prompt,
            max_new_tokens=120,
            temperature=0.7
        )

        return self.clean_response(
            raw
        )

    # ========================================================
    # STATUS
    # ========================================================

    def status(self) -> Dict[str, Any]:

        return {
            "available": self.available,
            "device": str(DEVICE),
            "model": str(MODEL_PATH),
            "model_exists": MODEL_PATH.exists(),
            "context": self.context,
            "vocabulary": len(self.letters),
            "error": self.error,
        }


# ============================================================
# GLOBAL CONNECTOR
# ============================================================

talking_brain = TalkingBrainConnector()


# Compatibility aliases
vale_talking_brain = talking_brain
connector = talking_brain
