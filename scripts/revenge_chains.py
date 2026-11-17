"""Revenge chains: is a killer tied to someone killed EARLIER in the same saga, and through which tie?

Order: chapter of each killing (first number in data/final/killings_final.csv 'chapter'); same chapter = not earlier.
Tie between two people (same saga), from data/analysis/family_edges.csv (blood, affinity, foster) and persons.csv:
  direct edge (main analysis, depth 1), or also a 2-step path through one relative (loose variant, depth 2:
  produced clearly spurious matches, e.g. a killer 'avenging' his wife's foster-father), or same household label.
  The ambiguous names Egill and Kolur in Njáls saga (several different men) are given no ties.
  Tie type of a path: foster if any foster edge, else affinity if any affinity edge, else blood; 'household' if only
  the family-group label links them. The closest tie wins (direct before 2-step, then blood > foster > affinity).
Revenge killing: killer has a tie to an earlier victim.
Targeted revenge: additionally the victim is that earlier victim's killer, or tied to that killer.
Null models (1,000 draws, seed 2805), both within saga:
  time  : shuffle the chapter order of the killings (does it matter that the loss came FIRST?)
  victim: shuffle victims among killings, as in SQ1 (is the pattern more than coincidence?)
Writes data/analysis/revenge_results.csv, data/analysis/revenge_killings.csv, figures/revenge_ties.png.
"""
import csv, re, random, statistics, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A, FIG = ROOT / "data/analysis", ROOT / "figures"
N, SEED = 1000, 2805
import sys
DEPTH = int(sys.argv[1]) if len(sys.argv) > 1 else 1   # 1 = direct ties only (main); 2 = also 2-step paths (loose)
AMBIGUOUS = {("brennu-njals_saga", "Egill"), ("brennu-njals_saga", "Kolur")}  # several different men share these names
kill = [dict(r, ch=int(re.findall(r"\d+", r["chapter"])[0])) for r in csv.DictReader(open(ROOT / "data/final/killings_final.csv", encoding="utf-8"))]
grp = {(r["saga"], r["name"]): r["family_group"] for r in csv.DictReader(open(A / "persons.csv", encoding="utf-8"))}
adj = collections.defaultdict(dict)
RANK = {"blood": 0, "foster": 1, "affinity": 2}
for e in csv.DictReader(open(A / "family_edges.csv", encoding="utf-8")):
    if e["layer"] in RANK:
        for x, y in ((e["a"], e["b"]), (e["b"], e["a"])):
            k = (e["saga"], x); old = adj[k].get(y)
            if old is None or RANK[e["layer"]] < RANK[old]:
                adj[k][y] = e["layer"]

_cache = {}
def tie(s, a, b):
    """Closest tie type between a and b in saga s, or None."""
    key = (s, a, b)
    if key in _cache:
        return _cache[key]
    t = None
    if (s, a) in AMBIGUOUS or (s, b) in AMBIGUOUS:
        t = None
    elif b in adj[(s, a)]:
        t = adj[(s, a)][b]
    elif DEPTH >= 2:
        best = None
        for m, l1 in adj[(s, a)].items():
            l2 = adj[(s, m)].get(b)
            if l2:
                ls = {l1, l2}
                lt = "foster" if "foster" in ls else ("affinity" if "affinity" in ls else "blood")
                if best is None or RANK[lt] < RANK[best]:
                    best = lt
        t = best
    if t is None and (s, a) not in AMBIGUOUS and (s, b) not in AMBIGUOUS and grp.get((s, a)) and grp.get((s, a)) == grp.get((s, b)):
        t = "household"
    _cache[key] = _cache[(s, b, a)] = t
    return t


def analyse(ks):
    """ks: list of (saga, chapter, killer, victim). Returns per-killing results."""
    by = collections.defaultdict(list)
    for x in ks:
        by[x[0]].append(x)
    out = []
    for s, lst in by.items():
        for (s_, cj, a, b) in lst:
            best, targeted, avenged = None, False, ""
            for (_, ci, ka, x) in lst:
                if ci >= cj or x in (a, b):
                    continue
                t = tie(s, a, x)
                if t and (best is None or ["blood", "foster", "affinity", "household"].index(t) < ["blood", "foster", "affinity", "household"].index(best)):
                    best, avenged = t, x
                if t and (b == ka or tie(s, b, ka)):
                    targeted = True
            out.append({"saga": s, "chapter": cj, "killer": a, "victim": b, "revenge_tie": best or "", "avenges": avenged,
                        "targeted": "yes" if targeted else ""})
    return out


def summary(res):
    c = collections.Counter(r["revenge_tie"] for r in res if r["revenge_tie"])
    return {"revenge": sum(c.values()), "targeted": sum(1 for r in res if r["targeted"]), **{t: c[t] for t in ("blood", "foster", "affinity", "household")}}


base = [(r["saga"], r["ch"], r["killer"], r["victim"]) for r in kill]
obs_res = analyse(base); obs = summary(obs_res)
with open(A / f"revenge_killings_depth{DEPTH}.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(obs_res[0])); w.writeheader(); w.writerows(sorted(obs_res, key=lambda r: (r["saga"], r["chapter"])))

rng = random.Random(SEED)
def shuffle_time(ks):
    by = collections.defaultdict(list)
    for x in ks: by[x[0]].append(x)
    out = []
    for s, lst in by.items():
        chs = [x[1] for x in lst]; rng.shuffle(chs)
        out += [(s, c, x[2], x[3]) for x, c in zip(lst, chs)]
    return out
def shuffle_victims(ks):
    by = collections.defaultdict(list)
    for x in ks: by[x[0]].append(x)
    out = []
    for s, lst in by.items():
        vs = [x[3] for x in lst]
        for _ in range(200):
            rng.shuffle(vs)
            if all(x[2] != v for x, v in zip(lst, vs)): break
        out += [(s, x[1], x[2], v) for x, v in zip(lst, vs)]
    return out

rows = []
nulls = {}
for name, fn in [("time order shuffled", shuffle_time), ("victims shuffled", shuffle_victims)]:
    sims = [summary(analyse(fn(base))) for _ in range(N)]
    nulls[name] = sims
    for key in ("revenge", "targeted", "blood", "foster", "affinity", "household"):
        v = [s[key] for s in sims]; mu, sd = statistics.mean(v), statistics.pstdev(v)
        p = min(1, 2 * min((sum(x >= obs[key] for x in v) + 1) / (N + 1), (sum(x <= obs[key] for x in v) + 1) / (N + 1)))
        rows.append({"null": name, "measure": key, "observed": obs[key], "null_mean": round(mu, 2), "null_sd": round(sd, 2),
                     "z": round((obs[key] - mu) / sd, 2) if sd else "", "p_two_sided": round(p, 4)})
        print(f"[{name:20s}] {key:10s} observed {obs[key]:3d}   null {mu:6.2f} ± {sd:5.2f}   p={p:.3f}")
with open(A / f"revenge_results_depth{DEPTH}.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
print(f"\n{obs['revenge']} of {len(base)} killings are by someone tied to an earlier victim; {obs['targeted']} targeted.")
for r in sorted(obs_res, key=lambda r: (r["saga"], r["chapter"])):
    if r["revenge_tie"] in ("foster", "affinity", "blood"):
        print(f"  {r['saga'][:18]:18s} ch{r['chapter']:>3}  {r['killer']} -> {r['victim']}  avenges {r['avenges']} via {r['revenge_tie']}{'  [targeted]' if r['targeted'] else ''}")
