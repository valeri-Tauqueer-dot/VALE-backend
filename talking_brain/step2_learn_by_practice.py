# =====================================================================
# STEP 2 - The brain learns by PRACTICE (a small neural network)
# =====================================================================
#
# In Step 1 the brain only COUNTED. It never practiced.
# In Step 2 the brain PRACTICES, like a student.
#
# Think of a radio with many small knobs:
#   - At the start, the knobs are set in a random way. We hear only noise.
#   - We turn each knob a tiny bit and listen again. Is it better?
#   - We do this thousands of times. Slowly the sound becomes clear.
#
# The knobs are just numbers inside the brain. They are called WEIGHTS.
# The "how bad is the noise" number is called the LOSS.
# Lower loss = better brain.
#
# One round of practice has 4 parts:
#   1. GUESS  - the brain sees some letters and guesses the next letter.
#   2. CHECK  - we measure how wrong the guess was. This is the loss.
#   3. FIND   - we find which knobs to turn, and in which direction.
#   4. TURN   - we turn the knobs a tiny bit.
# Then we repeat. This whole thing is called TRAINING.
#
# MORE TEXT = SMARTER BRAIN.
# This step reads EVERY .txt file inside the "data" folder.
# Add more .txt files there, run again, and the brain learns from all.
#
# SAVING: at the end, the brain is saved in a file called brain.npz.
# That file holds what the brain learned. You can use it later without
# practice. See the file use_saved_brain.py.
#
# This step needs numpy. Google Colab already has it.
# How to run:   python step2_learn_by_practice.py
# =====================================================================

import glob
import os
import time

import numpy as np

# ---------------------------------------------------------------------
# SETTINGS - change these and run again to see what happens
# ---------------------------------------------------------------------

CONTEXT = 5          # how many letters the brain looks back at
EMBED_SIZE = 10      # each letter becomes a small list of this many numbers
HIDDEN_SIZE = 200    # how many "thinking cells" are in the middle
STEPS = 6000         # how many rounds of practice
BATCH_SIZE = 64      # how many examples the brain sees in one round
LEARNING_RATE = 0.1  # how big each knob turn is (too big = wild, too small = slow)

TEMPERATURE = 1.0    # for writing: lower = safer text, higher = wilder text
START_TEXT = "The market"
LENGTH = 500

# After practice, the brain is saved in this file (in the same folder as this script).
# The file holds the knobs. Without it, the brain forgets everything.
SAVE_FILE = "brain.npz"

# Use a number (like 1) to get the same result every time.
# Use None to get a different result every time.
SEED = 1

# ---------------------------------------------------------------------
# WHERE THE TEXT FILES ARE
# ---------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(HERE, "data")


def read_all_text():
    """Read every .txt file in the data folder and join them."""
    files = sorted(glob.glob(os.path.join(DATA_FOLDER, "*.txt")))
    if not files:
        print("I cannot find any .txt file in this folder:")
        print("   " + DATA_FOLDER)
        raise SystemExit
    parts = []
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            parts.append(f.read())
        print("Read: " + os.path.basename(path))
    return "\n\n".join(parts)


# ---------------------------------------------------------------------
# PART A - Turn letters into numbers (a computer only understands numbers)
# ---------------------------------------------------------------------

def make_examples(numbers, context):
    """
    Make practice examples.
    Each example is: some letters (X) and the letter that came next (Y).
    """
    X = []
    Y = []
    for i in range(context, len(numbers)):
        X.append(numbers[i - context : i])
        Y.append(numbers[i])
    return np.array(X), np.array(Y)


# ---------------------------------------------------------------------
# PART B - The brain (the knobs)
# ---------------------------------------------------------------------

