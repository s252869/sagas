"""Time dimension: how feuds unfold over the chapters.
- Feud starters: share of revenge among the FIRST killing of each feud (3+ killings) vs the later killings;
  tested by shuffling the order of killings within each feud (5,000 draws, seed 2805).
- Revenge delay: chapters between a killing and the revenge for it.
- Figure: (A) timeline of the feuds in Njáls saga, (B) revenge share by position in the feud (all sagas).
Writes data/analysis/time_results.md and figures/timeline.png/.pdf."""
import csv, re, collections, statistics, random, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KILLINGS = os.environ.get("KILLINGS", "killings_all.csv")
A, FIG = ROOT / "data/analysis", ROOT / "figures"
k = {r["kid"]: r for r in csv.DictReader(open(ROOT / "data/final" / KILLINGS, encoding="utf-8"))}
f = {r["kid"]: r for r in csv.DictReader(open(ROOT / "data/feuds/killings_feuds.csv", encoding="utf-8")) if r["kid"] in k}
feuds = {(r["saga"], r["feud_id"]): r for r in csv.DictReader(open(ROOT / "data/feuds/feuds.csv", encoding="utf-8"))}
low = lambda s: str(s or "").strip().lower()
ch = lambda kid: int(re.findall(r"\d+", str(k[kid]["chapter"]))[0])
isrev = lambda kid: low(f[kid]["revenge_basis"]) in ("explicit", "implied")

fe = collections.defaultdict(list)
for kid, x in f.items():
    if x["feud_id"]:
        fe[(k[kid]["saga"], x["feud_id"])].append(kid)
big = {key: sorted(v, key=lambda kid: (ch(kid), kid)) for key, v in fe.items() if len(v) >= 3}

def share(lists):
    first = [isrev(v[0]) for v in lists]; mid = [isrev(x) for v in lists for x in v[1:-1]]; last = [isrev(v[-1]) for v in lists]
    return sum(first) / len(first), sum(mid) / len(mid), sum(last) / len(last)
def stat(lists):
    first = [isrev(v[0]) for v in lists]; rest = [isrev(x) for v in lists for x in v[1:]]
    return sum(rest) / len(rest) - sum(first) / len(first)
lists = list(big.values()); obs = stat(lists); rng = random.Random(2805); null = []; null_pos = []
for _ in range(5000):
    sh = []
    for v in lists:
        w = v[:]; rng.shuffle(w); sh.append(w)
    null.append(stat(sh)); null_pos.append(share(sh))
p = (sum(x >= obs for x in null) + 1) / 5001
s_first, s_mid, s_last = share(lists)
starters = collections.Counter(("revenge" if isrev(v[0]) else low(f[v[0]]["motive"])) for v in lists)
rev = [x for x in f.values() if isrev(x["kid"]) and x["avenges_kid"] in k]
delay = [ch(x["kid"]) - ch(x["avenges_kid"]) for x in rev]
out = [f"- Feuds with 3+ killings: {len(lists)} ({sum(map(len, lists))} killings)",
       f"- Revenge share: first killing {s_first:.0%}, middle {s_mid:.0%}, last {s_last:.0%}; later minus first = {obs:.3f}, p = {p:.4f} (within-feud order shuffle)",
       f"- What starts a feud: {dict(starters.most_common())}",
       f"- Revenge delay (n={len(delay)}): median {statistics.median(delay)} chapters; same chapter {sum(d == 0 for d in delay)}; within 2 chapters {sum(d <= 2 for d in delay)}; more than 10 chapters {sum(d > 10 for d in delay)}"]
(A / "time_results.md").write_text("# Time dimension\n\n" + "\n".join(out) + "\n", encoding="utf-8"); print("\n".join(out))

# ---------------- figure ----------------
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from matplotlib.lines import Line2D
INK, MUTED, GRID, ACCENT, OTHER = "#1d2427", "#5b6669", "#d5dad6", "#b5452f", "#7a868a"
fig = plt.figure(figsize=(7.0, 2.5))
gs = fig.add_gridspec(1, 2, width_ratios=[2.0, 1], wspace=0.12)
ax = fig.add_subplot(gs[0]); bx = fig.add_subplot(gs[1])
nj = sorted([(key, v) for key, v in big.items() if key[0] == "brennu-njals_saga"], key=lambda kv: ch(kv[1][0]))
NAMES = {}
for key, v in nj:
    nm = feuds.get(key, {}).get("feud_name", key[1])
    nm = re.sub(r"\s*\(.*?\)", "", nm)
    SHORT = [("Hallgerður", "Hallgerður vs Bergþóra"), ("Gunnar", "Gunnar vs Otkell and Starkaður"), ("viking", "Vikings in Scotland"),
             ("Hrapp", "Hrappur in Norway"), ("Þráinn", "Njálssons vs Þráinn"), ("Höskuldur Hvítanes", "Höskuldur and the Burning")]
    NAMES[key] = next((sh for kw, sh in SHORT if kw.lower() in nm.lower()), (nm[:30] + "…") if len(nm) > 31 else nm)
