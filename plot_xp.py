"""Plot the XP odds from the logged RNGdle reroller run, grouped into detailed XP ranges."""
import matplotlib.pyplot as plt
import numpy as np

xp = np.loadtxt("data/run2_rolls.csv", delimiter=",", usecols=2, ndmin=1)
n = len(xp)

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE = "#2a78d6"

# Finer steps where most rolls land, wider steps in the rare tail.
EDGES = [0, 2_500, 3_500, 4_500, 5_500, 6_500, 8_000, 10_000, 15_000, 20_000, 30_000, 50_000,
         100_000, 250_000, 500_000, 1_000_000, 5_000_000, 10_000_000, np.inf]

def short(v):
    if v >= 1e6:
        return f"{v / 1e6:g}M"
    if v >= 1e3:
        return f"{v / 1e3:g}k"
    return f"{v:g}"

def range_label(lo, hi):
    if lo == 0:
        return f"Under {short(hi)}"
    if hi == np.inf:
        return f"{short(lo)} or more"
    return f"{short(lo)} – {short(hi)}"

def one_in(p):
    if p == 0:
        return "—"
    return f"1 in {1 / p:,.0f}"

def pct(p):
    if p == 0:
        return "0%"
    return f"{p:.1%}" if p >= 0.001 else f"{p:.2%}"

rows = []
for lo, hi in zip(EDGES[:-1], EDGES[1:]):
    c = int(((xp >= lo) & (xp < hi)).sum())
    rows.append((range_label(lo, hi), c, c / n, (xp >= lo).mean()))

plt.rcParams.update({"font.family": "Helvetica Neue", "font.size": 12})
fig = plt.figure(figsize=(13, 11), facecolor=SURFACE)

fig.text(0.04, 0.965, "RNGdle: how likely is each XP score?", fontsize=22, fontweight="bold", color=INK)
fig.text(0.04, 0.94, f"Based on {n:,} real rolls from one reroller run", fontsize=12.5, color=INK2)

# Headline numbers: where the middle, average and top slices of rolls start.
tiles = [
    (f"{np.median(xp):,.0f}", "typical roll (median)"),
    (f"{xp.mean():,.0f}", "average roll (pulled up by rare huge rolls)"),
    (f"{np.percentile(xp, 90):,.0f}+", "top 10% of rolls"),
    (f"{np.percentile(xp, 99):,.0f}+", "top 1% of rolls"),
]
for i, (big, small) in enumerate(tiles):
    x = 0.04 + i * 0.24
    fig.text(x, 0.885, big, fontsize=24, fontweight="bold", color=INK)
    fig.text(x, 0.862, small, fontsize=11, color=INK2)

# Table-style chart: label | bar | rolls | % | odds | chance of this or more.
top, bottom = 0.79, 0.07
ax = fig.add_axes((0.14, bottom, 0.36, top - bottom), facecolor="none")
y = np.arange(len(rows))[::-1]
shares = [r[2] for r in rows]
ax.barh(y, shares, height=0.7, color=BLUE)
# A tiny tick so ranges with only a roll or two are still visible as "something".
for yi, (_, c, s, _) in zip(y, rows):
    if 0 < s < max(shares) * 0.01:
        ax.plot([0, max(shares) * 0.01], [yi, yi], color=BLUE, linewidth=4, solid_capstyle="butt")
ax.set_yticks(y, [r[0] for r in rows], fontsize=12.5, color=INK)
ax.set_ylim(-0.6, len(rows) - 0.4)
ax.set_xlim(0, max(shares) * 1.05)
ax.set_xticks([])
for s in ("top", "right", "bottom", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0, pad=8)
# Light bands every other row to guide the eye across to the numbers.
for yi in y[::2]:
    fig.patches.append(plt.Rectangle(
        (0.035, fig.transFigure.inverted().transform(ax.transData.transform((0, yi - 0.5)))[1]),
        0.93, (top - bottom) / len(rows), transform=fig.transFigure, color="#f1f0ec", zorder=-1))

cols = [(0.53, "Rolls"), (0.62, "% of rolls"), (0.73, "Odds"), (0.84, "Chance of this\nor more")]
for x, head in cols:
    fig.text(x, top + 0.008, head, fontsize=11.5, color=INK2, fontweight="bold", va="bottom")
fig.text(0.14, top + 0.008, "Share of rolls in each XP range", fontsize=11.5, color=INK2,
         fontweight="bold", va="bottom")
for yi, (_, c, share, at_least) in zip(y, rows):
    yfig = fig.transFigure.inverted().transform(ax.transData.transform((0, yi)))[1]
    for (x, _), text in zip(cols, (f"{c:,}", pct(share), one_in(share), pct(at_least))):
        fig.text(x, yfig, text, fontsize=12.5, color=INK, va="center")

fig.text(0.04, 0.03, "Best roll in this run: 50,012,528 XP (Exact Boob, the number 58008). "
         "Ranges with only a few rolls have rough odds.", fontsize=10.5, color=INK2)
fig.savefig("charts/xp_odds.png", dpi=150, facecolor=SURFACE)

for label, c, share, at_least in rows:
    print(f"{label:>14}: {c:5} rolls  {pct(share):>6}  {one_in(share):>10}  this-or-more {one_in(at_least)}")
print(f"median {np.median(xp):,.0f}  mean {xp.mean():,.0f}  p90 {np.percentile(xp, 90):,.0f}  p99 {np.percentile(xp, 99):,.0f}")
