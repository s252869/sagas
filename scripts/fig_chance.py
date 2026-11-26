"""Figure 2: the two main results against their null model, in one style.
(A) SQ1: share of killings within a family group / along a direct kin tie, observed vs 1,000 within-saga victim shuffles.
(B) SQ2: killings along a direct tie of each type, observed vs the same null.
Reads data/analysis/sq1_nulls.json and sq2_tie_nulls.json (written by sq1_null_model.py and sq2_communities.py).
Writes figures/chance.png/.pdf."""
import json, statistics
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
A, FIG = ROOT / "data/analysis", ROOT / "figures"
INK, MUTED, GRID, ACCENT, NULLC = "#1d2427", "#5b6669", "#d5dad6", "#24506b", "#c9cfcc"
s1 = json.load(open(A / "sq1_nulls.json")); s2 = json.load(open(A / "sq2_tie_nulls.json"))


def pval(obs, null):
    n = len(null)
    return min(1, 2 * min((sum(x >= obs for x in null) + 1) / (n + 1), (sum(x <= obs for x in null) + 1) / (n + 1)))


def panel(ax, rows, unit, title):
    xmax = 0
    for i, (lab, obs, null) in enumerate(rows):
        nv = sorted(null); lo, hi = nv[int(0.025 * len(nv))], nv[int(0.975 * len(nv)) - 1]; mu = statistics.mean(nv)
        xmax = max(xmax, hi, obs); p = pval(obs, null)
        ax.plot([lo, hi], [i, i], color=NULLC, lw=7, solid_capstyle="round", zorder=1)
        ax.plot([obs], [i], "o", ms=6.5, color=ACCENT, mec="white", mew=1.2, zorder=3)
        ax.plot([mu], [i], marker="|", ms=13, mew=1.6, color=MUTED, zorder=4)
        ptxt = "p = 0.002" if p <= 0.002 else (f"p = {p:.3f}" if p < 0.01 else f"p = {p:.2f}")
        ax.text(1.0, i, f"{obs:{unit}} vs {mu:{unit}}\n{ptxt}", transform=ax.get_yaxis_transform(), ha="left", va="center",
                fontsize=6.3, color=INK if p < 0.05 else MUTED, fontweight="bold" if p < 0.05 else "normal")
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=6.8, color=INK)
    ax.set_ylim(len(rows) - 0.4, -0.6); ax.set_xlim(0 if unit == ".0f" else -0.3, xmax * 1.12)
    ax.set_title(title, fontsize=7.5, loc="left", color=INK)
    ax.tick_params(axis="x", labelsize=6, colors=MUTED); ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRID, lw=0.5); ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False); ax.spines["bottom"].set_color(GRID)


fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.1), gridspec_kw={"wspace": 1.15})
pct = lambda d: (100 * d["obs"], [100 * x for x in d["null"]])
g_obs, g_null = pct(s1["group"]); t_obs, t_null = pct(s1["tie"])
panel(a1, [("Same family\nor household", g_obs, g_null), ("Any direct\nkin tie", t_obs, t_null)], ".1f",
      "A  Killings inside the family (SQ1)")
a1.set_xlabel("share of killings (%)", fontsize=6.5, color=MUTED)
for t in a1.texts:
    a, b = t.get_text().split("\n"); x, _, y = a.partition(" vs "); t.set_text(f"{x}% vs {y}%\n{b}")
panel(a2, [("Blood\n(parent, child, sibling)", s2["blood"]["obs"], s2["blood"]["null"]),
           ("Foster\n(foster-father, -brother)", s2["foster"]["obs"], s2["foster"]["null"]),
           ("Marriage\n(spouse, in-law)", s2["affinity"]["obs"], s2["affinity"]["null"])], ".1f",
      "B  Which ties protect (SQ2)")
a2.set_xlabel("killings along this tie", fontsize=6.5, color=MUTED)
for t in a2.texts:                                        # counts: observed is an integer
    t.set_text(t.get_text().replace(".0 vs", " vs", 1))
handles = [Line2D([], [], marker="o", ls="", ms=6, color=ACCENT, mec="white", label="observed"),
           Line2D([], [], color=NULLC, lw=6, label="95% range when victims are shuffled within each saga"),
           Line2D([], [], marker="|", ls="", ms=9, mew=1.5, color=MUTED, label="mean of shuffles")]
fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=False,
           fontsize=6, handlelength=1.6, handletextpad=0.8, columnspacing=1.6, labelcolor=MUTED)
fig.savefig(FIG / "chance.png", dpi=300, bbox_inches="tight"); fig.savefig(FIG / "chance.pdf", bbox_inches="tight")
print("saved figures/chance.png")
