"""Signed saga network: family ties = friendly (+) edges, killings = hostile (-) edges.
Statistics in the style of Mac Carron & Kenna (2013), Table I: N, M, <k>, k_max, l, l_rand, C, C_rand, S, G_C, Delta,
plus degree assortativity r_k and Louvain modularity Q.
Delta = % of closed triads with an odd number of hostile edges (structural balance); compared with a null model that
shuffles the signs over the edges (1,000 draws, seed 2805).
Nodes are (saga, name): characters are not merged across sagas, so the all-sagas network is a union of saga networks.
Writes data/analysis/network_stats.csv, paper/table_network.tex, figures/network_njala.png.
"""
import csv, math, random, statistics, collections
from pathlib import Path
import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
import os
KILLINGS = os.environ.get("KILLINGS", "killings_all.csv")   # killings_final.csv = original keyword set only

A, FIG = ROOT / "data/analysis", ROOT / "figures"
kill = list(csv.DictReader(open(ROOT / "data/final" / KILLINGS, encoding="utf-8")))
fam = [e for e in csv.DictReader(open(A / "family_edges.csv", encoding="utf-8")) if e["layer"] in ("blood", "affinity", "foster")]
NICE = {"brennu-njals_saga": "Njáls saga", "laxdaela_saga": "Laxdæla saga", "egils_saga": "Egils saga", "grettis_saga": "Grettis saga",
        "eyrbyggja_saga": "Eyrbyggja saga", "vatnsdaela_saga": "Vatnsdæla saga", "gisla_saga_surssonar": "Gísla saga",
        "fostbraedra_saga": "Fóstbræðra saga", "faereyinga_saga": "Færeyinga saga", "viga-glums_saga": "Víga-Glúms saga", "reykdaela_saga_og_viga-skutu": "Reykdæla saga", "gull-thoris_saga": "Gull-Þóris saga"}


def signed_graph(sagas=None):
    G = nx.Graph()
    for e in fam:
        if sagas is None or e["saga"] in sagas:
            G.add_edge((e["saga"], e["a"]), (e["saga"], e["b"]), sign=1)
    for r in kill:
        if sagas is None or r["saga"] in sagas:
            u, v = (r["saga"], r["killer"]), (r["saga"], r["victim"])
            if u != v:
                G.add_edge(u, v, sign=-1)          # a killing overrides a family tie between the same pair
    return G


def triads(G):
    out = []
    for u, v in G.edges():
        for w in set(G[u]) & set(G[v]):
            if w > u and w > v:                   # count each triangle once
                out.append(((u, v), (v, w), (u, w)))
    return out


def delta(G, tri, sign):
    if not tri:
        return float("nan")
    odd = sum(1 for t in tri if sum(sign[frozenset(e)] < 0 for e in t) % 2 == 1)
    return odd / len(tri)


def stats(name, G, rng):
    N, M = G.number_of_nodes(), G.number_of_edges()
    k = [d for _, d in G.degree()]; kmean = 2 * M / N
    gc = G.subgraph(max(nx.connected_components(G), key=len))
    l = nx.average_shortest_path_length(gc)
    l_rand = math.log(N) / math.log(kmean) if kmean > 1 else float("nan")
    C = nx.average_clustering(G); C_rand = kmean / N
    S = (C / C_rand) / (l / l_rand) if C_rand and l_rand else float("nan")
    sign = {frozenset((u, v)): d["sign"] for u, v, d in G.edges(data=True)}
    tri = triads(G); D = delta(G, tri, sign)
    signs = list(sign.values()); keys = list(sign.keys()); null = []
    if tri:
        for _ in range(1000):
            rng.shuffle(signs); null.append(delta(G, tri, dict(zip(keys, signs))))
    try:
        rk = nx.degree_assortativity_coefficient(G)
    except Exception:
        rk = float("nan")
    Q = nx.community.modularity(G, nx.community.louvain_communities(G, seed=2805))
    neg = sum(1 for s in signs if s < 0)
    row = {"network": name, "N": N, "M": M, "hostile_edges": neg, "k_mean": round(kmean, 2), "k_max": max(k),
           "l": round(l, 2), "l_rand": round(l_rand, 2), "C": round(C, 3), "C_rand": round(C_rand, 4), "S": round(S, 1),
           "G_C_pct": round(100 * gc.number_of_nodes() / N), "triads": len(tri), "Delta_pct": round(100 * D, 1) if tri else "",
           "Delta_null_pct": round(100 * statistics.mean(null), 1) if null else "",
           "Delta_p": round(min(1, 2 * min((sum(x <= D for x in null) + 1) / 1001, (sum(x >= D for x in null) + 1) / 1001)), 3) if null else "",
           "r_k": round(rk, 2), "Q": round(Q, 2)}
    print(row)
    return row


