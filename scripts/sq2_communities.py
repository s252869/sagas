"""SQ2: do family communities match conflict groups? Does violence follow marriage (weak) or blood (strong) ties?

Family graph: data/analysis/family_edges.csv, layers blood + affinity + foster (also blood only).
  - Louvain (networkx), 100 seeds: modularity mean/sd and mean pairwise NMI between runs (stability).
  - Label propagation (asyn_lpa, 20 seeds) vs Louvain: NMI (method check).
Conflict groups: connected components of the undirected killing network (feuds).
  - NMI(family communities, feud components) over killing participants in the family graph.
  - Both partitions live within sagas, which inflates NMI, so we compare with the SQ1 null model:
    NMI with feud components rebuilt from 1,000 within-saga victim permutations.
Weak vs strong: killings along a direct affinity tie vs a direct blood tie, observed vs the same null.
Writes data/analysis/sq2_results.csv and figures/sq2_*.png.
"""
import csv, random, statistics, collections, math, itertools
from pathlib import Path
import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "data/analysis"; FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
SEED, N = 2805, 1000
kill = list(csv.DictReader(open(ROOT / "data/final/killings_final.csv", encoding="utf-8")))
E = list(csv.DictReader(open(A / "family_edges.csv", encoding="utf-8")))


def nmi(a, b):
    """Normalised mutual information (arithmetic mean normalisation) between two labelings (dicts) on shared keys."""
    keys = [k for k in a if k in b]; n = len(keys)
    if n == 0:
        return float("nan")
    ca, cb = collections.Counter(a[k] for k in keys), collections.Counter(b[k] for k in keys)
    cab = collections.Counter((a[k], b[k]) for k in keys)
    mi = sum(c / n * math.log((c / n) / (ca[x] / n * cb[y] / n)) for (x, y), c in cab.items())
    h = lambda cnt: -sum(c / n * math.log(c / n) for c in cnt.values())
    ha, hb = h(ca), h(cb)
    return 1.0 if ha + hb == 0 else 2 * mi / (ha + hb)


def family_graph(layers):
    G = nx.Graph()
    for e in E:
        if e["layer"] in layers:
            G.add_edge((e["saga"], e["a"]), (e["saga"], e["b"]), layer=e["layer"])
    return G


def labels(comms):
    return {v: i for i, c in enumerate(comms) for v in c}


def feud_components(pairs):
    K = nx.Graph(); K.add_edges_from(((s, k), (s, v)) for s, k, v in pairs)
    return labels(nx.connected_components(K))


def permute(pairs, rng):
    by = collections.defaultdict(list)
    for s, k, v in pairs:
        by[s].append((k, v))
    out = []
    for s, kv in by.items():
        ks, vs = [k for k, _ in kv], [v for _, v in kv]
        for _ in range(200):
            rng.shuffle(vs)
            if all(k != v for k, v in zip(ks, vs)):
                break
        out += [(s, k, v) for k, v in zip(ks, vs)]
    return out


pairs = [(r["saga"], r["killer"], r["victim"]) for r in kill]
results = []
rng = random.Random(SEED)
for name, layers in [("blood+affinity+foster", {"blood", "affinity", "foster"}), ("blood only", {"blood"})]:
    G = family_graph(layers)
    runs = [nx.community.louvain_communities(G, seed=s) for s in range(100)]
    mods = [nx.community.modularity(G, c) for c in runs]
    labs = [labels(c) for c in runs]
    pair_idx = random.Random(SEED).sample(list(itertools.combinations(range(100), 2)), 300)
    stab = statistics.mean(nmi(labs[i], labs[j]) for i, j in pair_idx)
    lpa = [labels(nx.community.asyn_lpa_communities(G, seed=s)) for s in range(20)]
    lpa_vs = statistics.mean(nmi(labs[0], l) for l in lpa)
    fam = labs[0]
    obs = nmi(fam, feud_components(pairs))
    null = [nmi(fam, feud_components(permute(pairs, rng))) for _ in range(N)]
    mu, sd = statistics.mean(null), statistics.pstdev(null)
    p = min(1, 2 * min((sum(x >= obs for x in null) + 1) / (N + 1), (sum(x <= obs for x in null) + 1) / (N + 1)))
    shared = sum(1 for (s, k, v) in pairs for x in (k, v) if (s, x) in fam)
    res = {"graph": name, "nodes": G.number_of_nodes(), "edges": G.number_of_edges(), "communities": len(runs[0]),
           "modularity_mean": round(statistics.mean(mods), 3), "modularity_sd": round(statistics.pstdev(mods), 4),
           "louvain_stability_nmi": round(stab, 3), "louvain_vs_labelprop_nmi": round(lpa_vs, 3),
           "nmi_family_vs_feuds": round(obs, 3), "nmi_null_mean": round(mu, 3), "nmi_null_sd": round(sd, 3),
           "z": round((obs - mu) / sd, 2) if sd else "", "p_two_sided": round(p, 4)}
    results.append(res)
    print(f"[{name}] {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, {len(runs[0])} communities; "
          f"Q={res['modularity_mean']}±{res['modularity_sd']}; stability NMI={stab:.3f}; Louvain vs LPA NMI={lpa_vs:.3f}")
    print(f"   NMI(family communities, feud components) = {obs:.3f}  vs null {mu:.3f}±{sd:.3f}  z={res['z']}  p={p:.3f}")

