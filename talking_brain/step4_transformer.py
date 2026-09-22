# =====================================================================
# STEP 4 - A REAL TRANSFORMER (the design inside big AIs like ChatGPT)
# =====================================================================
#
# Steps 1 to 3 used one small design, and you saw it fill up: more text
# stopped helping, because the design itself was too small.
#
# Step 4 uses a BIGGER, SMARTER design, called a TRANSFORMER.
# Two things are new:
#
#   1. PYTORCH TURNS THE KNOBS FOR US.
#      In Step 2, find_knobs() was YOU (well, me) doing the hard math by
#      hand. From now on, a tool called PyTorch does that math for us.
#      We only say what the brain looks like. PyTorch finds every knob
#      and turns it. This is called AUTOGRAD.
#
#   2. ATTENTION: the brain can look far back, and it learns WHAT MATTERS.
#      Before, the brain only looked at the last few letters, and it
#      treated them all the same. Attention lets the brain look back
#      much further (128 letters instead of 8), and for every letter it
#      is writing, it learns which of those earlier letters matter most.
#      Think of it like reading with a highlighter: attention marks the
#      important earlier words, instead of re-reading everything equally.
#
# A GPU is a special chip that turns many knobs AT THE SAME TIME, like
# many hands on the radio instead of one. This is why Step 4 needs a
# GPU, and Colab gives you one for free.
#
# BEFORE YOU RUN THIS: turn on the free GPU.
#   1. In Colab, open the "Runtime" menu at the top.
#   2. Tap "Change runtime type".
#   3. Under "Hardware accelerator", choose "T4 GPU" (or "GPU").
#   4. Tap "Save".
# This RESTARTS Colab and DELETES the files inside it. So, after this,
# clone your repo again and run get_text.py again, THEN run this file.
#
# This step still reads LETTERS, the same as Steps 1 to 3. Reading whole
# WORDS is a good idea for later, once this design is working well.
#
# How to run:   python step4_transformer.py
# The brain is saved in transformer_brain.pt.
# =====================================================================

import os
import time

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError:
    print("This step needs PyTorch. Google Colab already has it.")
    print("If you see this message, run this first:   !pip install torch")
    raise SystemExit

# We reuse the reading job from Step 3. Both files must be in this folder.
from step3_big_text import read_files

# ---------------------------------------------------------------------
# SETTINGS - change these and run again to see what happens
# ---------------------------------------------------------------------

CONTEXT = 128        # how many letters the brain looks back at (was 8 before)
EMBED_SIZE = 192     # each letter becomes a list of this many numbers
N_HEAD = 6           # how many "highlighters" read the text at once
N_LAYER = 4          # how many attention layers are stacked
DROPOUT = 0.1        # during practice, hide this share of the numbers each
                     # time, so the brain does not lean on just a few of them

BATCH_SIZE = 64      # how many pieces of text the brain sees in one round
LEARNING_RATE = 3e-4

MAX_STEPS = 6000     # how many rounds of practice, at most
MAX_MINUTES = 20     # stop after this many minutes, even if rounds remain
EVAL_EVERY = 250     # show the loss every this many rounds
EVAL_ROUNDS = 40     # how many small checks we average for one loss number

# Which files count as "small" (your own text) is decided inside
# read_files(), by SMALL_FILE_LETTERS in step3_big_text.py.
SMALL_SHARE = 0.15   # how often a round of practice comes from small files

TEMPERATURE = 0.8    # for writing: lower = safer text, higher = wilder text
LENGTH = 500

SEED = 1
SAVE_FILE = "transformer_brain.pt"

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------
# PART A - Turn letters into numbers, and make practice batches
# ---------------------------------------------------------------------

def encode_all(big_text, small_text):
    """Build the alphabet, and turn both texts into arrays of numbers."""
    letters = sorted(set(big_text + small_text))
    letter_to_number = {ch: i for i, ch in enumerate(letters)}

    table = np.zeros(256, dtype=np.int64)
    for ch, i in letter_to_number.items():
        table[ord(ch)] = i

    def to_numbers(text):
        return table[np.frombuffer(text.encode("ascii"), dtype=np.uint8)]

    return letters, letter_to_number, to_numbers(big_text), to_numbers(small_text)


def split_practice_test(numbers):
    """Keep the last 5% of the text secret, as a TEST."""
    cut = int(len(numbers) * 0.95)
    return numbers[:cut], numbers[cut:]