rng = random.Random(2805)
size = collections.Counter()
for e in fam: size[e["saga"]] += 1
for r in kill: size[r["saga"]] += 1
big = [s for s, _ in size.most_common(6)]
rows = [stats(NICE.get(s, s), signed_graph({s}), rng) for s in big]
rows.append(stats("All 42 sagas", signed_graph(), rng))
with open(A / "network_stats.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)

tex = ["\\begin{table*}[t!]", "\\centering",
       "\\caption{The signed saga networks: family ties as friendly edges, killings as hostile edges. $N$, $M$: nodes and edges (hostile in brackets); "
       "$\\langle k\\rangle$, $k_{\\max}$: mean and maximum degree; $\\ell$, $C$: mean path length (giant component) and clustering, with random-graph "
       "equivalents; $S$: small-world-ness; $G_C$: giant component; $r_k$: degree assortativity; $Q$: Louvain modularity; $\\Delta$: closed triads with an odd number "
       "of hostile edges, with the mean of 1{,}000 sign shuffles. Characters are not merged across sagas, so the all-sagas network is a union of saga networks.}",
       "\\label{tab:network}",
       "\\begin{tabular*}{\\textwidth}{@{\\extracolsep{\\fill}}lrrrrrrrrrrrrr@{}}", "\\toprule",
       "Network & $N$ & $M$ (hostile) & $\\langle k\\rangle$ & $k_{\\max}$ & $\\ell$ & $\\ell_{\\mathrm{rand}}$ & $C$ & $C_{\\mathrm{rand}}$ & $S$ & $G_C$ & $r_k$ & $Q$ & $\\Delta$ (null) \\\\", "\\midrule"]
for r in rows:
    d = f"{r['Delta_pct']}\\% ({r['Delta_null_pct']}\\%)" if r["Delta_pct"] != "" else "--"
    tex.append(f"\\textit{{{r['network']}}} & {r['N']} & {r['M']} ({r['hostile_edges']}) & {r['k_mean']} & {r['k_max']} & {r['l']} & {r['l_rand']} & "
               f"{r['C']} & {r['C_rand']} & {r['S']} & {r['G_C_pct']}\\% & {r['r_k']} & {r['Q']} & {d} \\\\")
tex += ["\\bottomrule", "\\end{tabular*}", "\\end{table*}"]
(ROOT / "paper/table_network.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")

# ---- figure: the Njáls saga signed network, people coloured by family group ----
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
G = signed_graph({"brennu-njals_saga"})
G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
pos = nx.spring_layout(G, seed=7, k=0.3, iterations=500)
INK, KIN, HOST, OTHER, REL = "#1d2427", "#c9cfcc", "#b5452f", "#7a868a", "#b7bfbd"
grp = {(r["saga"], r["name"]): r["family_group"] for r in csv.DictReader(open(A / "persons.csv", encoding="utf-8"))}
# Okabe-Ito colours (colour-blind safe), without orange/vermilion so they cannot be confused with the red killings
FAM = [("njálssynir / bergþórshvoll", "Njáll's household (Bergþórshvoll)", "#0072B2"),
       ("sigfússynir / grjótá", "Sigfússynir (Þráinn, Höskuldur)", "#009E73"),
       ("svínfellingar (flosi's kin)", "Flosi's kin (Svínfellingar)", "#CC79A7"),
       ("hlíðarendi (gunnar's kin)", "Gunnar's kin (Hlíðarendi)", "#56B4E9"),
       ("kirkjubær (otkell's kin)", "Otkell's kin (Kirkjubær)", "#8C6D1F")]
col = {g: c for g, _, c in FAM}
part = {(r["saga"], n) for r in kill for n in (r["killer"], r["victim"])}
deg = dict(G.degree())
fig, ax = plt.subplots(figsize=(7.0, 6.0))
fe = [(u, v) for u, v, d in G.edges(data=True) if d["sign"] > 0]
he = [(u, v) for u, v, d in G.edges(data=True) if d["sign"] < 0]
nx.draw_networkx_edges(G, pos, edgelist=fe, edge_color=KIN, width=0.5, ax=ax)
nx.draw_networkx_edges(G, pos, edgelist=he, edge_color=HOST, width=1.2, alpha=0.9, ax=ax)
nx.draw_networkx_nodes(G, pos, nodelist=[v for v in G if v not in part], node_size=5, node_color=REL, linewidths=0, ax=ax)
pv = sorted((v for v in G if v in part), key=lambda v: grp.get(v, "") in col)   # coloured families drawn on top
nx.draw_networkx_nodes(G, pos, nodelist=pv, node_size=[10 + 5 * deg[v] for v in pv],
                       node_color=[col.get(grp.get(v, ""), OTHER) for v in pv], edgecolors="white", linewidths=0.5, ax=ax)
# labels on a ring outside the network, spread apart, with thin leader lines
import numpy as np
names = ["Gunnar", "Njáll", "Skarphéðinn", "Kári", "Flosi", "Höskuldur Hvítanesgoði", "Þráinn", "Starkaður", "Otkell"]
lab = [v for v in G if v[1] in names]
P = np.array(list(pos.values())); xmin, xmax = P[:, 0].min(), P[:, 0].max(); ymin, ymax = P[:, 1].min(), P[:, 1].max()
W, H = xmax - xmin, ymax - ymin; cx = (xmin + xmax) / 2
for side in ("left", "right"):                         # callout columns at the left and right edges
    vs = sorted([v for v in lab if (pos[v][0] < cx) == (side == "left")], key=lambda v: -pos[v][1])
    ys = [pos[v][1] for v in vs]
    for k in range(1, len(ys)):                        # keep labels at least 0.065*H apart, top to bottom
        ys[k] = min(ys[k], ys[k - 1] - 0.065 * H)
    lx = xmin - 0.08 * W if side == "left" else xmax + 0.08 * W
    for v, ly in zip(vs, ys):
        ax.annotate(v[1], pos[v], xytext=(lx, ly), fontsize=7, color=INK, va="center", zorder=5,
                    ha="right" if side == "left" else "left",
                    arrowprops=dict(arrowstyle="-", color="#5b6669", lw=0.5, shrinkA=1, shrinkB=3,
                                    connectionstyle="angle,angleA=0,angleB=60" if False else "arc3"))
ax.set_xlim(xmin - 0.36 * W, xmax + 0.36 * W)
handles = [Line2D([], [], marker="o", ls="", ms=6, color=cc, mec="white", label=l) for _, l, cc in FAM]
handles += [Line2D([], [], marker="o", ls="", ms=6, color=OTHER, mec="white", label="other killers and victims"),
            Line2D([], [], marker="o", ls="", ms=3, color=REL, label="relative"),
            Line2D([], [], color=KIN, lw=1.5, label="family tie (friendly)"), Line2D([], [], color=HOST, lw=2, label="killing (hostile)")]
ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=3, fontsize=6.5, frameon=False, labelcolor=INK,
          columnspacing=1.4, handletextpad=0.7)
