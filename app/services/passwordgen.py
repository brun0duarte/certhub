"""Geração de senhas fortes com política configurável."""
import secrets

UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"
SYMBOLS = "!@#$%&*+-=?"
AMBIGUOUS = set("O0Il1|`'\"")


def generate(length=16, upper=True, lower=True, digits=True,
             symbols=True, exclude_ambiguous=True) -> str:
    pools = []
    if upper:
        pools.append(UPPER)
    if lower:
        pools.append(LOWER)
    if digits:
        pools.append(DIGITS)
    if symbols:
        pools.append(SYMBOLS)
    if not pools:
        pools = [LOWER, DIGITS]
    if exclude_ambiguous:
        pools = ["".join(c for c in p if c not in AMBIGUOUS) for p in pools]

    length = max(int(length), len(pools), 4)
    # garante ao menos um caractere de cada classe escolhida
    chars = [secrets.choice(p) for p in pools]
    all_chars = "".join(pools)
    chars += [secrets.choice(all_chars) for _ in range(length - len(chars))]
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    return "".join(chars)
