"""How the kind of number rolled relates to XP, from data/run2_rolls.csv (roll, number, xp)."""
import matplotlib.pyplot as plt
import numpy as np

d = np.loadtxt("data/run2_rolls.csv", delimiter=",", dtype=np.int64)
num, xp = d[:, 1], d[:, 2]
s = [str(x) for x in num]
n = len(xp)

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, FAINT = "#2a78d6", "#9fc3ee"
FEW = 10  # groups with fewer rolls than this get a lighter bar


def longest_run(t):
    best = cur = 1
    for a, b in zip(t, t[1:]):
        cur = cur + 1 if a == b else 1
        best = max(best, cur)
    return best


def short(v):
    if v >= 1e6:
        return f"{v / 1e6:.1f}M"
    if v >= 1e3:
        return f"{v / 1e3:.1f}k" if v < 1e4 else f"{v / 1e3:.0f}k"
    return f"{v:.0f}"


# (title, takeaway, per-roll group key, ordered groups as (key, label))
PANELS = [
    ("Different digits used", "Fewer different digits = much more XP",
     [len(set(t)) for t in s], [(6, "6"), (5, "5"), (4, "4"), (3, "3"), (2, "2")]),
    ("Longest run of the same digit", "Runs like 777 or 0000 pay well",
     [longest_run(t) for t in s], [(1, "none"), (2, "2 (77)"), (3, "3 (777)"), (4, "4 (7777)")]),
    ("How many digits", "Shorter numbers score higher",
     [len(t) for t in s], [(6, "6"), (5, "5"), (4, "4"), (3, "3")]),
    ("Zeros at the end", "Ending in 000 is a jackpot",
     [len(t) - len(t.rstrip("0")) for t in s], [(0, "none"), (1, "…0"), (2, "…00"), (3, "…000")]),
    ("Reads the same backwards", "Palindromes (e.g. 818181) score big",
     [t == t[::-1] for t in s], [(False, "no"), (True, "yes")]),
    ("Even or odd", "Makes almost no difference",
     [x % 2 == 0 for x in num], [(False, "odd"), (True, "even")]),
]

plt.rcParams.update({"font.family": "Helvetica Neue", "font.size": 12})
fig, axes = plt.subplots(2, 3, figsize=(15, 9.6), facecolor=SURFACE)
fig.subplots_adjust(left=0.05, right=0.98, top=0.8, bottom=0.11, hspace=0.75, wspace=0.28)
fig.text(0.05, 0.95, "What kind of number gets the most XP?", fontsize=22, fontweight="bold", color=INK)
fig.text(0.05, 0.915, f"Typical (median) XP for each group, from {n:,} real rolls. "
         "Numbers under each bar = how many rolls were in that group.", fontsize=12.5, color=INK2)
fig.text(0.05, 0.885, "Overall typical roll: "
         f"{np.median(xp):,.0f} XP.   Lighter bars = fewer than {FEW} rolls, so less reliable.",
         fontsize=12.5, color=INK2)

for ax, (title, takeaway, keys, groups) in zip(axes.flat, PANELS):
    keys = np.array(keys)
    meds, counts = [], []
    for k, _ in groups:
        m = keys == k
        counts.append(int(m.sum()))
        meds.append(np.median(xp[m]) if m.any() else 0)
    x = np.arange(len(groups))
    colors = [BLUE if c >= FEW else FAINT for c in counts]
    ax.bar(x, meds, width=0.66, color=colors)
    ax.set_facecolor(SURFACE)
    ax.set_yscale("log")
    ax.set_ylim(2_000, max(meds) * 4)
    ax.set_yticks([])
    ax.minorticks_off()
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.set_xticks(x, [f"{lab}\n{c:,} rolls" for (_, lab), c in zip(groups, counts)],
                  fontsize=11, color=INK2)
    ax.tick_params(axis="x", length=0, pad=6)
    for xi, m in zip(x, meds):
        ax.text(xi, m * 1.15, short(m), ha="center", va="bottom", fontsize=12.5, fontweight="bold", color=INK)
    ax.set_title(f"{title}\n", loc="left", fontsize=14, fontweight="bold", color=INK)
    ax.text(0, 1.04, takeaway, transform=ax.transAxes, fontsize=11.5, color=INK2)

fig.text(0.05, 0.035, "The very biggest rolls come from specific 'special' numbers, not patterns: "
         "58008 (50M), 694204 (1.7M), 62832 (τ digits). Bars use a log scale so big and small groups both fit.",
         fontsize=11, color=INK2)
fig.savefig("charts/xp_by_number_type.png", dpi=150, facecolor=SURFACE)
print("saved")