ax.axis("off"); fig.tight_layout()
fig.savefig(FIG / "network_njala.png", dpi=300, bbox_inches="tight"); fig.savefig(FIG / "network_njala.pdf", bbox_inches="tight")
print("saved figures/network_njala.png")

# ---- figure: the five largest saga networks (small multiples) ----
NODE = "#24506b"; KIN = "#b9c2c0"
from matplotlib.lines import Line2D
top5 = [s for s, _ in size.most_common(5)]
fig, axes = plt.subplots(2, 3, figsize=(7.0, 4.9))
for ax, s in zip(axes.flat, top5):
    full = signed_graph({s})
    G = full.subgraph(max(nx.connected_components(full), key=len)).copy()
    pos = nx.spring_layout(G, seed=3, k=1.0 / math.sqrt(G.number_of_nodes()), iterations=500)
    fe = [(u, v) for u, v, d in G.edges(data=True) if d["sign"] > 0]
    he = [(u, v) for u, v, d in G.edges(data=True) if d["sign"] < 0]
    nx.draw_networkx_edges(G, pos, edgelist=fe, edge_color=KIN, width=0.4, ax=ax)
    nx.draw_networkx_edges(G, pos, edgelist=he, edge_color=HOST, width=0.9, ax=ax)
    pv = [v for v in G if v in part]; deg = dict(G.degree())
    nx.draw_networkx_nodes(G, pos, nodelist=pv, node_size=[4 + 2.5 * deg[v] for v in pv], node_color=NODE, linewidths=0, ax=ax)
    nx.draw_networkx_nodes(G, pos, nodelist=[v for v in G if v not in part], node_size=2, node_color="#9aa6a8", linewidths=0, ax=ax)
    nk = sum(1 for r in kill if r["saga"] == s)
    nkg = sum(1 for r in kill if r["saga"] == s and (s, r["killer"]) in G and (s, r["victim"]) in G)
    ax.set_title(f"{NICE.get(s, s)}\n{G.number_of_nodes()} of {full.number_of_nodes()} people, {nkg} of {nk} killings", fontsize=7, color=INK)
    ax.axis("off")
leg = axes.flat[5]; leg.axis("off")
leg.legend(handles=[Line2D([], [], color=KIN, lw=1.2, label="family tie (friendly)"), Line2D([], [], color=HOST, lw=1.8, label="killing (hostile)"),
                    Line2D([], [], marker="o", ls="", ms=5, color=NODE, label="killer or victim"), Line2D([], [], marker="o", ls="", ms=2.5, color="#9aa6a8", label="relative")],
           loc="center", fontsize=7, frameon=False)
fig.tight_layout(); fig.savefig(FIG / "network_top5.png", dpi=300, bbox_inches="tight"); fig.savefig(FIG / "network_top5.pdf", bbox_inches="tight")
print("saved figures/network_top5.png")
