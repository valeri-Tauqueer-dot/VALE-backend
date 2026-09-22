# =====================================================================
# USE THE SAVED TRANSFORMER - no practice, only writing
# =====================================================================
#
# This loads the brain that step4_transformer.py saved, and writes text.
# There is no practice here, so it works even without a GPU.
#
# You need the file transformer_brain.pt in this same folder.
# Run step4_transformer.py first. It makes that file.
#
# How to run:   python use_transformer.py
# =====================================================================

import os

try:
    import torch
except ImportError:
    print("This step needs PyTorch. Google Colab already has it.")
    print("If you see this message, run this first:   !pip install torch")
    raise SystemExit

# We reuse the brain's design and the writing job from Step 4.
from step4_transformer import TalkingBrain, write_text

# ---------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------

START_TEXT = "The market"
LENGTH = 500
TEMPERATURE = 0.8    # lower = safer text, higher = wilder text

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN_FILE = os.path.join(HERE, "transformer_brain.pt")


def main():
    if not os.path.exists(BRAIN_FILE):
        print("I cannot find the brain file:")
        print("   " + BRAIN_FILE)
        print("Run step4_transformer.py first. It makes transformer_brain.pt.")
        print("Then put that file in this folder.")
        raise SystemExit

    device = "cuda" if torch.cuda.is_available() else "cpu"
    saved = torch.load(BRAIN_FILE, map_location=device)

    letters = saved["letters"]
    letter_to_number = {ch: i for i, ch in enumerate(letters)}

    model = TalkingBrain(
        len(letters), saved["context"], saved["embed_size"],
        saved["n_head"], saved["n_layer"], saved["dropout"],
    ).to(device)
    model.load_state_dict(saved["state_dict"])
    model.eval()

    n_params = sum(p.numel() for p in model.parameters())
    print("Loaded the brain. It has " + f"{n_params:,d}" + " knobs, it knows "
          + str(len(letters)) + " letters and signs,")
    print("and it looks back " + str(saved["context"]) + " letters. It did NOT practice again.")
    print()

    print("----------- The brain writes -----------")
    print(write_text(model, START_TEXT, LENGTH, saved["context"], letter_to_number,
                      letters, TEMPERATURE, device))
    print("----------------------------------------")


if __name__ == "__main__":
    main()