lane = {key: i for i, (key, _) in enumerate(nj)}
XPOS = {}
for key, v in nj:
    y = lane[key]
    ax.plot([ch(v[0]), ch(v[-1])], [y, y], color=GRID, lw=5, solid_capstyle="round", zorder=1)
    bych = collections.defaultdict(list)
    for kid in v: bych[ch(kid)].append(kid)
    for c_, kids in bych.items():                      # spread killings in the same chapter side by side
        for j, kid in enumerate(kids):
            XPOS[kid] = c_ + (j - (len(kids) - 1) / 2) * 1.1
            ax.plot(XPOS[kid], y, "o", ms=3.6, color=ACCENT if isrev(kid) else OTHER, mec="white", mew=0.6, zorder=3)
where = {kid: lane[key] for key, v in nj for kid in v}
for x in rev:
    a, b = x["avenges_kid"], x["kid"]
    if a in where and b in where:
        ax.add_patch(FancyArrowPatch((XPOS[a], where[a]), (XPOS[b], where[b]), connectionstyle="arc3,rad=-0.35",
                                     arrowstyle="-|>", mutation_scale=5, lw=0.6, color=ACCENT, alpha=0.55, zorder=2))
ax.set_yticks(range(len(nj)), [NAMES[key] for key, _ in nj], fontsize=5.8, color=INK)
ax.invert_yaxis(); ax.set_xlabel("chapter of Njáls saga", fontsize=6.5, color=MUTED)
ax.tick_params(axis="x", labelsize=6, colors=MUTED); ax.tick_params(axis="y", length=0)
ax.spines[["top", "right", "left"]].set_visible(False); ax.spines["bottom"].set_color(GRID)
ax.set_title("A  The feuds of Njáls saga over time", fontsize=7.5, loc="left", color=INK)
for chap, txt, yy in [(77, "Gunnar killed", -0.85), (111, "Höskuldur killed", -0.85), (129, "the Burning", -0.35)]:
    ax.axvline(chap, color=GRID, lw=0.6, ls="--", zorder=0)
    ax.text(chap + 0.8, yy, txt, fontsize=5.8, color=MUTED, ha="left", va="bottom")
ax.set_ylim(len(nj) - 0.4, -1.3)
ax.legend(handles=[Line2D([], [], marker="o", ls="", ms=4.5, color=OTHER, mec="white", label="killing"),
                   Line2D([], [], marker="o", ls="", ms=4.5, color=ACCENT, mec="white", label="revenge killing"),
                   Line2D([], [], color=ACCENT, lw=0.8, alpha=0.7, label="avenges")],
          loc="lower left", fontsize=5.8, frameon=False, ncol=3, bbox_to_anchor=(0, -0.42), labelcolor=MUTED)
vals = [s_first, s_mid, s_last]; labs = ["first\nkilling", "middle", "last\nkilling"]
for i, v in enumerate(vals):
    nv = sorted(100 * q[i] for q in null_pos); lo_, hi_ = nv[int(0.025 * len(nv))], nv[int(0.975 * len(nv)) - 1]
    bx.plot([i, i], [lo_, hi_], color="#c9cfcc", lw=8, solid_capstyle="round", zorder=1)
    bx.plot([i], [statistics.mean(nv)], marker="_", ms=14, mew=1.8, color=MUTED, zorder=4)
    bx.plot([i], [100 * v], "o", ms=6.5, color=ACCENT if i else OTHER, mec="white", mew=1.2, zorder=3)
    bx.text(i + 0.18, 100 * v, f"{100 * v:.0f}%", va="center", fontsize=6.8, color=INK, fontweight="bold")
bx.set_xticks(range(3), labs, fontsize=6.5, color=INK); bx.set_ylim(0, 52); bx.set_xlim(-0.5, 2.7)
bx.set_ylabel("killings that are revenge (%)", fontsize=6.5, color=MUTED)
bx.set_title(f"B  Position in the feud (all sagas,\n{len(lists)} feuds; p < 0.001)", fontsize=7.5, loc="left", color=INK)
bx.tick_params(axis="y", labelsize=6, colors=MUTED); bx.tick_params(axis="x", length=0)
bx.grid(axis="y", color=GRID, lw=0.5); bx.set_axisbelow(True)
bx.spines[["top", "right", "left"]].set_visible(False); bx.spines["bottom"].set_color(GRID)
bx.yaxis.tick_right(); bx.yaxis.set_label_position("right")
bx.text(2.6, -11, "gray: 95% range when the order\nof killings in each feud is shuffled", fontsize=5.6, color=MUTED, ha="right", va="top")
fig.savefig(FIG / "timeline.png", dpi=300, bbox_inches="tight"); fig.savefig(FIG / "timeline.pdf", bbox_inches="tight")
print("saved figures/timeline.png")
