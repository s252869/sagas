"""Extension: merge the labelled extra candidates into NEW distinct killings.
in : data/extension/ext_output_*.json, data/final/killings_final.csv, data/final/aliases.csv
out: data/extension/new_killings.csv  (one row per new killer->victim pair, id KN###, with supporting cids)
     data/extension/labels_all.csv    (every candidate with its label)
Pairing as in the main dataset: parallel lists 'A; B' -> 'C; D' pair in order; otherwise every combination."""
import csv, json, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "data/extension"
cand = {r["cid"]: r for r in csv.DictReader(open(E / "candidates.csv", encoding="utf-8"))}
lab = {}
for f in sorted(E.glob("ext_output_*.json")):
    for r in json.loads(f.read_text(encoding="utf-8")):
        lab[r["cid"]] = r
print(f"labelled {len(lab)}/{len(cand)} candidates")
alias = {(r["saga"], r["name"]): r["canonical"] for r in csv.DictReader(open(ROOT / "data/final/aliases.csv", encoding="utf-8"))}
canon = lambda s, n: alias.get((s, n.strip()), n.strip())
existing = {(r["saga"], r["killer"], r["victim"]) for r in csv.DictReader(open(ROOT / "data/final/killings_final.csv", encoding="utf-8"))}

with open(E / "labels_all.csv", "w", newline="", encoding="utf-8") as fh:
    keys = ["cid", "saga", "chapter", "kill_words", "sentence", "killing", "killer", "victim", "duplicate_of", "note"]
    w = csv.DictWriter(fh, keys); w.writeheader()
    for cid, c in cand.items():
        l = lab.get(cid, {})
        w.writerow({**{k: c[k] for k in ("cid", "saga", "chapter", "kill_words", "sentence")},
                    **{k: l.get(k, "") for k in ("killing", "killer", "victim", "duplicate_of", "note")}})

yes = [l for l in lab.values() if str(l.get("killing", "")).lower() == "yes"]
dup = [l for l in yes if l.get("duplicate_of")]
pairs = collections.OrderedDict()
for l in yes:
    if l.get("duplicate_of"):
        continue
    s = cand[l["cid"]]["saga"]
    ks = [x.strip() for x in str(l.get("killer", "")).split(";") if x.strip()]
    vs = [x.strip() for x in str(l.get("victim", "")).split(";") if x.strip()]
    combos = list(zip(ks, vs)) if len(ks) == len(vs) else [(k, v) for k in ks for v in vs]
    for k, v in combos:
        k, v = canon(s, k), canon(s, v)
        if k == v or (s, k, v) in existing:
            continue
        p = pairs.setdefault((s, k, v), {"cids": [], "chapters": set()})
        p["cids"].append(l["cid"]); p["chapters"].add(str(l.get("chapter") or cand[l["cid"]]["chapter"]))
out = []
for i, ((s, k, v), p) in enumerate(pairs.items(), 1):
    out.append({"kid": f"KN{i:03d}", "saga": s, "killer": k, "victim": v, "chapter": sorted(p["chapters"], key=lambda x: int(x) if x.isdigit() else 999)[0],
                "n_sentences": len(p["cids"]), "cids": " ".join(p["cids"])})
with open(E / "new_killings.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, list(out[0]) if out else ["kid"]); w.writeheader(); w.writerows(out)
print(f"yes: {len(yes)} sentences ({len(dup)} duplicates of existing killings); new distinct killings: {len(out)}")
print("by saga:", collections.Counter(r["saga"] for r in out).most_common())
