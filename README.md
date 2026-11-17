# Saga Feuds: killing and kinship in the Sagas of Icelanders

Group project for DTU 02805 Social Graphs and Interactions (2026).
Ylfa Margrét Ólafsdóttir, Tanja Kristín Árnadóttir and Andrea Hermóðsdóttir.

**Question:** do killings in the 42 *Íslendingasögur* follow family lines, or cut across them?

## The data at a glance

| | |
|---|---|
| Sagas | 42 (modern-spelling Icelandic, [sagadb.org](https://sagadb.org/downloads)) |
| Candidate sentences (14 forms of *drepa*, *vega*, *víg*) + extension (other killing words) | 1,048 + 1,745 |
| Sentences labelled as killings | 407 + 492 |
| Final distinct killings (killer → victim) | **482** (194 original + 291 extension − 3 replaced) |
| Characters involved | 624 |

**Main file: [`data/final/killings_all.csv`](data/final/killings_all.csv)** (`killings_final.csv` = the original 194, used as a robustness check), with one row per killing:
saga, killer, victim, relation (`none` / `blood` / `affinity` / `foster` / `sworn`), same family group,
whether the family is known, support (`yes` / `partly`), chapter, a quoted Icelandic clause as evidence,
and how the row was decided.

## How it was made (AI-assisted)

The annotation and kinship lookup were done with **Claude (Anthropic)**. We defined and refined the
inclusion rules, and the model did the detailed annotation. Consistency was measured between independent AI passes, and accuracy by a manual check of 90 killings:

1. **Labelling:** for each candidate sentence, is this a killing, and who is the killer and the victim → `data/labelled/person{1,2,3}_named_killings.xlsx`
2. **Family lookup:** the family situation of every killer and victim, read from the saga text with chapter citations → `data/family/`
3. **Corrections:** errors found while reading the full passages (wrong killers, swapped victims, duplicates, out-of-scope killings), each with its evidence → `data/final/corrections.csv`, `data/final/aliases.csv`
4. **Blind second pass:** every killing recoded from the text, without access to pass 1 → `data/final/pass2_output_*.json`
5. **Comparison:** kin vs not kin agreed in 93.9% of killings (κ = 0.74); relation category 92.4% (κ = 0.69) → `data/final/killings_compared.csv`
6. **Tie-break:** a third pass resolved the 27 real disagreements using written coding rules → `data/final/tiebreak_output.json`
7. **Manual check:** each author checked a different random sample of 30 killings by hand (90 in total, including all 22 kin killings) → `data/review/manual_check_*.xlsx`. 82/90 attributions correct (5 partly, 3 wrong), 79/90 relations correct (14/22 among kin codings), 0/10 negatives were killings. Corrections → `data/final/manual_corrections.csv`. Indirect ties for the wide-definition robustness check → `data/final/broad_kin.csv`. Killings found outside the candidate set → `data/final/missed_killings.csv`

`data/labelled/SagaDB_family_network.xlsx` is an earlier automatic kinship extraction. It was used only
to prefill the family sheets and contains known errors. Don't use it for analysis.

## Reproduce

```bash
# 1. put the 42 Icelandic texts (*.is.txt from sagadb.org's all_sagas_text.zip) in data/raw/is/
pip install openpyxl networkx matplotlib
python scripts/make_family_sheets.py data/labelled data/family   # family sheets (overwrites!)
python scripts/merge_family_results.py      # merge data/family/work/*_output.json into them
python scripts/build_final_killings.py      # apply corrections → killings_pass1.csv
python scripts/compare_passes.py            # agreement statistics, disagreements
python scripts/finalize_killings.py         # → killings_final.csv (pre-review)
python scripts/apply_manual_checks.py       # manual corrections → killings_final.csv (original 194)
python scripts/ext_build_candidates.py      # extension: candidates with other killing words
python scripts/ext_merge.py                 # merge AI labels → data/extension/new_killings.csv
python scripts/ext_integrate.py             # verified new killings → data/final/killings_all.csv
# every analysis script reads killings_all.csv; KILLINGS=killings_final.csv python ... runs it on the original 194
```

The script that extracted the 1,048 candidate sentences is not yet in this repository (TODO).

## Analysis

```bash
python scripts/build_family_graph.py   # person table + family graph → data/analysis/
python scripts/sq1_null_model.py       # SQ1 → data/analysis/sq1_results.csv, figures/sq1_null.png
python scripts/sq2_communities.py      # SQ2 → data/analysis/sq2_results.csv, figures/sq2_ties.png
python scripts/revenge_chains.py 1     # network revenge measure → data/analysis/revenge_*_depth1.csv
python scripts/feud_analysis.py        # feuds and revenge from the text annotation → data/feuds/, figures/revenge.png
python scripts/network_stats.py        # signed network statistics (Mac Carron & Kenna style) → paper/table_network.tex, figures/network_njala.png
python scripts/descriptive_stats.py    # dataset overview → data/analysis/descriptive_stats.md, paper/table_overview.tex
```

| Result (482 killings) | Observed | Chance (within-saga victim shuffles) | p |
|---|---|---|---|
| Killings within a family group / household | 15/468 (3.2%) | 9.0% | 0.002 |
| Killer–victim direct kin tie | 12/482 (2.5%) | 4.9% | 0.008 |
| …immediate blood (parent, child, sibling) | 2 | 14.2 | 0.002 |
| …foster | 5 | 4.8 | 1.0 |
| …marriage | 5 | 4.4 | 0.87 |
| NMI family communities vs feuds | 0.839 | 0.825 | 0.002 |
| Structural balance Δ (signed network, all sagas) | 10.8% | 41.9% | 0.002 |
| Targeted revenge (network measure) | 70 | 37.9 | 0.002 |
| Revenge killings (text) | 127 (26%); 80 strike the killer himself | | |

Original 194 killings only: `data/analysis/original_only/`.

## Paper

`paper/pnas_main.tex`. Compile it in Overleaf with the *PNAS Template for Research Articles*.
