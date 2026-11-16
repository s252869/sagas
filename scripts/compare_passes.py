"""Compare pass 1 (data/final/killings_pass1.csv) with the blind pass 2 (data/final/pass2_output_*.json).
Writes data/final/killings_compared.csv and data/final/disagreements.json (input for a tie-break pass),
and prints agreement statistics for the Methods section."""
import collections, csv, json
from pathlib import Path

FIN = Path(__file__).resolve().parents[1] / "data/final"
p1 = {r["kid"]: r for r in csv.DictReader(open(FIN / "killings_pass1.csv", encoding="utf-8"))}
p2 = {}
for f in sorted(FIN.glob("pass2_output_*.json")):
    for r in json.loads(f.read_text(encoding="utf-8")):
        p2[r["kid"]] = r
print(f"pass1 {len(p1)} killings, pass2 {len(p2)} coded")

cat = lambda s: (str(s or "").split(":")[0].split("(")[0].strip().lower() or "blank")
yn = lambda s: str(s or "").strip().lower()[:3].rstrip() or "blank"


def kappa(a, b):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum(a.count(c) / n * b.count(c) / n for c in set(a) | set(b))
    return po, (po - pe) / (1 - pe) if pe < 1 else float("nan")


sup = collections.Counter(yn(r.get("supported")) for r in p2.values())
print("pass2 supports the killing:", dict(sup))
both = [k for k in p1 if k in p2 and p1[k]["relation_p1"]]  # corrected pairs have no pass-1 relation
a = [cat(p1[k]["relation_p1"]) for k in both]; b = [cat(p2[k]["relation"]) for k in both]
po, k = kappa(a, b)
print(f"relation category: {po:.1%} agreement, Cohen's kappa {k:.2f} (n={len(both)})")
print("  confusion (pass1 -> pass2):", collections.Counter((x, y) for x, y in zip(a, b) if x != y).most_common())
a2 = [yn(p1[k]["same_group_p1"]) for k in both]; b2 = [yn(p2[k]["same_group"]) for k in both]
po2, k2 = kappa(a2, b2)
print(f"same family group: {po2:.1%} agreement, Cohen's kappa {k2:.2f}")
nu = lambda c: "none" if c == "unknown" else c
po4, k4 = kappa([nu(x) for x in a], [nu(x) for x in b])
print(f"relation category, unknown=none: {po4:.1%} agreement, Cohen's kappa {k4:.2f}")
kin = lambda c: "kin" if c in ("blood", "affinity", "foster", "sworn") else "not kin"
po3, k3 = kappa([kin(x) for x in a], [kin(x) for x in b])
print(f"kin vs not kin: {po3:.1%} agreement, Cohen's kappa {k3:.2f}")

rows, dis = [], []
for kid, r in p1.items():
    q = p2.get(kid, {})
    flags = []
    if yn(q.get("supported")) not in ("yes",):
        flags.append(f"support={q.get('supported')}")
    if r["relation_p1"] and cat(r["relation_p1"]) != cat(q.get("relation")):
        flags.append("relation")
    if r["relation_p1"] and yn(r["same_group_p1"]) != yn(q.get("same_group")):
        flags.append("same_group")
    if not r["relation_p1"]:
        flags.append("corrected_pair(no pass1 relation)")
    row = {**r, "supported_p2": q.get("supported", ""), "actual_killer_p2": q.get("actual_killer", ""),
           "actual_victim_p2": q.get("actual_victim", ""), "chapter_p2": q.get("chapter", ""),
           "evidence_p2": q.get("evidence", ""), "relation_p2": q.get("relation", ""),
           "relation_detail_p2": q.get("relation_detail", ""), "same_group_p2": q.get("same_group", ""),
           "confidence_p2": q.get("confidence", ""), "note_p2": q.get("note", ""), "flags": "; ".join(flags)}
    rows.append(row)
    if flags:
        dis.append({k: row[k] for k in ("kid", "saga", "killer", "victim", "first_sentence_id", "flags",
                                        "relation_p1", "same_group_p1", "notes_p1", "supported_p2",
                                        "actual_killer_p2", "actual_victim_p2", "chapter_p2", "evidence_p2",
                                        "relation_p2", "relation_detail_p2", "same_group_p2", "note_p2")})
with open(FIN / "killings_compared.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
json.dump(dis, open(FIN / "disagreements.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(dis)} killings need a tie-break ({collections.Counter(f.split('=')[0].split('(')[0] for d in dis for f in d['flags'].split('; '))})")
