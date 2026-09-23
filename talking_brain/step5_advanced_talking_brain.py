# ============================================================
# VALE TALKING BRAIN — ADVANCED INSTRUCTION TRAINING
# ============================================================
#
# Purpose:
#   Train the existing Talking Brain to learn:
#
#       USER: ...
#       ASSISTANT: ...
#
# instead of simply learning raw text continuation.
#
# This remains a standalone Talking Brain.
# It does NOT connect Alpha, Legend, Marco, Cognitive Brain, etc.
#
# ============================================================

from __future__ import annotations

import os
import math
import random
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F


# ============================================================
# 1. SETTINGS
# ============================================================

ROOT = Path(__file__).resolve().parent

DATA_FILES = [
    ROOT / "qa_vale2.txt",
    ROOT / "qa_safety.txt",
    ROOT / "qa_strategy.txt",
]

OUTPUT_FILE = ROOT / "transformer_brain_advanced.pt"

SEED = 42

EMBED_SIZE = 384
N_HEAD = 6
N_LAYER = 6
DROPOUT = 0.10

CONTEXT = 256

BATCH_SIZE = 32

MAX_STEPS = 30000

LEARNING_RATE = 3e-4

EVAL_INTERVAL = 500
EVAL_BATCHES = 20

TEMPERATURE = 0.65


# ============================================================
# 2. REPRODUCIBILITY
# ============================================================

random.seed(SEED)
torch.manual_seed(SEED)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

device = "cuda" if torch.cuda.is_available() else "cpu"

print("Device:", device)


# ============================================================
# 3. LOAD TRAINING DATA
# ============================================================

def load_text():
    pieces = []

    for file in DATA_FILES:

        if not file.exists():
            print("WARNING: missing:", file)
            continue

        text = file.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        if text.strip():
            pieces.append(text)

    if not pieces:
        raise RuntimeError(
            "No training files were found."
        )

    return "\n\n".join(pieces)


TEXT = load_text()

print("Training characters:", len(TEXT))


# ============================================================
# 4. CHARACTER VOCABULARY
# ============================================================

letters = sorted(list(set(TEXT)))

vocab_size = len(letters)

letter_to_number = {
    ch: i
    for i, ch in enumerate(letters)
}

number_to_letter = {
    i: ch
    for i, ch in enumerate(letters)
}


def encode(text):
    return [
        letter_to_number[ch]
        for ch in text
        if ch in letter_to_number
    ]


def decode(numbers):
    return "".join(
        number_to_letter[int(i)]
        for i in numbers
    )


data = torch.tensor(
    encode(TEXT),
    dtype=torch.long
)

print("Vocabulary:", vocab_size)
print("Encoded tokens:", len(data))


# ============================================================
# 5. TRAIN / VALIDATION SPLIT
# ============================================================

split = int(0.90 * len(data))

train_data = data[:split]
val_data = data[split:]


# ============================================================
# 6. BATCH CREATION
# ============================================================

def get_batch(source):

    if len(source) <= CONTEXT + 1:
        raise RuntimeError(
            "Training data is smaller than CONTEXT."
        )

    starts = torch.randint(
        0,
        len(source) - CONTEXT - 1,
        (BATCH_SIZE,)
    )

    x = torch.stack([
        source[i:i + CONTEXT]
        for i in starts
    ])

    y = torch.stack([
        source[i + 1:i + CONTEXT + 1]
        for i in starts
    ])

    return x.to(device), y.to(device)


# ============================================================
# 7. CAUSAL SELF ATTENTION
# ============================================================

class CausalSelfAttention(nn.Module):

    def __init__(self, embed_size, n_head):

        super().__init__()

        if embed_size % n_head != 0:
            raise ValueError(
                "EMBED_SIZE must divide evenly by N_HEAD"
            )

        self.n_head = n_head
        self.head_dim = embed_size // n_head

        self.qkv = nn.Linear(
            embed_size,
            embed_size * 3
        )

        self.proj = nn.Linear(
            embed_size,
            embed_size
        )

        self.dropout = nn.Dropout(DROPOUT)

        mask = torch.tril(
            torch.ones(
                CONTEXT,
                CONTEXT
            )
        )

        self.register_buffer(
            "mask",
            mask.view(1, 1, CONTEXT, CONTEXT)
        )

    def forward(self, x):

        B, T, C = x.shape

        qkv = self.qkv(x)

        q, k, v = qkv.chunk(
            3,
            dim=-1
        )

        q = q.view(
            B,
            T,
            self.n_head,
            self.head_dim
        ).transpose(1, 2)

        k = k.view(
            B,
            T,
            self.n_head,
            self.head_dim
        ).transpose(1, 2)

        v = v.view(
            B,
            T,
            self.n_head,
            self.head_dim
        ).transpose(1, 2)

        attention = (
            q @ k.transpose(-2, -1)
        ) / math.sqrt(self.head_dim)

        attention = attention.masked_fill(
            self.mask[:, :, :T, :T] == 0,
            float("-inf")
        )

        attention = F.softmax(
            attention,
            dim=-1
        )

        attention = self.dropout(
            attention
        )

        out = attention @ v

        out = out.transpose(
            1, 2
        ).contiguous().view(
            B,
            T,
            C
        )

        return self.proj(out)


# ============================================================
# 8. TRANSFORMER BLOCK
# ============================================================

