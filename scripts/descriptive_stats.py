"""Overall statistics about the dataset: corpus, killings, people, networks, feuds.
Writes data/analysis/descriptive_stats.md, paper/table_overview.tex and figures/killings_per_saga.png."""
import csv, re, collections, statistics
from pathlib import Path
import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT.parent / "saga-feuds/data/raw/is"          # texts are not in the repo (see README)
if not RAW.exists():
    RAW = ROOT / "data/raw/is"
A, FIG = ROOT / "data/analysis", ROOT / "figures"
kill = list(csv.DictReader(open(ROOT / "data/final/killings_final.csv", encoding="utf-8")))
feud = {r["kid"]: r for r in csv.DictReader(open(ROOT / "data/feuds/killings_feuds.csv", encoding="utf-8"))}
feuds = list(csv.DictReader(open(ROOT / "data/feuds/feuds.csv", encoding="utf-8")))
fam = list(csv.DictReader(open(A / "family_edges.csv", encoding="utf-8")))
L = []
add = L.append

# corpus
words = chapters = 0; sagas = []
for f in sorted(RAW.glob("*.is.txt")):
    t = f.read_text(encoding="utf-8"); sagas.append(f.name.split(".")[0])
    words += len(re.findall(r"\w+", t)); chapters += len(re.findall(r"^\s*\d+\. kafli\s*$", t, re.M))
per = collections.Counter(r["saga"] for r in kill)
add("## Corpus")
add(f"- Sagas: {len(sagas)}; words: {words:,}; chapters: {chapters:,}")
add(f"- Candidate sentences: 1,048; labelled as killings: 407; distinct killings after merging and corrections: {len(kill)}")
add(f"- Sagas with at least one killing: {len(per)} of {len(sagas)}; median killings per saga (all 42): {statistics.median([per.get(s,0) for s in sagas])}; "
    f"most: {', '.join(f'{s} ({n})' for s, n in per.most_common(5))}")
add(f"- Killings per 10,000 words (corpus): {len(kill)/words*1e4:.1f}")

# people and killing network
G = nx.DiGraph()
for r in kill:
    G.add_edge((r["saga"], r["killer"]), (r["saga"], r["victim"]))
killers = {v for v in G if G.out_degree(v)}; victims = {v for v in G if G.in_degree(v)}
add("\n## People and the killing network")
add(f"- People: {G.number_of_nodes()}; killers: {len(killers)}; victims: {len(victims)}; both killer and killed: {len(killers & victims)}")
top_k = sorted(G.out_degree, key=lambda x: -x[1])[:8]
add("- Most killings committed: " + ", ".join(f"{n} ({s.split('_')[0]}) {d}" for (s, n), d in top_k))
top_v = [x for x in sorted(G.in_degree, key=lambda x: -x[1]) if x[1] > 1]
add("- Victims credited to more than one killer: " + ", ".join(f"{n} ({s.split('_')[0]}) {d}" for (s, n), d in top_v[:6]) + f" ({len(top_v)} in total)")
outd = [d for _, d in G.out_degree if d]
add(f"- Killers with one killing: {sum(1 for d in outd if d==1)}; with 2-4: {sum(1 for d in outd if 2<=d<=4)}; with 5+: {sum(1 for d in outd if d>=5)}")
comps = sorted(nx.weakly_connected_components(G), key=len, reverse=True)
add(f"- Connected components (chains of linked killings): {len(comps)}; largest: {len(comps[0])} people "
    f"({next(iter(comps[0]))[0]}); components of size 2 (a single isolated killing): {sum(1 for c in comps if len(c)==2)}")
add(f"- Mean killings per killer: {statistics.mean(outd):.2f}; pairs who killed each other: "
    f"{sum(1 for u, v in G.edges if G.has_edge(v, u))//2}")

