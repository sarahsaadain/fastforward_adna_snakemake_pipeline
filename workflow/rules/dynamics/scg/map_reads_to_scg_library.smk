
####################################################
# Snakemake rules
####################################################

_scg_sel_settings      = config.get("pipeline", {}).get("dynamics", {}).get("scg_selector", {}).get("settings", {})
_dyn_settings          = config.get("pipeline", {}).get("dynamics", {}).get("mapping", {}).get("settings", {})
_dyn_mapper_default    = _dyn_settings.get("mapper", "bwa-mem2")
_scg_sel_mapper        = _scg_sel_settings.get("mapper") or _dyn_mapper_default
_SCG_BWA_ALN_DEFAULTS  = "-n 0.01 -k 2 -l 1024 -o 2"  # Oliva et al. 2021 (10.1093/bib/bbab076)
_SCG_MINIMAP2_DEFAULTS = "-ax sr"
_mapper_extra_fallback = (
    _SCG_BWA_ALN_DEFAULTS if _scg_sel_mapper == "bwa-aln" else
    (_SCG_MINIMAP2_DEFAULTS if _scg_sel_mapper == "minimap2" else "")
)
_scg_sel_mapper_extra  = (
    _scg_sel_settings.get("mapper_extra_params")
    or _dyn_settings.get("mapper_extra_params")
    or _mapper_extra_fallback
)

if _scg_sel_mapper == "minimap2":

    rule index_scg_library_for_mapping_minimap2:
        input:
            target="{species}/processed/dynamics/scg/{species}_scg_library.fasta"
        output:
            "{species}/processed/dynamics/scg/{species}_scg_library.fasta.mmi",
        log:
            "{species}/processed/dynamics/scg/{species}_scg_library_minimap2_index.log"
        message: "Indexing SCG library {input} with minimap2"
        wrapper:
            "v9.3.0/bio/minimap2/index"

    rule map_reads_to_scg_library_minimap2:
        input:
            query=["{species}/processed/reads/reads_merged/{individual}.fastq.gz"],
            target="{species}/processed/dynamics/scg/{species}_scg_library.fasta.mmi",
        output:
            temp("{species}/processed/dynamics/scg/reads_mapped/{individual}_scg_library.sorted.with_unmapped.bam"),
        log:
            "{species}/processed/dynamics/scg/reads_mapped/{individual}_scg_library_minimap2.log",
        message: "Mapping reads of {wildcards.individual} to {wildcards.species} SCG library with minimap2"
        params:
            extra=_scg_sel_mapper_extra,
            sorting="coordinate"
        threads: 10
        wrapper:
            "v9.3.0/bio/minimap2/aligner"

elif _scg_sel_mapper == "bwa-aln":

    rule index_scg_library_for_mapping_bwa_aln:
        input:
            "{species}/processed/dynamics/scg/{species}_scg_library.fasta"
        output:
            multiext("{species}/processed/dynamics/scg/{species}_scg_library.fasta", ".amb", ".ann", ".bwt", ".pac", ".sa"),
        log:
            "{species}/processed/dynamics/scg/{species}_scg_library_bwa_aln_index.log"
        message: "Indexing SCG library {input} with BWA (for BWA ALN)"
        wrapper:
            "v9.3.0/bio/bwa/index"

    rule align_reads_to_scg_library_bwa_aln:
        input:
            fastq="{species}/processed/reads/reads_merged/{individual}.fastq.gz",
            idx=multiext("{species}/processed/dynamics/scg/{species}_scg_library.fasta", ".amb", ".ann", ".bwt", ".pac", ".sa"),
        output:
            temp("{species}/processed/dynamics/scg/reads_mapped/{individual}_scg_library.sai"),
        log:
            "{species}/processed/dynamics/scg/reads_mapped/{individual}_scg_library_bwa_aln.log",
        params:
            extra=_scg_sel_mapper_extra,
        threads: 10
        wrapper:
            "v9.3.0/bio/bwa/aln"

    rule map_reads_to_scg_library_bwa_aln:
        input:
            fastq="{species}/processed/reads/reads_merged/{individual}.fastq.gz",
            sai="{species}/processed/dynamics/scg/reads_mapped/{individual}_scg_library.sai",
            idx=multiext("{species}/processed/dynamics/scg/{species}_scg_library.fasta", ".amb", ".ann", ".bwt", ".pac", ".sa"),
        output:
            temp("{species}/processed/dynamics/scg/reads_mapped/{individual}_scg_library.unsorted.with_unmapped.bam"),
        log:
            "{species}/processed/dynamics/scg/reads_mapped/{individual}_scg_library_bwa_samse.log"
        threads: 1
        wrapper:
            "v9.3.0/bio/bwa/samse"

    rule sort_scg_bam_reads:
        input:
            "{species}/processed/dynamics/scg/reads_mapped/{individual}_scg_library.unsorted.with_unmapped.bam"
        output:
            temp("{species}/processed/dynamics/scg/reads_mapped/{individual}_scg_library.sorted.with_unmapped.bam")
        message: "Sorting SCG BAM file for {input}"
        log:
            "{species}/processed/dynamics/scg/reads_mapped/{individual}_scg_library_sort_bam.log",
        threads: 8
        wrapper:
            "v9.3.0/bio/samtools/sort"

