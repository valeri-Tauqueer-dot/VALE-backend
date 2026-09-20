# =====================================================================
# STEP 1 - A very small talking brain that learns LETTERS
# =====================================================================
#
# The big idea (every talking brain, small or big, does this):
#
#       It guesses the NEXT piece of text.
#
# In this step the "piece" is one letter, and the brain learns by
# COUNTING. There is no hard math and no library to install.
#
#   1. Read a text file.
#   2. Learn: "after these letters, which letter comes next?"
#   3. Write new text, one letter at a time.
#
# How to run:   python step1_letter_model.py
# (on some computers you must write:   python3 step1_letter_model.py)
# =====================================================================

import os
import random

# ---------------------------------------------------------------------
# SETTINGS - change these and run again to see what happens
# ---------------------------------------------------------------------

# How many letters the brain looks back at before it guesses the next one.
# Try 1, 2, 3, 4, 5, 6, 8 and see how the text changes.
CONTEXT = 3

# How many letters the brain should write.
LENGTH = 500

# The brain starts writing from this text.
START_TEXT = "The market"

# Use a number (like 42) to get the same text every time.
# Use None to get different text every time.
SEED = None

# ---------------------------------------------------------------------
# WHERE THE TEXT FILE IS
# ---------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, "data", "sample.txt")


def read_text(path):
    """Read the whole text file."""
    if not os.path.exists(path):
        print("I cannot find the text file.")
        print("Please put a text file here:")
        print("   " + path)
        raise SystemExit
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def learn(text, context):
    """
    LEARNING = COUNTING.
    Look at every group of letters in the text, and count which letter
    came right after it.

    Example: after "mar" the letter "k" came 5 times, "g" came 2 times.
        table["mar"] = {"k": 5, "g": 2}
    """
    table = {}
    for i in range(len(text) - context):
        before = text[i : i + context]   # the group of letters
        after = text[i + context]        # the letter that came next
        if before not in table:
            table[before] = {}
        table[before][after] = table[before].get(after, 0) + 1
    return table


def pick_next(table, before):
    """
    Pick the next letter.
    A letter that was seen MORE often is picked MORE often.
    If the brain never saw these letters, it returns None.
    """
    counts = table.get(before)
    if not counts:
        return None
    letters = list(counts.keys())
    weights = list(counts.values())
    return random.choices(letters, weights=weights)[0]


def write(table, start, context, length):
    """Write new text, one letter at a time."""
    text = start
    while len(text) < length:
        before = text[-context:]           # the last few letters
        nxt = pick_next(table, before)
        if nxt is None:
            # The brain never saw these letters. It is lost.
            # So it jumps to a random group of letters it knows.
            before = random.choice(list(table.keys()))
            text = text + " " + before
            continue
        text = text + nxt
    return text


def look_at(table, letters):
    """Show what the brain learned about one group of letters."""
    counts = table.get(letters)
    print('After "' + letters + '" the brain saw these letters:')
    if not counts:
        print("   (nothing - the brain never saw this group)")
        return
    total = sum(counts.values())
    # Show the most common letters first.
    for letter, n in sorted(counts.items(), key=lambda item: -item[1]):
        percent = n * 100 // total
        word = "time" if n == 1 else "times"
        # repr() shows spaces and new lines in a way we can see.
        print("   " + repr(letter) + "   " + str(n) + " " + word
              + "   (" + str(percent) + "%)")


def main():
    if SEED is not None:
        random.seed(SEED)

    text = read_text(DATA_FILE)
    print("The brain read " + str(len(text)) + " letters.")

    table = learn(text, CONTEXT)
    print("The brain learned " + str(len(table)) + " different groups of "
          + str(CONTEXT) + " letters.")
    print()

    look_at(table, START_TEXT[-CONTEXT:])
    print()

    print("----------- The brain writes -----------")
    print(write(table, START_TEXT, CONTEXT, LENGTH))
    print("----------------------------------------")


if __name__ == "__main__":
    main()
