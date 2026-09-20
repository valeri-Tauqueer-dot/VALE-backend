# Talking Brain

This is my own "talking brain" for VALE.

A talking brain is the part of an AI that **writes words**.
I am building a small one myself, step by step, to learn how it works.

This is a learning project. It is not for business.

## The one big idea

A talking brain does one simple thing:

> It guesses the **next piece of text**.

You give it some text. It guesses what comes next.
Then it guesses the next one, and the next one. That is how it writes.

Big AIs (like ChatGPT and Claude) do the same thing.
They are just much, much better at guessing.

## What makes it smarter?

It is **not** the size of the code files.

1. **More text to learn from.** This helps the most.
2. **A bigger brain.** More "memory" inside the model.
3. **More time learning.** This is called training.

The code stays quite small.
We add a new file when we learn a new idea.

## The steps

| Step | File | What we learn |
|------|------|---------------|
| 1 | `step1_letter_model.py` | Count letters. The brain learns which letter comes next. No libraries. **(we are here)** |
| 2 | (coming) | The same idea, but with a small neural network (PyTorch). It learns instead of only counting. |
| 3 | (coming) | Words instead of letters. This is called a tokenizer. |
| 4 | (coming) | The transformer. This is the design inside big AIs. We build a mini one. |
| 5 | (coming) | Train it on more text. Save the trained brain to a file. |
| 6 | (coming) | Connect it to VALE. VALE's brains find the facts. The talking brain writes the answer. |

This plan can change while we learn.

## Step 1: how to run

You need Python. Nothing else.

```
python step1_letter_model.py
```

On some computers you must write `python3` instead of `python`.

The folder must look like this:

```
talking_brain/
    README.md
    step1_letter_model.py
    data/
        sample.txt
```

## Things to try

Open `step1_letter_model.py`. At the top there are 4 settings.

- Change `CONTEXT` to 1, 2, 3, 5, 8 and run again.
  - Very small: the text is nonsense letters.
  - Middle: the text looks like real words.
  - Very big: the brain only **copies** the text. It memorized, it did not learn.
- Change `START_TEXT` to your own words.
- Put your own text in `data/sample.txt`. More text is better.

## Honest notes

- The text it writes is often nonsense. That is normal for Step 1.
- It does not understand anything yet. It only counts letters.
- Each step will be better than the one before.
