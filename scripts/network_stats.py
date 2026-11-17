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
A, FIG = ROOT / "data/analysis", ROOT / "figures"
kill = list(csv.DictReader(open(ROOT / "data/final/killings_final.csv", encoding="utf-8")))
fam = [e for e in csv.DictReader(open(A / "family_edges.csv", encoding="utf-8")) if e["layer"] in ("blood", "affinity", "foster")]
NICE = {"brennu-njals_saga": "Njáls saga", "laxdaela_saga": "Laxdæla saga", "egils_saga": "Egils saga", "grettis_saga": "Grettis saga",
        "eyrbyggja_saga": "Eyrbyggja saga", "vatnsdaela_saga": "Vatnsdæla saga", "gisla_saga_surssonar": "Gísla saga",
        "fostbraedra_saga": "Fóstbræðra saga", "faereyinga_saga": "Færeyinga saga", "viga-glums_saga": "Víga-Glúms saga"}


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

# ---- figure: the Njáls saga signed network ----
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
G = signed_graph({"brennu-njals_saga"})
G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
pos = nx.spring_layout(G, seed=7, k=0.3, iterations=500)
INK, KIN, HOST, NODE = "#1d2427", "#b9c2c0", "#b5452f", "#24506b"
fig, ax = plt.subplots(figsize=(7.0, 5.6))
fe = [(u, v) for u, v, d in G.edges(data=True) if d["sign"] > 0]
he = [(u, v) for u, v, d in G.edges(data=True) if d["sign"] < 0]
nx.draw_networkx_edges(G, pos, edgelist=fe, edge_color=KIN, width=0.6, ax=ax)
nx.draw_networkx_edges(G, pos, edgelist=he, edge_color=HOST, width=1.3, ax=ax)
part = {(r["saga"], n) for r in kill for n in (r["killer"], r["victim"])}
deg = dict(G.degree())
nx.draw_networkx_nodes(G, pos, nodelist=[v for v in G if v in part], node_size=[8 + 6 * deg[v] for v in G if v in part],
                       node_color=NODE, edgecolors="white", linewidths=0.4, ax=ax)
nx.draw_networkx_nodes(G, pos, nodelist=[v for v in G if v not in part], node_size=6, node_color="#9aa6a8", linewidths=0, ax=ax)
top = sorted((v for v in G if v in part), key=lambda v: -deg[v])[:11]
placed = []
xs = [p[0] for p in pos.values()]; ys = [p[1] for p in pos.values()]
W, H = (max(xs) - min(xs)), (max(ys) - min(ys))
for v in sorted(top, key=lambda v: -pos[v][1]):
    x, y = pos[v]; ly = y + 0.03 * H
    for _ in range(30):                      # simple label repulsion: push down until free
        if all(abs(x - px) > 0.16 * W or abs(ly - py) > 0.035 * H for px, py in placed):
            break
        ly -= 0.035 * H
    placed.append((x, ly))
    ax.annotate(v[1], (x, y), xytext=(x, ly), fontsize=6.5, ha="center", va="bottom", color=INK,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85),
                arrowprops=dict(arrowstyle="-", color="#5b6669", lw=0.4) if abs(ly - y - 0.03 * H) > 1e-9 else None)
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([], [], color=KIN, lw=1.5, label="family tie (friendly)"), Line2D([], [], color=HOST, lw=2, label="killing (hostile)"),
                   Line2D([], [], marker="o", ls="", color=NODE, label="killer or victim"), Line2D([], [], marker="o", ls="", ms=3, color="#9aa6a8", label="relative")],
          loc="lower left", fontsize=6.5, frameon=False)
ax.axis("off"); fig.tight_layout()
fig.savefig(FIG / "network_njala.png", dpi=300, bbox_inches="tight"); fig.savefig(FIG / "network_njala.pdf", bbox_inches="tight")
print("saved figures/network_njala.png")