else:
    # bwa-mem2 (default)

    rule index_scg_library_for_mapping_bwa_mem2:
        input:
            "{species}/processed/dynamics/scg/{species}_scg_library.fasta"
        output:
            "{species}/processed/dynamics/scg/{species}_scg_library.fasta.0123",
            "{species}/processed/dynamics/scg/{species}_scg_library.fasta.amb",
            "{species}/processed/dynamics/scg/{species}_scg_library.fasta.ann",
            "{species}/processed/dynamics/scg/{species}_scg_library.fasta.bwt.2bit.64",
            "{species}/processed/dynamics/scg/{species}_scg_library.fasta.pac",
        log:
            "{species}/processed/dynamics/scg/{species}_scg_library_bwa_index.log"
        message: "Indexing SCG library {input} with BWA-MEM2"
        wrapper:
            "v9.3.0/bio/bwa-mem2/index"

    rule map_reads_to_scg_library_bwa_mem2:
        input:
            reads=["{species}/processed/reads/reads_merged/{individual}.fastq.gz"],
            idx=multiext("{species}/processed/dynamics/scg/{species}_scg_library.fasta", ".amb", ".ann", ".bwt.2bit.64", ".pac", ".0123"),
        output:
            temp("{species}/processed/dynamics/scg/reads_mapped/{individual}_scg_library.sorted.with_unmapped.bam"),
        log:
            "{species}/processed/dynamics/scg/reads_mapped/{individual}_scg_library_bwa.log",
        message: "Mapping reads of {wildcards.individual} to {wildcards.species} SCG library with BWA-MEM2"
        params:
            extra=_scg_sel_mapper_extra,
            sort="samtools",
            sort_order="coordinate",
        threads: 10
        wrapper:
            "v9.3.0/bio/bwa-mem2/mem"

# Remove unmapped reads — BAM is temporary (only needed for stats computation)
rule remove_unmapped_reads_from_scg_bam:
    input:
        "{species}/processed/dynamics/scg/reads_mapped/{individual}_scg_library.sorted.with_unmapped.bam"
    output:
        bam=temp("{species}/processed/dynamics/scg/reads_mapped/{individual}_scg_library.sorted.bam")
    message: "Removing unmapped reads from SCG BAM for {input}"
    params:
        extra="-b -F 4",
    threads: 2
    wrapper:
        "v9.3.0/bio/samtools/view"

# SAMTOOLS doesn't parallelize the indexing work — it only parallelizes compression/decompression.
rule index_scg_bam_reads:
    input:
        "{species}/processed/dynamics/scg/reads_mapped/{individual}_scg_library.sorted.bam"
    output:
        temp("{species}/processed/dynamics/scg/reads_mapped/{individual}_scg_library.sorted.bam.bai")
    message: "Indexing SCG BAM file for {input}"
    params:
        extra="",
    threads: 5
    wrapper:
        "v9.3.0/bio/samtools/index"
