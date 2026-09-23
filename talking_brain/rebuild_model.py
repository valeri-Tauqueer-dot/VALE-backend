from pathlib import Path

BASE = Path(__file__).resolve().parent

part1 = BASE / "transformer_brain.part1"
part2 = BASE / "transformer_brain.part2"
output = BASE / "transformer_brain.pt"

if not part1.exists():
    raise FileNotFoundError(f"Missing: {part1}")

if not part2.exists():
    raise FileNotFoundError(f"Missing: {part2}")

with open(output, "wb") as out:
    with open(part1, "rb") as f:
        while chunk := f.read(1024 * 1024):
            out.write(chunk)

    with open(part2, "rb") as f:
        while chunk := f.read(1024 * 1024):
            out.write(chunk)

print(f"Rebuilt: {output}")
print(f"Size: {output.stat().st_size:,} bytes")