# relations, support
add("\n## Killer–victim relations")
add(f"- Strict: {dict(collections.Counter(r['relation'] for r in kill))}; wide kin: {sum(r['kin_broad']=='yes' for r in kill)}")
add(f"- Same family group: {sum(r['same_group']=='yes' for r in kill)}; support partly: {sum(r['support']=='partly' for r in kill)}; "
    f"family of a participant unknown: {sum(r['family_known']=='no' for r in kill)}")

# family network
fe = collections.Counter(e["layer"] for e in fam)
F = nx.Graph(); F.add_edges_from(((e["saga"], e["a"]), (e["saga"], e["b"])) for e in fam if e["layer"] != "other")
add("\n## Family network")
add(f"- People: {F.number_of_nodes()} (participants and their recorded kin); ties: {F.number_of_edges()} "
    f"(blood {fe['blood']}, affinity {fe['affinity']}, foster {fe['foster']}; plus {fe['other']} unspecified kin not used)")
add(f"- Mean number of recorded relatives per participant: {statistics.mean(F.degree(v) for v in G if v in F):.1f}")

# feuds and motives
real = [x for x in feuds if x.get("feud_type", "").lower() != "isolated" and int(x.get("n_killings") or 0) >= 2]
rev = [r for r in feud.values() if r["revenge_basis"].lower() in ("explicit", "implied")]
add("\n## Feuds and motives")
add(f"- Conflicts identified: {len(feuds)}; feuds with 2+ killings: {len(real)}, containing {sum(int(x['n_killings']) for x in real)} killings "
    f"({sum(int(x['n_killings']) for x in real)/len(kill):.0%}); median killings per feud: {statistics.median(int(x['n_killings']) for x in real)}")
add(f"- Feuds ended by: {dict(collections.Counter(x.get('ended_by','').lower() for x in real))}")
add(f"- Motives: {dict(collections.Counter(r['motive'].lower() for r in feud.values()).most_common())}")
add(f"- Revenge killings: {len(rev)} ({len(rev)/len(kill):.0%}); explicit in the text: {sum(r['revenge_basis'].lower()=='explicit' for r in rev)}; "
    f"strikes the killer himself: {sum(r['target'].lower()=='the killer himself' for r in rev)}")