def get_batch(numbers, context, batch_size, rng, device):
    """
    Make one practice batch.
    X is 'context' letters in a row. Y is the SAME letters, moved one
    letter later. So Y always tells X what should come next, at every
    single position, not only at the very end.
    """
    starts = rng.integers(0, len(numbers) - context - 1, batch_size)
    positions = starts[:, None] + np.arange(context)
    X = numbers[positions]
    Y = numbers[positions + 1]
    return (torch.from_numpy(X).long().to(device),
            torch.from_numpy(Y).long().to(device))


# ---------------------------------------------------------------------
# PART B - The transformer (the brain's design)
# ---------------------------------------------------------------------

class AttentionBlock(nn.Module):
    """
    One layer of the brain. It has two parts:
      1. Attention: look back at earlier letters, and learn what matters.
      2. A small 2-step "think about it" part (the MLP), for every letter.
    Both parts have a "shortcut" around them (this is called a residual
    connection). It lets information skip a layer if that layer is not
    useful yet, which makes deep brains much easier to practice.
    """

    def __init__(self, embed_size, n_head, dropout):
        super().__init__()
        self.n_head = n_head
        self.head_size = embed_size // n_head

        self.norm1 = nn.LayerNorm(embed_size)
        self.key = nn.Linear(embed_size, embed_size)
        self.query = nn.Linear(embed_size, embed_size)
        self.value = nn.Linear(embed_size, embed_size)
        self.attn_out = nn.Linear(embed_size, embed_size)
        self.attn_dropout = dropout

        self.norm2 = nn.LayerNorm(embed_size)
        self.mlp = nn.Sequential(
            nn.Linear(embed_size, 4 * embed_size),
            nn.GELU(),
            nn.Linear(4 * embed_size, embed_size),
            nn.Dropout(dropout),
        )

    def split_heads(self, x, B, T):
        # (B, T, embed_size) -> (B, n_head, T, head_size)
        return x.view(B, T, self.n_head, self.head_size).transpose(1, 2)

    def forward(self, x):
        B, T, _ = x.shape

        # ----- 1. Attention, with a shortcut around it -----
        normed = self.norm1(x)
        q = self.split_heads(self.query(normed), B, T)
        k = self.split_heads(self.key(normed), B, T)
        v = self.split_heads(self.value(normed), B, T)

        # is_causal=True means: a letter can only look at EARLIER letters,
        # never at later ones. Without this, the brain could "cheat" by
        # peeking at the answer.
        drop = self.attn_dropout if self.training else 0.0
        attended = F.scaled_dot_product_attention(q, k, v, dropout_p=drop, is_causal=True)

        attended = attended.transpose(1, 2).contiguous().view(B, T, -1)
        x = x + self.attn_out(attended)

        # ----- 2. The "think about it" part, with a shortcut around it -----
        x = x + self.mlp(self.norm2(x))
        return x


class TalkingBrain(nn.Module):
    """The whole brain: turn letters into numbers, think in layers, guess."""

    def __init__(self, vocab_size, context, embed_size, n_head, n_layer, dropout):
        super().__init__()
        self.context = context
        self.letter_embed = nn.Embedding(vocab_size, embed_size)
        self.position_embed = nn.Embedding(context, embed_size)
        self.dropout = nn.Dropout(dropout)
        self.blocks = nn.ModuleList(
            [AttentionBlock(embed_size, n_head, dropout) for _ in range(n_layer)]
        )
        self.norm_out = nn.LayerNorm(embed_size)
        self.head = nn.Linear(embed_size, vocab_size)

    def forward(self, X, Y=None):
        B, T = X.shape
        positions = torch.arange(T, device=X.device)

        x = self.letter_embed(X) + self.position_embed(positions)
        x = self.dropout(x)
        for block in self.blocks:
            x = block(x)
        x = self.norm_out(x)
        scores = self.head(x)   # one score per possible letter, for every position

        loss = None
        if Y is not None:
            loss = F.cross_entropy(scores.view(B * T, -1), Y.view(B * T))
        return scores, loss

    @torch.no_grad()
    def write(self, start_numbers, length, temperature, device):
        """Write new letters, one at a time, using what it learned."""
        self.eval()
        ids = list(start_numbers)
        for _ in range(length):
            recent = torch.tensor([ids[-self.context:]], dtype=torch.long, device=device)
            scores, _ = self(recent)
            last_scores = scores[0, -1] / max(temperature, 0.05)
            chances = F.softmax(last_scores, dim=-1)
            next_id = torch.multinomial(chances, 1).item()
            ids.append(next_id)
        self.train()
        return ids


# ---------------------------------------------------------------------
# PART C - Practice
# ---------------------------------------------------------------------

@torch.no_grad()
def average_loss(model, numbers, context, batch_size, rounds, rng, device):
    model.eval()
    total = 0.0
    for _ in range(rounds):
        X, Y = get_batch(numbers, context, batch_size, rng, device)
        _, loss = model(X, Y)
        total += loss.item()
    model.train()
    return total / rounds