# ---- weak (affinity) vs strong (blood) ties ----
tie = collections.defaultdict(dict)
for e in E:
    if e["layer"] in ("blood", "affinity", "foster"):
        for x, y in ((e["a"], e["b"]), (e["b"], e["a"])):
            prev = tie[(e["saga"], x)].get(y)
            order = {"blood": 0, "foster": 1, "affinity": 2}
            if prev is None or order[e["layer"]] < order[prev]:
                tie[(e["saga"], x)][y] = e["layer"]
count = lambda ps: collections.Counter(tie[(s, k)].get(v, "none") for s, k, v in ps)
obs_c = count(pairs)
nulls = [count(permute(pairs, rng)) for _ in range(N)]
for layer in ("blood", "affinity", "foster"):
    nv = [c[layer] for c in nulls]; mu, sd = statistics.mean(nv), statistics.pstdev(nv)
    p = min(1, 2 * min((sum(x >= obs_c[layer] for x in nv) + 1) / (N + 1), (sum(x <= obs_c[layer] for x in nv) + 1) / (N + 1)))
    print(f"killings along a direct {layer:8s} tie: observed {obs_c[layer]}, null {mu:.2f}±{sd:.2f}, ratio {obs_c[layer]/mu if mu else float('nan'):.2f}, p={p:.3f}")
    results.append({"graph": f"tie:{layer}", "nmi_family_vs_feuds": obs_c[layer], "nmi_null_mean": round(mu, 2),
                    "nmi_null_sd": round(sd, 2), "p_two_sided": round(p, 4)})
# ---- main figure: observed vs chance by tie type ----
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
INK, MUTED, GRID, ACCENT, NULLC = "#1d2427", "#5b6669", "#d5dad6", "#24506b", "#c9cfcc"
rows_fig = [("blood", "Blood\n(parent, child, sibling)"), ("foster", "Foster\n(foster-father, -brother)"), ("affinity", "Marriage\n(spouse, in-law)")]
fig, ax = plt.subplots(figsize=(3.4, 2.5))
for i, (layer, lab) in enumerate(rows_fig):
    nv = sorted(c[layer] for c in nulls); lo, hi = nv[int(0.025 * N)], nv[int(0.975 * N) - 1]
    mu = statistics.mean(nv)
    ax.plot([lo, hi], [i, i], color=NULLC, lw=7, solid_capstyle="round", zorder=1)
    ax.plot([mu], [i], marker="|", ms=12, mew=1.5, color=MUTED, zorder=2)
    ax.plot([obs_c[layer]], [i], "o", ms=8, color=ACCENT, mec="white", mew=1.5, zorder=3)
    ax.annotate(f"{obs_c[layer]}", (obs_c[layer], i), xytext=(0, 7), textcoords="offset points",
                ha="center", fontsize=7, color=INK)
ax.set_yticks(range(len(rows_fig)), [l for _, l in rows_fig], fontsize=7, color=INK)
ax.invert_yaxis(); ax.set_xlim(-0.5, None)
ax.set_xlabel("killings between killer and victim with this tie", fontsize=7, color=MUTED)
ax.tick_params(axis="x", labelsize=7, colors=MUTED); ax.tick_params(axis="y", length=0)
ax.grid(axis="x", color=GRID, lw=0.5); ax.set_axisbelow(True)
ax.spines[["top", "right", "left"]].set_visible(False); ax.spines["bottom"].set_color(GRID)
from matplotlib.lines import Line2D
handles = [Line2D([], [], marker="o", ls="", ms=6, color=ACCENT, mec="white", label="observed"),
           Line2D([], [], color=NULLC, lw=6, label="95% range by chance"),
           Line2D([], [], marker="|", ls="", ms=9, mew=1.5, color=MUTED, label="chance mean")]
fig.tight_layout(rect=(0, 0.1, 1, 1))
fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=3, frameon=False,
           fontsize=6, handlelength=1.6, handletextpad=1.0, columnspacing=1.4, labelcolor=MUTED)
fig.savefig(FIG / "sq2_ties.png", dpi=300, bbox_inches="tight"); fig.savefig(FIG / "sq2_ties.pdf", bbox_inches="tight")
print("saved figures/sq2_ties.png")

with open(A / "sq2_results.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, sorted({k for r in results for k in r}, key=lambda k: list(results[0]).index(k) if k in results[0] else 99))
    w.writeheader(); w.writerows(results)
