#!/usr/bin/env python3
"""
Compute per-position indel statistics from a single .so file.

Output is a TSV with one row per indel event, intended as input for
compare_indelstats.py. For SNP statistics see so2snpstats.py.

Usage
-----
    SeqVista indelstats --so sample1.so --sample-id Dmel1933_SL07
    SeqVista indelstats --so sample1.so --sample-id Dmel1933_SL07 --outfile out.indelstats.tsv

Output columns
--------------
  seqid             sequence name
  pos               1-based start position of the indel
  sampleid          value of --sample-id
  type              ins | del
  cov               coverage at the position immediately before the indel
  indel_length      length of the insertion or deletion in bp
  indel_count       number of supporting reads
  indel_freq        indel_count / cov

Authors
-------
    Robert Kofler
    Sarah Saadain
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

from modules import SeqEntryReader

log = logging.getLogger(__name__)

_COLS = [
    "seqid", "pos", "sampleid", "type", "cov",
    "indel_length", "indel_count", "indel_freq",
]


def _indel_records(se, sample_id: str) -> list[dict]:
    """Extract one record per indel event from a SeqEntry."""
    records = []
    cov = se.cov
    for indel in se.indellist:
        p = indel.pos  # 0-based
        # coverage is taken one position before the indel, matching toSeqEntry convention
        cov_p = cov[p - 1] if p > 0 and (p - 1) < len(cov) else 0.0
        freq  = round(indel.count / cov_p, 4) if cov_p > 0 else 0.0

        records.append({
            "seqid":        se.seqname,
            "pos":          p + 1,
            "sampleid":     sample_id,
            "type":         indel.type,
            "cov":          round(cov_p, 3),
            "indel_length": indel.length,
            "indel_count":  round(indel.count, 3),
            "indel_freq":   freq,
        })
    return records


def compute_indelstats(filepath: Path, sample_id: str) -> pd.DataFrame:
    records = []
    for se in SeqEntryReader(str(filepath)):
        records.extend(_indel_records(se, sample_id))
    df = pd.DataFrame(records, columns=_COLS) if records else pd.DataFrame(columns=_COLS)
    dupes = df.duplicated(subset=["seqid", "pos", "type", "indel_length"])
    if dupes.any():
        log.warning(
            "%d duplicate indel events in %s — keeping first occurrence:\n%s",
            int(dupes.sum()), filepath.name,
            df[dupes][["seqid", "pos", "type", "indel_length"]].to_string(index=False),
        )
        df = df[~dupes].reset_index(drop=True)
    return df


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Compute per-position indel stats from a single .so file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--so", required=True, type=Path, metavar="FILE",
                        help="Input .so file.")
    parser.add_argument("--sample-id", required=True, dest="sample_id", metavar="ID",
                        help="Sample identifier written into the output (e.g. Dmel1933_SL07).")
    parser.add_argument("--outfile", "-o", type=Path, default=None, metavar="FILE",
                        help="Output TSV (default: <sample_id>.indelstats.tsv).")

    args = parser.parse_args()

    if not args.so.is_file():
        parser.error(f"File not found: {args.so}")

    outfile = args.outfile or Path(f"{args.sample_id}.indelstats.tsv")

    log.info("Parsing %s (sample_id=%s)", args.so.name, args.sample_id)
    df = compute_indelstats(args.so, args.sample_id)

    df.to_csv(outfile, sep="\t", index=False)
    log.info("Indels → %s  (%d events)", outfile, len(df))


if __name__ == "__main__":
    main()
