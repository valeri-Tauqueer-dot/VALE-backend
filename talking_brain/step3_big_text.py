# =====================================================================
# STEP 3 - BIG TEXT: the brain practices on MILLIONS of letters
# =====================================================================
#
# In Step 2 the brain had only thousands of letters. When it practiced
# too long, it MEMORIZED the text (the test loss went up).
#
# Now the brain gets MILLIONS of letters. It cannot memorize all of them,
# so it must learn patterns. Now, MORE PRACTICE = SMARTER BRAIN.
#
# What is new here:
#   1. It reads BIG files (millions of letters) without problems.
#   2. The brain is bigger (more knobs), so it can learn more.
#   3. A stop clock. It stops after MAX_MINUTES and saves the brain.
#   4. Some examples in every round come from your SMALL files (like your
#      questions and answers), so the brain does not forget them.
#
# The practice is the same as Step 2: guess, check, find, turn.
# We reuse the code from step2_learn_by_practice.py.
# Both files must be in the same folder.
#
# You need big text files in the "data" folder. Run get_text.py first.
#
# How to run:   python step3_big_text.py
# The brain is saved in brain.npz. use_saved_brain.py can use it.
# =====================================================================

import glob
import os
import time
import unicodedata

import numpy as np

# The practice code from Step 2. We do not copy it.
from step2_learn_by_practice import (
    check, find_knobs, guess, make_brain, save_brain, turn_knobs, write,
)

# ---------------------------------------------------------------------
# SETTINGS - change these and run again to see what happens
# ---------------------------------------------------------------------

CONTEXT = 8          # how many letters the brain looks back at
EMBED_SIZE = 16      # each letter becomes a list of this many numbers
HIDDEN_SIZE = 512    # how many "thinking cells" are in the middle
BATCH_SIZE = 128     # how many examples the brain sees in one round
LEARNING_RATE = 0.1  # how big each knob turn is

STEPS = 200000       # how many rounds of practice
MAX_MINUTES = 25     # stop after this many minutes, even if the rounds are not done

# Files with fewer letters than this are "small files" (your own text).
SMALL_FILE_LETTERS = 100000
# How many examples out of every 100 come from the small files.
SMALL_SHARE = 0.15

TEMPERATURE = 0.7    # for writing: lower = safer text, higher = wilder text
LENGTH = 500
SHOW_EVERY = 5000    # show the loss every this many rounds

SEED = 1
SAVE_FILE = "brain.npz"

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(HERE, "data")


def clean(text):
    """Keep only plain letters and signs (ASCII). Turns e-with-accent into e."""
    text = unicodedata.normalize("NFKD", text)
    return text.encode("ascii", "ignore").decode("ascii")


def read_files():
    """Read every .txt file. Sort them into BIG files and SMALL files."""
    paths = sorted(glob.glob(os.path.join(DATA_FOLDER, "*.txt")))
    if not paths:
        print("I cannot find any .txt file in this folder:")
        print("   " + DATA_FOLDER)
        raise SystemExit
    big_parts = []
    small_parts = []
    for path in paths:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = clean(f.read())
        kind = "small" if len(text) < SMALL_FILE_LETTERS else "BIG"
        print(f"Read: {os.path.basename(path):24s} {len(text):9,d} letters   ({kind})")
        if kind == "small":
            small_parts.append(text)
        else:
            big_parts.append(text)
    big = "\n\n".join(big_parts)
    small = "\n\n".join(small_parts)
    if not big:            # no big files: treat everything as the main text
        big, small = small, ""
    return big, small


def take_examples(numbers, context, how_many, rng):
    """Pick random places in the text. Each place gives one example."""
    start = rng.integers(0, len(numbers) - context, how_many)
    X = numbers[start[:, None] + np.arange(context)]   # the letters before
    Y = numbers[start + context]                       # the letter that came next
    return X, Y


def split_test(numbers):
    """Keep the last 5% of the text secret, as a TEST."""
    cut = int(len(numbers) * 0.95)
    return numbers[:cut], numbers[cut:]