def make_brain(vocab_size, context, embed_size, hidden_size, rng):
    """
    Make the knobs. At the start they are random, so the brain knows nothing.

    C  : a small list of numbers for each letter
    W1 : knobs between the letters and the middle cells
    W2 : knobs between the middle cells and the answer
    b1, b2 : small extra knobs
    """
    size_in = context * embed_size
    brain = {}
    brain["C"] = rng.standard_normal((vocab_size, embed_size))
    brain["W1"] = rng.standard_normal((size_in, hidden_size)) / np.sqrt(size_in)
    brain["b1"] = np.zeros(hidden_size)
    brain["W2"] = rng.standard_normal((hidden_size, vocab_size)) * 0.01
    brain["b2"] = np.zeros(vocab_size)
    return brain


def count_knobs(brain):
    return sum(knob.size for knob in brain.values())


def softmax(scores):
    """Turn scores into chances that add up to 1 (like 70%, 20%, 10%)."""
    scores = scores - scores.max(axis=-1, keepdims=True)   # keeps numbers safe
    hot = np.exp(scores)
    return hot / hot.sum(axis=-1, keepdims=True)


# ---------------------------------------------------------------------
# PART C - Practice
# ---------------------------------------------------------------------

def guess(brain, X):
    """
    Practice part 1: GUESS.
    Send letters through the brain. Get a chance for every possible next letter.
    """
    letters = brain["C"][X]                         # letters -> numbers
    flat = letters.reshape(X.shape[0], -1)          # put them in one long line
    middle = np.tanh(flat @ brain["W1"] + brain["b1"])   # the thinking cells
    scores = middle @ brain["W2"] + brain["b2"]     # one score per letter
    chances = softmax(scores)
    return chances, flat, middle


def check(chances, Y):
    """
    Practice part 2: CHECK.
    How much chance did the brain give to the RIGHT letter?
    A small chance = a big loss. A big chance = a small loss.
    """
    right = chances[np.arange(len(Y)), Y]
    return -np.log(right + 1e-12).mean()


def find_knobs(brain, X, Y, chances, flat, middle):
    """
    Practice part 3: FIND which knobs to turn.
    This is the math part (it is called backpropagation).
    You can skip reading it for now. Later we will use a tool called PyTorch,
    and it does this part for us.
    """
    batch = len(Y)

    # How wrong was each score?
    d_scores = chances.copy()
    d_scores[np.arange(batch), Y] -= 1
    d_scores /= batch

    # Go backward through the brain, one layer at a time.
    d = {}
    d["W2"] = middle.T @ d_scores
    d["b2"] = d_scores.sum(axis=0)

    d_middle = d_scores @ brain["W2"].T
    d_before_tanh = d_middle * (1 - middle ** 2)
    d["W1"] = flat.T @ d_before_tanh
    d["b1"] = d_before_tanh.sum(axis=0)

    d_flat = d_before_tanh @ brain["W1"].T
    d_letters = d_flat.reshape(X.shape[0], X.shape[1], -1)
    d["C"] = np.zeros_like(brain["C"])
    np.add.at(d["C"], X, d_letters)
    return d


def turn_knobs(brain, d, learning_rate):
    """Practice part 4: TURN each knob a tiny bit."""
    for name in brain:
        brain[name] -= learning_rate * d[name]


# ---------------------------------------------------------------------
# PART D - Save the brain
# ---------------------------------------------------------------------

def save_brain(brain, letters, context, path):
    """
    Save the knobs, and the list of letters the brain knows, in one file.
    Later, another program can load this file and use the brain.
    The brain does not need to practice again.
    """
    np.savez(
        path,
        C=brain["C"], W1=brain["W1"], b1=brain["b1"],
        W2=brain["W2"], b2=brain["b2"],
        letters=np.array(letters),
        context=np.array(context),
    )


# ---------------------------------------------------------------------
# PART E - Write text with the trained brain
# ---------------------------------------------------------------------

