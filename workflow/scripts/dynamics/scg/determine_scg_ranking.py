import json
import numpy as np
import logging
import sys
from collections import defaultdict

stats_files = snakemake.input.stats
summary_file = snakemake.output.ranked_tsv
json_file = snakemake.output.ranked_json
log_filename = snakemake.log[0]

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stderr), logging.FileHandler(log_filename)]
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Load per-individual SCG stats
# ─────────────────────────────────────────────────────────────────────────────
logger.info(f"Loading SCG stats from {len(stats_files)} files...")

scg_stats_per_bam = []
for stats_file in stats_files:
    with open(stats_file) as f:
        scg_stats_per_bam.append(json.load(f))

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Aggregate stats across all individuals
# ─────────────────────────────────────────────────────────────────────────────
logger.info("Aggregating SCG stats across individuals...")

scg_aggregated = defaultdict(list)
for stats_file, scg_stats in zip(stats_files, scg_stats_per_bam):
    for scg, stats in scg_stats.items():
        stats["source_file"] = stats_file
        scg_aggregated[scg].append(stats)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Compute summary metrics per SCG across all individuals
# ─────────────────────────────────────────────────────────────────────────────
logger.info("Computing metrics across individuals...")
scg_summary = {}
for scg, values in scg_aggregated.items():
    logger.info(f"Processing SCG: {scg}; Number of individuals: {len(values)}")

    samples_min_depths    = [v["min_depth"] for v in values]
    samples_median_depths = [v["median_depth"] for v in values]
    samples_avg_depths    = [v["avg_depth"] for v in values]
    samples_max_depths    = [v["max_depth"] for v in values]
    length                = values[0]["length"]
    samples_covered_bases = [v["covered_bases"] for v in values]
    samples_breadths      = [v["breadth"] for v in values]
    source_files          = [v["source_file"] for v in values]

    mean_avg_depth    = np.mean(samples_avg_depths)
    mean_median_depth = np.mean(samples_median_depths)
    max_variation     = max(samples_max_depths) / mean_median_depth if mean_median_depth > 0 else 99
    mean_breadth      = np.mean(samples_breadths)

    scg_summary[scg] = {
        "samples": len(values),
        "source_files": source_files,
        "per_sample": {
            source_files[i]: {
                "min_depth":     samples_min_depths[i],
                "median_depth":  samples_median_depths[i],
                "avg_depth":     samples_avg_depths[i],
                "max_depth":     samples_max_depths[i],
                "covered_bases": samples_covered_bases[i],
                "breadth":       samples_breadths[i],
            }
            for i in range(len(values))
        },
        "length":           length,
        "min_depth":        min(samples_min_depths),
        "max_depth":        max(samples_max_depths),
        "mean_depth":       round(mean_avg_depth, 4),
        "median_depth":     round(mean_median_depth, 4),
        "per_sample_min_depths":    samples_min_depths,
        "per_sample_avg_depths":    samples_avg_depths,
        "per_sample_max_depths":    samples_max_depths,
        "per_sample_median_depths": samples_median_depths,
        "per_sample_breadths":      samples_breadths,
        "per_sample_covered_bases": samples_covered_bases,
        "max_variation":  round(max_variation, 4),
        "mean_breadth":   round(mean_breadth, 4),
    }

    logger.info(
        f"SCG metrics computed. Min depth: {scg_summary[scg]['min_depth']}; "
        f"Mean depth: {scg_summary[scg]['mean_depth']}; "
        f"Breadth: {scg_summary[scg]['mean_breadth']}"
    )

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Compute reference depth statistics across all SCGs
# ─────────────────────────────────────────────────────────────────────────────
logger.info("Normalizing metrics for scoring...")

all_median_depths = [v["median_depth"] for v in scg_summary.values()]
median_depth = np.median(all_median_depths)
mad_depth    = np.median(np.abs(np.array(all_median_depths) - median_depth))

logger.info(f"Median depth: {median_depth:.2f} (MAD: {mad_depth:.2f})")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: Score each SCG
# ─────────────────────────────────────────────────────────────────────────────
depth_variance_decay   = 0.15
depth_consistency_decay = 4

scg_scores = {}
for scg, vals in scg_summary.items():
    logger.info(f"Scoring SCG: {scg}")

    score_breadth = vals["mean_breadth"]
    score_depth_variation = np.exp(-vals["max_variation"] * depth_variance_decay)
    depth_deviation = abs(vals["median_depth"] - median_depth) / (mad_depth + 1e-9)
    score_depth_consistency = np.exp(-depth_deviation / depth_consistency_decay)
    score = score_breadth + score_depth_variation + score_depth_consistency

    logger.info(
        f"SCG: {scg}; Breadth: {score_breadth:.3f}; "
        f"Depth variation: {score_depth_variation:.3f}; "
        f"Depth consistency: {score_depth_consistency:.3f}; "
        f"Total: {score:.3f}"
    )

    scg_scores[scg] = score
    scg_summary[scg]["scoring"] = {
        "global_median_depth":    round(float(median_depth), 4),
        "global_mad_depth":       round(float(mad_depth), 4),
        "depth_variance_decay":   depth_variance_decay,
        "depth_consistency_decay": depth_consistency_decay,
        "depth_deviation":        round(float(depth_deviation), 4),
        "score_breadth":          round(float(score_breadth), 4),
        "score_depth_variation":  round(float(score_depth_variation), 4),
        "score_depth_consistency": round(float(score_depth_consistency), 4),
        "score_scg":              round(float(score), 4),
    }

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6: Rank SCGs and write outputs
# ─────────────────────────────────────────────────────────────────────────────
top_scgs = sorted(scg_scores.items(), key=lambda x: x[1], reverse=True)

logger.info("Writing TSV ranking...")
with open(summary_file, "w") as f:
    f.write("scg_name\tsamples\tmedian_depth\tdepth_variation\tmean_breadth\tscore_breadth\tscore_depth_variation\tscore_depth_consistency\tscore\n")
    for scg, score in top_scgs:
        stats = scg_summary[scg]
        s = stats["scoring"]
        f.write(
            f"{scg}\t{stats['samples']}\t{stats['median_depth']:.2f}\t"
            f"{stats['max_variation']:.2f}\t{stats['mean_breadth']:.3f}\t"
            f"{s['score_breadth']:.3f}\t{s['score_depth_variation']:.3f}\t"
            f"{s['score_depth_consistency']:.3f}\t{s['score_scg']:.3f}\n"
        )

logger.info("Writing JSON ranking...")
json_output = {
    "global_stats": {
        "median_depth": round(float(median_depth), 4),
        "mad_depth":    round(float(mad_depth), 4),
        "decay":        depth_variance_decay,
        "n_scgs":       len(scg_summary),
        "n_individuals": len(stats_files),
    },
    "scgs": {scg: scg_summary[scg] for scg, _ in top_scgs}
}

with open(json_file, "w") as f:
    json.dump(json_output, f, indent=2)

logger.info("Done.")
