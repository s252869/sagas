"""Extension: candidate sentences with OTHER killing words than the original 14 forms.
Writes data/extension/candidates.csv and chunked agent inputs ext_input_{1..5}.json (with the existing killings per saga)."""
import re, csv, json, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT.parent / "saga-feuds/data/raw/is"
OLD = set("drap drápu drepið drepinn drepin drepnir vó vógu veginn vegið vegnir víg vígið víginu".split())
NEW = re.compile(r"^(féll|fellur|felldi|felldu|fallinn|föllnu|banahögg|banahöggið|banasár|banasárið|bana|bani|banamaður|banamann|"
                 r"brenndur|brenndir|brennu|brenna|líflát|lífláti|deyddi|deyddur|höggva|hjó|hjuggu|vegur|drepur|drepa)$")
SPLIT = re.compile(r'(?<=[.!?])["“”»]?\s+(?=[„"“«]?[A-ZÁÐÉÍÓÚÝÞÆÖ0-9])')
rows = []
for f in sorted(RAW.glob("*.is.txt")):
    saga = f.name.split(".")[0]; ch = 0; sents = []
    for para in re.split(r"\n\s*\n", f.read_text(encoding="utf-8")):
        para = " ".join(para.split()); m = re.fullmatch(r"(\d+)\. kafli", para)
        if m: ch = int(m.group(1)); continue
        sents += [(ch, s) for s in SPLIT.split(para) if s]
    for i, (ch, s) in enumerate(sents):
        w = [x.lower() for x in re.findall(r"[^\W\d_]+", s)]
        if any(x in OLD for x in w): continue
        hits = sorted({x for x in w if NEW.match(x)})
        if hits:
            rows.append({"cid": f"{saga}:x{i}", "saga": saga, "chapter": ch, "before": sents[i-1][1] if i else "",
                         "sentence": s, "after": sents[i+1][1] if i + 1 < len(sents) else "", "kill_words": ", ".join(hits)})
with open(ROOT / "data/extension/candidates.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
kill = list(csv.DictReader(open(ROOT / "data/final/killings_final.csv", encoding="utf-8")))
exist = collections.defaultdict(list)
for r in kill: exist[r["saga"]].append({"kid": r["kid"], "chapter": r["chapter"], "killer": r["killer"], "victim": r["victim"]})
per = collections.Counter(r["saga"] for r in rows)
# balance 5 chunks; Njála split into two halves by chapter
items = []
for s, n in per.items():
    if s == "brennu-njals_saga":
        nj = [r for r in rows if r["saga"] == s]; half = len(nj) // 2
        items += [(f"{s}#1", nj[:half]), (f"{s}#2", nj[half:])]
    else:
        items.append((s, [r for r in rows if r["saga"] == s]))
chunks = [[] for _ in range(5)]; load = [0] * 5
for key, rs in sorted(items, key=lambda x: -len(x[1])):
    i = load.index(min(load)); chunks[i].append((key, rs)); load[i] += len(rs)
for i, ch in enumerate(chunks, 1):
    sagas = sorted({k.split("#")[0] for k, _ in ch})
    json.dump({"candidates": [r for _, rs in ch for r in rs], "existing_killings": {s: exist.get(s, []) for s in sagas}},
              open(ROOT / f"data/extension/ext_input_{i}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(i, load[i-1], [k for k, _ in ch])
print("total candidates", len(rows))