def write(brain, start, length, context, letter_to_number, number_to_letter,
          temperature, rng):
    text = start
    space = letter_to_number.get(" ", 0)
    temperature = max(temperature, 0.05)
    while len(text) < length:
        recent = text[-context:]
        numbers = [letter_to_number.get(ch, space) for ch in recent]
        numbers = [space] * (context - len(numbers)) + numbers
        X = np.array([numbers])

        letters = brain["C"][X].reshape(1, -1)
        middle = np.tanh(letters @ brain["W1"] + brain["b1"])
        scores = (middle @ brain["W2"] + brain["b2"])[0]
        chances = softmax(scores / temperature)

        next_number = rng.choice(len(chances), p=chances)
        text += number_to_letter[next_number]
    return text


def main():
    rng = np.random.default_rng(SEED)

    text = read_all_text()
    print("The brain read " + str(len(text)) + " letters.")

    # Letters -> numbers
    letters = sorted(set(text))
    letter_to_number = {ch: i for i, ch in enumerate(letters)}
    number_to_letter = {i: ch for ch, i in letter_to_number.items()}
    numbers = [letter_to_number[ch] for ch in text]
    print("The brain knows " + str(len(letters)) + " different letters and signs.")

    # Practice examples. We keep the last 10% secret, as a TEST.
    # If the brain does well on text it never practiced on, it really learned.
    X, Y = make_examples(numbers, CONTEXT)
    cut = int(len(X) * 0.9)
    X_practice, Y_practice = X[:cut], Y[:cut]
    X_test, Y_test = X[cut:], Y[cut:]
    print("Practice examples: " + str(len(X_practice)) + "   Test examples: " + str(len(X_test)))

    brain = make_brain(len(letters), CONTEXT, EMBED_SIZE, HIDDEN_SIZE, rng)
    print("The brain has " + str(count_knobs(brain)) + " knobs.")
    print()
    print("Loss = how wrong the brain is. Lower is better.")
    print("At the start, the loss is about " + str(round(float(np.log(len(letters))), 2))
          + ". That means the brain is only guessing.")
    print()

    # Let the brain write BEFORE practice. The knobs are random, so it is noise.
    print("----- Before practice (the knobs are random) -----")
    print(write(brain, START_TEXT, 150, CONTEXT, letter_to_number,
                number_to_letter, TEMPERATURE, rng))
    print("--------------------------------------------------")
    print()

    start_time = time.time()
    for step in range(STEPS + 1):
        # Show the loss now and then.
        # This is part 2, CHECK, done on all the examples.
        if step % 500 == 0:
            practice_loss = check(guess(brain, X_practice)[0], Y_practice)
            test_loss = check(guess(brain, X_test)[0], Y_test)
            print(f"round {step:5d}   practice loss {practice_loss:.2f}   test loss {test_loss:.2f}")
        if step == STEPS:
            break

        # Take a few random examples.
        pick = rng.integers(0, len(X_practice), BATCH_SIZE)
        xb, yb = X_practice[pick], Y_practice[pick]

        # The parts of practice.
        chances, flat, middle = guess(brain, xb)                 # 1. GUESS
        # 2. CHECK: find_knobs() starts from how wrong the guess was.
        d = find_knobs(brain, xb, yb, chances, flat, middle)     # 3. FIND
        # At the end we turn the knobs less, so they settle down.
        learning_rate = LEARNING_RATE if step < STEPS * 0.7 else LEARNING_RATE / 10
        turn_knobs(brain, d, learning_rate)                      # 4. TURN

    print()
    print("Practice took " + str(round(time.time() - start_time, 1)) + " seconds.")

    # Save the brain, so it is not forgotten when the program ends.
    if SAVE_FILE:
        save_path = os.path.join(HERE, SAVE_FILE)
        save_brain(brain, letters, CONTEXT, save_path)
        size_kb = round(os.path.getsize(save_path) / 1024)
        print("Saved the brain in this file (" + str(size_kb) + " KB):")
        print("   " + save_path)
    print()

    print("----------- After practice: the brain writes -----------")
    print(write(brain, START_TEXT, LENGTH, CONTEXT, letter_to_number,
                number_to_letter, TEMPERATURE, rng))
    print("--------------------------------------------------------")


if __name__ == "__main__":
    main()
