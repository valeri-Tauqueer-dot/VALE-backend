from __future__ import annotations

import os
import torch

from step4_transformer import TalkingBrain


class TalkingBrainConnector:
    def __init__(self, model_path: str):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        checkpoint = torch.load(
            model_path,
            map_location=self.device,
            weights_only=False,
        )

        self.model = TalkingBrain(
            vocab_size=len(checkpoint["letters"]),
            context=checkpoint["context"],
            embed_size=checkpoint["embed_size"],
            n_head=checkpoint["n_head"],
            n_layer=checkpoint["n_layer"],
            dropout=checkpoint["dropout"],
        )

        self.model.load_state_dict(checkpoint["state_dict"])
        self.model.to(self.device)
        self.model.eval()

        self.letters = checkpoint["letters"]
        self.stoi = {c: i for i, c in enumerate(self.letters)}
        self.itos = {i: c for i, c in enumerate(self.letters)}

    @torch.no_grad()
    def respond(self, user_message: str, brain_result: str, max_new_tokens: int = 300):
        prompt = (
            "USER: " + user_message +
            "\nVALE BRAIN RESULT: " + brain_result +
            "\nASSISTANT:"
        )

        ids = [
            self.stoi[c]
            for c in prompt
            if c in self.stoi
        ]

        ids = ids[-self.model.context:]

        x = torch.tensor([ids], dtype=torch.long, device=self.device)

        generated = ""

        for _ in range(max_new_tokens):
            x_cond = x[:, -self.model.context:]

            output = self.model(x_cond)
            logits = output[0]

            next_id = torch.argmax(logits[:, -1, :], dim=-1).item()

            x = torch.cat(
                [x, torch.tensor([[next_id]], device=self.device)],
                dim=1,
            )

            char = self.itos[next_id]
            generated += char

            if generated.endswith("\nUSER:"):
                generated = generated[:-6]
                break

        return generated.strip()