class TransformerBlock(nn.Module):

    def __init__(self):

        super().__init__()

        self.ln1 = nn.LayerNorm(
            EMBED_SIZE
        )

        self.attention = CausalSelfAttention(
            EMBED_SIZE,
            N_HEAD
        )

        self.ln2 = nn.LayerNorm(
            EMBED_SIZE
        )

        self.ff = nn.Sequential(

            nn.Linear(
                EMBED_SIZE,
                EMBED_SIZE * 4
            ),

            nn.GELU(),

            nn.Linear(
                EMBED_SIZE * 4,
                EMBED_SIZE
            ),

            nn.Dropout(DROPOUT)
        )

    def forward(self, x):

        x = x + self.attention(
            self.ln1(x)
        )

        x = x + self.ff(
            self.ln2(x)
        )

        return x


# ============================================================
# 9. TALKING BRAIN
# ============================================================

class AdvancedTalkingBrain(nn.Module):

    def __init__(self):

        super().__init__()

        self.token_embedding = nn.Embedding(
            vocab_size,
            EMBED_SIZE
        )

        self.position_embedding = nn.Embedding(
            CONTEXT,
            EMBED_SIZE
        )

        self.blocks = nn.ModuleList([
            TransformerBlock()
            for _ in range(N_LAYER)
        ])

        self.ln_final = nn.LayerNorm(
            EMBED_SIZE
        )

        self.output = nn.Linear(
            EMBED_SIZE,
            vocab_size,
            bias=False
        )

        # Weight tying
        self.output.weight = (
            self.token_embedding.weight
        )

    def forward(self, idx, targets=None):

        B, T = idx.shape

        positions = torch.arange(
            T,
            device=idx.device
        )

        x = (
            self.token_embedding(idx)
            +
            self.position_embedding(
                positions
            )
        )

        for block in self.blocks:
            x = block(x)

        x = self.ln_final(x)

        logits = self.output(x)

        loss = None

        if targets is not None:

            loss = F.cross_entropy(
                logits.reshape(
                    -1,
                    vocab_size
                ),
                targets.reshape(-1)
            )

        return logits, loss


# ============================================================
# 10. CREATE MODEL
# ============================================================

model = AdvancedTalkingBrain().to(device)

parameters = sum(
    p.numel()
    for p in model.parameters()
)

print(
    "Model parameters:",
    f"{parameters:,}"
)


# ============================================================
# 11. OPTIMIZER
# ============================================================

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=0.01
)


# ============================================================
# 12. LOSS EVALUATION
# ============================================================

@torch.no_grad()
def estimate_loss():

    model.eval()

    results = {}

    for name, source in [
        ("train", train_data),
        ("val", val_data)
    ]:

        losses = []

        for _ in range(EVAL_BATCHES):

            x, y = get_batch(source)

            _, loss = model(
                x,
                y
            )

            losses.append(
                loss.item()
            )

        results[name] = sum(losses) / len(losses)

    model.train()

    return results


# ============================================================
# 13. GENERATION
# ============================================================

@torch.no_grad()
def generate(
    prompt,
    max_new_tokens=400,
    temperature=TEMPERATURE
):

    model.eval()

    ids = [
        letter_to_number[ch]
        for ch in prompt
        if ch in letter_to_number
    ]

    if not ids:
        ids = [0]

    idx = torch.tensor(
        [ids],
        dtype=torch.long,
        device=device
    )

    for _ in range(max_new_tokens):

        context = idx[:, -CONTEXT:]

        logits, _ = model(context)

        logits = logits[:, -1, :]

        logits = logits / temperature

        probabilities = F.softmax(
            logits,
            dim=-1
        )

        next_token = torch.multinomial(
            probabilities,
            num_samples=1
        )

        idx = torch.cat(
            [idx, next_token],
            dim=1
        )

    result = decode(
        idx[0].tolist()
    )

    model.train()

    return result


# ============================================================
# 14. TRAINING
# ============================================================

print()
print("========================================")
print(" STARTING ADVANCED TALKING BRAIN TRAINING")
print("========================================")

for step in range(1, MAX_STEPS + 1):

    x, y = get_batch(train_data)

    logits, loss = model(
        x,
        y
    )

    optimizer.zero_grad(
        set_to_none=True
    )

    loss.backward()

    torch.nn.utils.clip_grad_norm_(
        model.parameters(),
        1.0
    )

    optimizer.step()

    if step == 1 or step % EVAL_INTERVAL == 0:

        losses = estimate_loss()

        print(
            f"step {step:6d} | "
            f"train {losses['train']:.4f} | "
            f"val {losses['val']:.4f}"
        )


# ============================================================
# 15. SAVE
# ============================================================

checkpoint = {

    "state_dict":
        model.state_dict(),

    "letters":
        letters,

    "context":
        CONTEXT,

    "embed_size":
        EMBED_SIZE,

    "n_head":
        N_HEAD,

    "n_layer":
        N_LAYER,

    "dropout":
        DROPOUT,

    "model_type":
        "VALE_ADVANCED_TALKING_BRAIN",

    "version":
        "0.1",

}


torch.save(
    checkpoint,
    OUTPUT_FILE
)


print()
print("========================================")
print(" TRAINING COMPLETE")
print("========================================")
print("Saved:", OUTPUT_FILE)
print(
    "Size:",
    OUTPUT_FILE.stat().st_size,
    "bytes"
          )
