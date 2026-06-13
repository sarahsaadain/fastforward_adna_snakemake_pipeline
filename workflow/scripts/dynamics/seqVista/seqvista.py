#!/usr/bin/env python3
"""
SeqVista — central command for the SeqVista analysis pipeline

Subcommands
-----------
    bam2so        Convert BAM/SAM to sequence-overview (.so) format
    normalize     Normalize .so coverage to single-copy genes
    estimate      Estimate per-entry coverage statistics from a .so file
    so2plotable   Convert .so to R-plottable format
    plot          Render .plotable files to PNG via R
    cov-stats      Summarize .so coverage to tab-delimited stats
    cov-compare    Compare coverage stats files across samples
    snp-stats      Compute per-position SNP stats from a .so file
    snp-compare    Compare per-position SNP stats across samples
    indel-stats    Compute per-position indel stats from a .so file
    indel-compare  Compare per-position indel stats across samples
  
Pass --help after any subcommand for its full usage.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from version import __version__

_SRC = Path(__file__).parent

_SUBCOMMANDS = {
    "bam2so":      (_SRC / "bam2so.py",      "Convert BAM/SAM → .so (sequence overview)"),
    "normalize":   (_SRC / "normalize-so.py", "Normalize .so coverage to single-copy genes"),
    "estimate":    (_SRC / "estimate-so.py",  "Estimate per-entry coverage statistics"),
    "so2plotable": (_SRC / "so2plotable.py",  "Convert .so → R-plottable format"),
    "plot":        (_SRC / "plot.py", "Render .plotable files to PNG via R"),
    "cov-stats":     (_SRC / "so2covstats.py",        "Summarize .so coverage to tab-delimited stats"),
    "snp-stats":     (_SRC / "so2snpstats.py",        "Compute per-position SNP stats from a .so file"),
    "indel-stats":   (_SRC / "so2indelstats.py",      "Compute per-position indel stats from a .so file"),
    "cov-compare":   (_SRC / "compare_covstats.py",   "Compare coverage stats files across samples"),
    "snp-compare":   (_SRC / "compare_snpstats.py",   "Compare per-position SNP stats across samples"),
    "indel-compare": (_SRC / "compare_indelstats.py", "Compare per-position indel stats across samples"),
}


def main():
    parser = argparse.ArgumentParser(
        prog="SeqVista",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--version", action="version", version=f"SeqVista {__version__}")

    sub = parser.add_subparsers(dest="subcommand", metavar="<subcommand>")
    for name, (_, help_text) in _SUBCOMMANDS.items():
        sub.add_parser(name, help=help_text, add_help=False)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args, remaining = parser.parse_known_args()

    if args.subcommand is None:
        parser.print_help()
        sys.exit(1)

    script, _ = _SUBCOMMANDS[args.subcommand]
    result = subprocess.run([sys.executable, str(script)] + remaining)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