def write_text(model, start_text, length, context, letter_to_number, letters,
                temperature, device):
    space = letter_to_number.get(" ", 0)
    start_numbers = [letter_to_number.get(ch, space) for ch in start_text]
    start_numbers = [space] * max(0, context - len(start_numbers)) + start_numbers
    ids = model.write(start_numbers, length, temperature, device)
    return "".join(letters[i] for i in ids)


def main():
    rng = np.random.default_rng(SEED)
    torch.manual_seed(SEED)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        print("Using the GPU. Good, this will be fast.")
    else:
        print("No GPU found. This will be SLOW, and may not finish.")
        print("See the notes at the top of this file for how to turn one on.")
    print()

    big_text, small_text = read_files()
    letters, letter_to_number, big_numbers, small_numbers = encode_all(big_text, small_text)
    print()
    print("The brain knows " + str(len(letters)) + " different letters and signs.")

    big_practice, big_test = split_practice_test(big_numbers)
    use_small = len(small_numbers) > 4 * CONTEXT
    if use_small:
        small_practice, small_test = split_practice_test(small_numbers)
    small_share = SMALL_SHARE if use_small else 0.0

    model = TalkingBrain(len(letters), CONTEXT, EMBED_SIZE, N_HEAD, N_LAYER, DROPOUT).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print("The brain has " + f"{n_params:,d}" + " knobs.")
    print()

    print("----- Before practice (the knobs are random) -----")
    print(write_text(model, "The market", 150, CONTEXT, letter_to_number, letters,
                      TEMPERATURE, device))
    print("----------------------------------------------------")
    print()

    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)

    print("Loss = how wrong the brain is. Lower is better.")
    print("Stop clock: " + str(MAX_MINUTES) + " minutes, or " + str(MAX_STEPS) + " rounds.")
    print()

    start_time = time.time()
    max_seconds = MAX_MINUTES * 60
    step = 0
    while True:
        elapsed = time.time() - start_time
        stop = step >= MAX_STEPS or elapsed >= max_seconds

        if step % EVAL_EVERY == 0 or stop:
            practice_loss = average_loss(model, big_practice, CONTEXT, BATCH_SIZE,
                                          EVAL_ROUNDS, rng, device)
            test_loss = average_loss(model, big_test, CONTEXT, BATCH_SIZE,
                                      EVAL_ROUNDS, rng, device)
            line = f"round {step:5d}   practice {practice_loss:.2f}   test {test_loss:.2f}"
            if use_small:
                small_loss = average_loss(model, small_test, CONTEXT, BATCH_SIZE,
                                           min(EVAL_ROUNDS, 10), rng, device)
                line += f"   test on your small files {small_loss:.2f}"
            line += f"   ({elapsed / 60:.1f} min)"
            print(line, flush=True)
        if stop:
            break

        # Pick where this round's practice text comes from.
        source = small_practice if (use_small and rng.random() < small_share) else big_practice
        X, Y = get_batch(source, CONTEXT, BATCH_SIZE, rng, device)

        # The 4 parts of practice. PyTorch does part 3 (FIND) for us now.
        _, loss = model(X, Y)              # 1. GUESS   (loss is part 2, CHECK)
        optimizer.zero_grad()
        loss.backward()                    # 3. FIND, done by PyTorch (autograd)
        optimizer.step()                   # 4. TURN
        step += 1

    print()
    print(f"Practice took {(time.time() - start_time) / 60:.1f} minutes ({step:,d} rounds).")

    if SAVE_FILE:
        save_path = os.path.join(HERE, SAVE_FILE)
        torch.save({
            "state_dict": model.state_dict(),
            "letters": letters,
            "context": CONTEXT,
            "embed_size": EMBED_SIZE,
            "n_head": N_HEAD,
            "n_layer": N_LAYER,
            "dropout": DROPOUT,
        }, save_path)
        size_mb = round(os.path.getsize(save_path) / (1024 * 1024), 1)
        print(f"Saved the brain in this file ({size_mb} MB):")
        print("   " + save_path)
    print()

    print("----------- After practice: the brain writes -----------")
    print(write_text(model, "The market", LENGTH, CONTEXT, letter_to_number, letters,
                      TEMPERATURE, device))
    print("----------------------------------------------------------")
    print()
    print("----------- After practice: a question -----------")
    print(write_text(model, "Q: What is a stop loss?\nA:", LENGTH, CONTEXT,
                      letter_to_number, letters, TEMPERATURE, device))
    print("----------------------------------------------------")


if __name__ == "__main__":
    main()
