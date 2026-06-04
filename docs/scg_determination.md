# SCG Determination

The pastForward Dynamics pipeline normalises TE and feature-library coverage against a set of **single-copy genes (SCGs)**. This document explains how those SCGs are determined automatically when no user-provided SCG FASTA is present.

## Overview

When `pipeline.dynamics.scg_selector.execute: true` is set and no FASTA file is found in `{species}/raw/dynamics/scg/`, pastForward runs the SCG determination pipeline automatically. The result — a ranked list and a filtered FASTA of the top-scoring SCGs — is placed in `{species}/results/dynamics/scg/` and fed directly into the Dynamics mapping step.

If a FASTA is provided in `{species}/raw/dynamics/scg/`, this step is skipped entirely and the user-supplied file is used.

See [config/README.md](../config/README.md) for all configuration options (`lineage`, `num_top_scgs`, `min_length_scg`, `max_length_scg`, etc.).

---

## Why Not Just Use BUSCO Directly?

The naïve approach — using every gene BUSCO calls "Complete" — is insufficient for aDNA work. BUSCO operates on a polished modern assembly under ideal conditions and says nothing about how a gene behaves when short, degraded ancient reads are mapped onto it. The three-step pipeline below forces each candidate SCG to earn its place empirically.

---

## Step 1 — Identify Candidate SCGs via BUSCO

BUSCO is run against the species reference genome using the configured lineage database (e.g. `drosophilidae_odb12`). Genes marked **Complete** and single-copy are extracted as nucleotide sequences using the genomic coordinates in BUSCO's `full_table.tsv`.

Two length filters are applied at this stage:

| Parameter | Default | Purpose |
|---|---|---|
| `min_length_scg` | 4,000 bp | Exclude genes too short to yield reliable coverage estimates |
| `max_length_scg` | 8,000 bp | Exclude very long genes that increase mapping runtime without benefit |

The result is a FASTA library (`{species}/processed/dynamics/scg/{species}_scg_library.fasta`) used in Step 2.

---

## Step 2 — Map Reads and Compute Per-SCG Coverage Statistics

Per-individual merged reads (`reads_merged/{individual}.fastq.gz`) are mapped to the SCG library. After removing unmapped reads, the following statistics are computed per SCG per individual using `pysam.count_coverage()`:

| Metric | Description |
|---|---|
| **Min depth** | Minimum read depth at any position |
| **Average depth** | Mean read depth across all positions |
| **Median depth** | Median read depth across all positions |
| **Max depth** | Peak pile-up at any single position |
| **Covered bases** | Number of positions with depth > 0 |
| **Breadth** | Fraction of positions covered by ≥ 1 read (`covered_bases / length`) |

> `count_coverage()` counts per-base observations (A/C/G/T) rather than spanning reads. Reads with a deletion at a given position contribute 0 depth there — marginally different from `samtools depth`, but negligible for coverage estimation.

Stats are stored as per-individual JSON files in `{species}/processed/dynamics/scg/stats/`. The mapping BAMs are marked temporary and deleted once statistics are written.

---

## Step 3 — Score and Rank SCGs

`determine_scg_ranking.py` aggregates statistics across all individuals and scores each SCG on three jointly penalised criteria. SCGs are then ranked in descending order; the top `num_top_scgs` are written to the filtered FASTA used by the Dynamics pipeline.

### Breadth of coverage (`score_breadth`)

Mean breadth across all individuals. A gene that is not reliably covered along its full length is not useful for normalisation, regardless of how deep the covered portion is.

![Breadth Scoring](img/curve_breadth.png)

### Depth variation (`score_depth_variation`)

Penalises uneven depth within a gene using the ratio of `max_depth / mean_median_depth`:

```
score_depth_variation = exp(−max_variation × 0.15)
```

A true SCG should have relatively uniform depth. Genes with extreme local pile-ups — caused by repetitive elements (e.g. microsatellite tracts in introns), alignment artefacts, or paralogs missed by BUSCO — are downranked harshly.

![Depth Variation Scoring](img/curve_depth_variation.png)

Example of a microsatellite in a BUSCO gene that would be downranked by this criterion:

![Microsatellite in teplotter](img/microsatelite_example_clup_21182at33554_NC_049239.1_46153646_46163159_scg_teplotter.png)
*Coverage profile showing microsatellite pile-up (teplotter)*

![Microsatellite in IGV](img/microsatelite_example_clup_21182at33554_NC_049239.1_46153646_46163159_scg_icv.png)
*Same locus in IGV*

### Depth consistency (`score_depth_consistency`)

Penalises SCGs whose depth deviates from the global median across all SCGs. A MAD-based z-score is computed:

```
depth_deviation        = |median_depth_scg − global_median_depth| / (global_MAD + ε)
score_depth_consistency = exp(−depth_deviation / 4)
```

`global_median_depth` is the median of all per-SCG median depths; using the median rather than the mean makes this robust to the outliers being detected. `global_MAD` (Median Absolute Deviation) provides a scale-free spread measure: a `depth_deviation` of 1 means the SCG sits one MAD from the centre, a value of 5 marks a clear outlier.

SCGs that are consistently under- or over-represented relative to the bulk are likely not truly single-copy in practice. The more centrally they cluster, the more reliable they are as normalisers.

![Depth Consistency Scoring](img/curve_depth_consistency.png)

### Final score

```
score = score_breadth + score_depth_variation + score_depth_consistency
```

`score_breadth` and `score_depth_variation` evaluate each SCG individually; `score_depth_consistency` evaluates it relative to the full SCG population.

---

## Outputs

| Path | Description |
|---|---|
| `{species}/results/dynamics/scg/{species}_scg_ranked.tsv` | Full ranked table with all scoring components |
| `{species}/results/dynamics/scg/{species}_scg_ranked.json` | Detailed JSON with per-individual raw stats and scoring breakdown |
| `{species}/processed/dynamics/scg/{species}_relevant_scg.fasta` | Top-ranked SCG sequences passed to the Dynamics mapping step |
| `{species}/processed/dynamics/scg/{species}_relevant_scg.txt` | Plain list of retained SCG IDs |
| `{species}/processed/dynamics/scg/{species}_relevant_scg.bed` | BED file of retained SCG regions |
