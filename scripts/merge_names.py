"""Robustness check: merge obvious name variants of the same person within a saga.
Rule: a bare name X (not used as a separate person alongside the fuller name in the killing list) (one word) is merged with a fuller name "X ..." only if exactly ONE fuller name starting with X
exists in that saga (so "Njáll" + "Njáll Þorgeirsson" merge, but "Höskuldur" is left alone because there are two).
The canonical form is the one used in the killing list, if any; otherwise the fuller name.
Writes data/analysis/name_merges.csv and data/final/killings_all_merged.csv."""
import csv, collections, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A, FIN = ROOT / "data/analysis", ROOT / "data/final"
kill = list(csv.DictReader(open(FIN / "killings_all.csv", encoding="utf-8")))
fam = list(csv.DictReader(open(A / "family_edges.csv", encoding="utf-8")))
names = collections.defaultdict(set)
for e in fam:
    names[e["saga"]].update((e["a"], e["b"]))
in_kill = collections.defaultdict(set)
for r in kill:
    names[r["saga"]].update((r["killer"], r["victim"])); in_kill[r["saga"]].update((r["killer"], r["victim"]))
merges = []
for s, ns in names.items():
    for x in ns:
        if " " in x or "(" in x:
            continue
        full = [n for n in ns if n.startswith(x + " ") and "(" not in n and " and " not in n and " og " not in n]
        if len(full) == 1:
            f = full[0]
            if x in in_kill[s] and f in in_kill[s]:
                continue        # both forms used as separate people in the killing list: the annotators distinguished them
            canon = x if (x in in_kill[s] and f not in in_kill[s]) else f
            other = f if canon == x else x
            merges.append({"saga": s, "name": other, "canonical": canon})
with open(A / "name_merges.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, ["saga", "name", "canonical"]); w.writeheader(); w.writerows(merges)
m = {(r["saga"], r["name"]): r["canonical"] for r in merges}
out = []
for r in kill:
    r = dict(r); r["killer"] = m.get((r["saga"], r["killer"]), r["killer"]); r["victim"] = m.get((r["saga"], r["victim"]), r["victim"])
    if r["killer"] != r["victim"]:
        out.append(r)
with open(FIN / "killings_all_merged.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, list(out[0])); w.writeheader(); w.writerows(out)
print(f"{len(merges)} name variants merged; killings {len(kill)} -> {len(out)}")
for r in merges[:25]:
    print(f"  {r['saga'][:16]:16s} {r['name']}  ->  {r['canonical']}")