add(f"- Avenger's relation to the avenged: {dict(collections.Counter(r['relation_category'].lower() for r in rev).most_common())}")
(A / "descriptive_stats.md").write_text("# Dataset overview\n\n" + "\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))

# LaTeX table for the paper
T = [("Sagas / words", f"{len(sagas)} / {words/1e3:.0f}k"), ("Candidate sentences / labelled killings", "1,048 / 407"),
     ("Distinct killings", f"{len(kill)}"), ("People (killers / victims / both)", f"{G.number_of_nodes()} ({len(killers)} / {len(victims)} / {len(killers & victims)})"),
     ("Killing chains (components); largest", f"{len(comps)}; {len(comps[0])} people"),
     ("Family network: people / ties", f"{F.number_of_nodes()} / {F.number_of_edges()}"),
     ("Feuds (2+ killings) / killings in feuds", f"{len(real)} / {sum(int(x['n_killings']) for x in real)}"),
     ("Revenge killings (explicit in text)", f"{len(rev)} ({sum(r['revenge_basis'].lower()=='explicit' for r in rev)})"),
     ("Killer and victim related (strict / wide)", f"{sum(r['relation']!='none' for r in kill)} / {sum(r['kin_broad']=='yes' for r in kill)}")]
tex = ["\\begin{table}[tbhp]", "\\centering", "\\caption{The dataset.}", "\\label{tab:overview}",
       "\\begin{tabular}{lr}", "\\toprule"] + [f"{a} & {b} \\\\" for a, b in T] + ["\\bottomrule", "\\end{tabular}", "\\end{table}"]
(ROOT / "paper/table_overview.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")

# figure: killings per saga
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
INK, MUTED, GRID, ACCENT = "#1d2427", "#5b6669", "#d5dad6", "#24506b"
items = sorted(((per.get(s, 0), s) for s in sagas))[::-1]
NICE = {"brennu-njals_saga": "Njáls saga", "grettis_saga": "Grettis saga", "egils_saga": "Egils saga", "fostbraedra_saga": "Fóstbræðra saga",
    "laxdaela_saga": "Laxdæla saga", "kroka-refs_saga": "Króka-Refs saga", "gull-thoris_saga": "Gull-Þóris saga", "faereyinga_saga": "Færeyinga saga",
    "eyrbyggja_saga": "Eyrbyggja saga", "vatnsdaela_saga": "Vatnsdæla saga", "vopnfirdinga_saga": "Vopnfirðinga saga", "thordar_saga_hredu": "Þórðar saga hreðu",
    "reykdaela_saga_og_viga-skutu": "Reykdæla saga", "floamanna_saga": "Flóamanna saga", "droplaugarsona_saga": "Droplaugarsona saga",
    "viga-glums_saga": "Víga-Glúms saga", "svarfdaela_saga": "Svarfdæla saga", "thorsteins_saga_hvita": "Þorsteins saga hvíta",
    "ljosvetninga_saga": "Ljósvetninga saga", "hrana_saga_hrings": "Hrana saga hrings", "heidarviga_saga": "Heiðarvíga saga",
    "hallfredar_saga_vandraedaskalds": "Hallfreðar saga", "gisla_saga_surssonar": "Gísla saga", "bandamanna_saga": "Bandamanna saga",
    "valla-ljots_saga": "Valla-Ljóts saga", "kormaks_saga": "Kormáks saga", "gunnlaugs_saga_ormstungu": "Gunnlaugs saga",
    "finnboga_saga_ramma": "Finnboga saga", "eiriks_saga_rauda": "Eiríks saga rauða", "bardar_saga_snaefellsass": "Bárðar saga",
    "kjalnesinga_saga": "Kjalnesinga saga", "hrafnkels_saga_freysgoda": "Hrafnkels saga", "havardar_saga_isfirdings": "Hávarðar saga",
    "hardar_saga_og_holmverja": "Harðar saga", "gunnars_saga_keldugnupsfifls": "Gunnars saga Keldugnúpsfífls", "bjarnar_saga_hitdaelakappa": "Bjarnar saga",
    "viglundar_saga": "Víglundar saga", "thorsteins_saga_sidu-hallssonar": "Þorsteins saga Síðu-Hallssonar", "olkofra_saga": "Ölkofra þáttur",
    "haensna-thoris_saga": "Hænsa-Þóris saga", "graenlendinga_saga": "Grænlendinga saga", "fljotsdaela_saga": "Fljótsdæla saga"}
nice = lambda s: NICE.get(s, s)
fig, ax = plt.subplots(figsize=(3.4, 5.6))
ys = range(len(items))
ax.barh(list(ys), [n for n, _ in items], color=ACCENT, height=0.7)
for y, (n, _) in zip(ys, items):
    if n: ax.text(n + 0.6, y, str(n), va="center", fontsize=5.5, color=INK)
ax.set_yticks(list(ys), [nice(s) for _, s in items], fontsize=5.5, color=INK)
ax.invert_yaxis(); ax.tick_params(axis="y", length=0); ax.tick_params(axis="x", labelsize=6, colors=MUTED)
ax.set_xlabel("killings in the dataset", fontsize=6.5, color=MUTED)
ax.grid(axis="x", color=GRID, lw=0.5); ax.set_axisbelow(True)
ax.spines[["top", "right", "left"]].set_visible(False); ax.spines["bottom"].set_color(GRID)
fig.tight_layout(); fig.savefig(FIG / "killings_per_saga.png", dpi=300, bbox_inches="tight"); fig.savefig(FIG / "killings_per_saga.pdf", bbox_inches="tight")
