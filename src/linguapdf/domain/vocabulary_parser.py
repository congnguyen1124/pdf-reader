from __future__ import annotations

import csv
import io
import re


def parse_vocabulary(text: str, english_first: bool = True) -> tuple[list[tuple[str, str]], list[str]]:
    """Parse one bilingual pair per line, accepting tab, semicolon, comma or pipe."""
    cards: list[tuple[str, str]] = []
    errors: list[str] = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        if "\t" in line:
            parts = [part.strip() for part in line.split("\t", 1)]
        elif ";" in line or "|" in line:
            parts = [part.strip() for part in re.split(r"[;|]", line, maxsplit=1)]
        else:
            parts = next(csv.reader(io.StringIO(line), skipinitialspace=True))
            parts = [part.strip() for part in parts]

        if len(parts) != 2 or not all(parts):
            errors.append(f"Dòng {line_number}: cần đúng 2 cột")
            continue

        english, vietnamese = parts if english_first else (parts[1], parts[0])
        cards.append((english, vietnamese))

    return cards, errors