def main():
    rng = np.random.default_rng(SEED)

    big_text, small_text = read_files()
    print()
    print(f"Big text: {len(big_text):,d} letters.   Small files: {len(small_text):,d} letters.")

    # Letters -> numbers (fast way).
    letters = sorted(set(big_text + small_text))
    letter_to_number = {ch: i for i, ch in enumerate(letters)}
    number_to_letter = {i: ch for ch, i in letter_to_number.items()}
    table = np.zeros(256, dtype=np.int64)
    for ch, i in letter_to_number.items():
        table[ord(ch)] = i

    def to_numbers(text):
        return table[np.frombuffer(text.encode("ascii"), dtype=np.uint8)]

    big_practice, big_test = split_test(to_numbers(big_text))
    use_small = len(small_text) > 4 * CONTEXT
    if use_small:
        small_practice, small_test = split_test(to_numbers(small_text))
    small_share = SMALL_SHARE if use_small else 0.0
    print("The brain knows " + str(len(letters)) + " different letters and signs.")

    # The brain. We use small numbers (float32) so it is faster.
    brain = make_brain(len(letters), CONTEXT, EMBED_SIZE, HIDDEN_SIZE, rng)
    brain = {name: knob.astype(np.float32) for name, knob in brain.items()}
    print("The brain has " + str(sum(k.size for k in brain.values())) + " knobs.")
    print()

    # Fixed examples, to measure the loss again and again in the same way.
    X_big, Y_big = take_examples(big_test, CONTEXT, 20000, rng)
    X_pra, Y_pra = take_examples(big_practice, CONTEXT, 20000, rng)
    if use_small:
        X_small, Y_small = take_examples(small_test, CONTEXT, 5000, rng)

    print("Loss = how wrong the brain is. Lower is better.")
    print("practice = text it practices on.   test = text it never practiced on.")
    print("Stop clock: " + str(MAX_MINUTES) + " minutes.")
    print()

    start_time = time.time()
    max_seconds = MAX_MINUTES * 60
    step = 0
    while True:
        elapsed = time.time() - start_time
        progress = max(step / STEPS, elapsed / max_seconds)   # 0 = start, 1 = end

        if step % SHOW_EVERY == 0 or progress >= 1:
            line = f"round {step:7d}   practice {check(guess(brain, X_pra)[0], Y_pra):.2f}"
            line += f"   test {check(guess(brain, X_big)[0], Y_big):.2f}"
            if use_small:
                line += f"   test on your small files {check(guess(brain, X_small)[0], Y_small):.2f}"
            line += f"   ({elapsed / 60:.1f} min)"
            print(line, flush=True)
        if progress >= 1:
            break

        # Take examples: most from the big text, some from your small files.
        n_small = int(BATCH_SIZE * small_share)
        X, Y = take_examples(big_practice, CONTEXT, BATCH_SIZE - n_small, rng)
        if n_small:
            Xs, Ys = take_examples(small_practice, CONTEXT, n_small, rng)
            X = np.concatenate([X, Xs])
            Y = np.concatenate([Y, Ys])

        # The parts of practice (same as Step 2).
        chances, flat, middle = guess(brain, X)                  # 1. GUESS
        # 2. CHECK: find_knobs() starts from how wrong the guess was.
        d = find_knobs(brain, X, Y, chances, flat, middle)       # 3. FIND
        # In the last 30% we turn the knobs less, so they settle down.
        learning_rate = LEARNING_RATE if progress < 0.7 else LEARNING_RATE / 10
        turn_knobs(brain, d, learning_rate)                      # 4. TURN
        step += 1

    print()
    print(f"Practice took {(time.time() - start_time) / 60:.1f} minutes ({step:,d} rounds).")

    # Save the brain. We save it with normal numbers (float64).
    if SAVE_FILE:
        save_path = os.path.join(HERE, SAVE_FILE)
        brain64 = {name: knob.astype(np.float64) for name, knob in brain.items()}
        save_brain(brain64, letters, CONTEXT, save_path)
        print("Saved the brain in this file (" + str(round(os.path.getsize(save_path) / 1024))
              + " KB):")
        print("   " + save_path)
    print()

    print("----------- The brain writes (start: The market) -----------")
    print(write(brain, "The market", LENGTH, CONTEXT, letter_to_number,
                number_to_letter, TEMPERATURE, rng))
    print("------------------------------------------------------------")
    print()
    print("----------- The brain writes (start: a question) -----------")
    print(write(brain, "Q: What is a stop loss?\nA:", LENGTH, CONTEXT, letter_to_number,
                number_to_letter, TEMPERATURE, rng))
    print("------------------------------------------------------------")


if __name__ == "__main__":
    main()
