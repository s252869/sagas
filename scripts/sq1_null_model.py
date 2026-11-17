"""SQ1: are killings within a family group more or less common than chance?

Statistic: share of killings whose killer and victim have the same family_group (data/analysis/persons.csv),
over killings where both have a group.
Null model: within each saga, permute victims among that saga's killings (keeps every person's number of
killings committed and suffered); reject permutations with self-killings; 1,000 draws (seed 2805).
Also reported: share of killings with any direct kin tie in the family graph (blood/affinity/foster).
Variants: all killings; without 'partly' support; without killings where a family is unknown.
Writes data/analysis/sq1_results.csv and figures/sq1_null.png.
"""
import csv, random, statistics, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import os
KILLINGS = os.environ.get("KILLINGS", "killings_all.csv")   # killings_final.csv = original keyword set only

A = ROOT / "data/analysis"; FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
N, SEED = 1000, 2805
kill = list(csv.DictReader(open(ROOT / "data/final" / KILLINGS, encoding="utf-8")))
grp = {(r["saga"], r["name"]): r["family_group"] for r in csv.DictReader(open(A / "persons.csv", encoding="utf-8"))}
tie = collections.defaultdict(set)
for e in csv.DictReader(open(A / "family_edges.csv", encoding="utf-8")):
    if e["layer"] in ("blood", "affinity", "foster"):
        tie[(e["saga"], e["a"])].add(e["b"]); tie[(e["saga"], e["b"])].add(e["a"])


def same_group(s, k, v):
    gk, gv = grp.get((s, k), ""), grp.get((s, v), "")
    return None if not gk or not gv else gk == gv


def direct_tie(s, k, v):
    return v in tie[(s, k)]


def stat(pairs, f):
    vals = [f(*p) for p in pairs]; vals = [x for x in vals if x is not None]
    return sum(vals) / len(vals), sum(vals), len(vals)


def permute(pairs, rng):
    by = collections.defaultdict(list)
    for s, k, v in pairs:
        by[s].append((k, v))
    out = []
    for s, kv in by.items():
        ks, vs = [k for k, _ in kv], [v for _, v in kv]
        for _ in range(200):  # rejection sampling for self-killings
            rng.shuffle(vs)
            if all(k != v for k, v in zip(ks, vs)):
                break
        out += [(s, k, v) for k, v in zip(ks, vs)]
    return out


def test(name, rows, f, rng):
    pairs = [(r["saga"], r["killer"], r["victim"]) for r in rows]
    obs, hits, n = stat(pairs, f)
    null = [stat(permute(pairs, rng), f)[0] for _ in range(N)]
    mu, sd = statistics.mean(null), statistics.pstdev(null)
    z = (obs - mu) / sd if sd else float("nan")
    p_low = (sum(x <= obs for x in null) + 1) / (N + 1); p_high = (sum(x >= obs for x in null) + 1) / (N + 1)
    p = min(1.0, 2 * min(p_low, p_high))
    res = {"test": name, "killings": len(pairs), "n_scored": n, "observed": hits, "observed_share": round(obs, 4),
           "null_mean_share": round(mu, 4), "null_sd": round(sd, 4), "z": round(z, 2), "p_two_sided": round(p, 4),
           "ratio_obs_to_null": round(obs / mu, 2) if mu else ""}
    print(f"{name:55s} obs {hits}/{n} = {obs:.3f}  null {mu:.3f}±{sd:.3f}  z={z:+.2f}  p={p:.3f}  ratio={res['ratio_obs_to_null']}")
    return res, null, obs


rng = random.Random(SEED)
full = kill
no_partly = [r for r in kill if r["support"] == "yes"]
known = [r for r in kill if r["family_known"] == "yes"]
results, keep = [], {}
for label, rows in [("all killings", full), ("without partly-supported", no_partly), ("family known only", known)]:
    r1, null1, obs1 = test(f"same family group | {label}", rows, same_group, rng)
    r2, null2, obs2 = test(f"direct kin tie (graph) | {label}", rows, direct_tie, rng)
    results += [r1, r2]
    if label == "all killings":
        keep = {"group": (null1, obs1), "tie": (null2, obs2)}
with open(A / "sq1_results.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(results[0])); w.writeheader(); w.writerows(results)

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.6))
for ax, (key, title) in zip(axes, [("group", "Same family group"), ("tie", "Direct kin tie")]):
    null, obs = keep[key]
    ax.hist(null, bins=25, color="#c9cfcc", edgecolor="white")
    ax.axvline(obs, color="#24506b", lw=2, label="observed")
    ax.set_title(title, fontsize=9); ax.set_xlabel("share of killings", fontsize=8); ax.tick_params(labelsize=7)
    ax.spines[["top", "right"]].set_visible(False); ax.spines[["left", "bottom"]].set_color("#d5dad6"); ax.tick_params(colors="#5b6669")
axes[0].set_ylabel("permutations", fontsize=8); axes[1].legend(fontsize=7, frameon=False)
fig.tight_layout(); fig.savefig(FIG / "sq1_null.png", dpi=300); fig.savefig(FIG / "sq1_null.pdf")
print("saved figures/sq1_null.png")
