# =====================================================================
# USE THE SAVED BRAIN - no practice, only writing
# =====================================================================
#
# This is what VALE (on Render) will do later:
#   1. Load the brain file (the knobs that Colab learned).
#   2. Write text.
#
# There is NO practice here. So it is fast, and a small server can do it.
#
# You need the file brain.npz in this same folder.
# Step 2 makes that file (run step2_learn_by_practice.py).
#
# How to run:   python use_saved_brain.py
# =====================================================================

import os

import numpy as np

# We reuse the writing job from Step 2. We do not copy it.
from step2_learn_by_practice import write

# ---------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------

START_TEXT = "The market"
LENGTH = 500
TEMPERATURE = 1.0    # lower = safer text, higher = wilder text
SEED = None          # None = different text every time

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN_FILE = os.path.join(HERE, "brain.npz")


def load_brain(path):
    """Read the brain file. Returns the knobs, the letters, and the context."""
    data = np.load(path)
    brain = {}
    for name in ["C", "W1", "b1", "W2", "b2"]:
        brain[name] = data[name]
    letters = [str(ch) for ch in data["letters"]]
    context = int(data["context"])
    return brain, letters, context


def main():
    if not os.path.exists(BRAIN_FILE):
        print("I cannot find the brain file:")
        print("   " + BRAIN_FILE)
        print("Run step2_learn_by_practice.py first. It makes brain.npz.")
        print("Then put brain.npz in this folder.")
        raise SystemExit

    brain, letters, context = load_brain(BRAIN_FILE)
    knobs = sum(knob.size for knob in brain.values())
    print("Loaded the brain. It has " + str(knobs) + " knobs, it knows "
          + str(len(letters)) + " letters and signs,")
    print("and it looks back " + str(context) + " letters. It did NOT practice again.")
    print()

    letter_to_number = {ch: i for i, ch in enumerate(letters)}
    number_to_letter = {i: ch for ch, i in letter_to_number.items()}
    rng = np.random.default_rng(SEED)

    print("----------- The brain writes -----------")
    print(write(brain, START_TEXT, LENGTH, context, letter_to_number,
                number_to_letter, TEMPERATURE, rng))
    print("----------------------------------------")


if __name__ == "__main__":
    main()
