####################################################
# Python helper functions for rules
# Naming of functions: <rule_name>_<rule_parameter>[_<rule_subparameter>]>
####################################################

def combine_seqvistas_for_species_input_coverage_files(wildcards):
    """
    Return the full path to the FASTQ file corresponding to this sample
    from the config.
    """
    species = wildcards.species
    feature_library = wildcards.feature_library

    individuals = get_individuals_for_species(species)

    list_of_seqvista_files_of_individuals = []

    for individual in individuals:
        list_of_seqvista_files_of_individuals.append(f"{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_estimation.tsv")

    if not list_of_seqvista_files_of_individuals:
        raise ValueError(f"No seqvista files could be determined for species {species}.")

    return list_of_seqvista_files_of_individuals

####################################################
# Snakemake rules
####################################################

rule determine_seqvista_of_individual_bam_to_so:
    input:
        bam="{species}/processed/dynamics/{feature_library}/mapped/{individual}_{feature_library}_and_scg.sorted.bam",
        fasta="{species}/processed/dynamics/lib/{feature_library}_and_scg.suffixed.fasta"
    output:
        coverage="{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_coverage.tsv"
    log:
        "{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_bam2so.log"
    conda:
        "../../envs/python_and_r.yaml"
    message:
        "Determining seqvista coverage for {wildcards.individual} of {wildcards.species} using bam2so."
    shell:
        """
        python workflow/scripts/dynamics/seqvista/bam2so.py --infile {input.bam} --fasta {input.fasta} --outfile {output.coverage} 2> {log}
        """

rule normalize_seqvista_of_individual:
    input:
        coverage="{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_coverage.tsv"
    output:
        normalized="{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_coverage.normalized.tsv"
    conda:
        "../../envs/python_and_r.yaml"
    message:
        "Normalizing seqvista coverage for {wildcards.individual} of {wildcards.species}."
    shell:
        """
        python workflow/scripts/dynamics/seqvista/normalize-so.py --so {input.coverage} --outfile {output.normalized}
        """

rule estimate_seqvista_of_individual:
    input:
        coverage="{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_coverage.tsv"
    output:
        estimation="{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_estimation.tsv"
    conda:
        "../../envs/python_and_r.yaml"
    message:
        "Estimating seqvista for {wildcards.individual} of {wildcards.species}."
    shell:
        """
        python workflow/scripts/dynamics/seqvista/estimate-so.py --so {input.coverage} --outfile {output.estimation}
        """

rule prepare_seqvista_visualization_of_individual:
    input:
        coverage="{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_coverage.normalized.tsv",
    output:
        plotable=directory("{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_plotable")
    conda:
        "../../envs/python_and_r.yaml"
    message:
        "Preparing seqvista visualization for {wildcards.individual} of {wildcards.species}."
    shell:
        """
        python workflow/scripts/dynamics/seqvista/so2plotable.py \
            --so {input.coverage} \
            --outdir {output.plotable} \
            --seq-ids ALL \
            --sample-id {wildcards.individual}
        """

rule run_seqvista_visualization_of_individual:
    input:
        "{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_plotable"
    output:
        directory("{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_plots")
    conda:
        "../../envs/python_and_r.yaml"
    threads: 10
    params:
        log_threshhold = 25
    message:
        "Running seqvista visualization for {wildcards.individual} of {wildcards.species}."
    shell:
        """
        python workflow/scripts/dynamics/seqvista/run_plotable.py --folder {input} --outdir {output}  --log {params.log_threshhold}  --threads {threads}
        """

rule run_seqvista_visualization_of_species:
    input:
        lambda wildcards: expand(
            "{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_plotable",
            species=wildcards.species,
            feature_library=wildcards.feature_library,
            individual=get_individuals_for_species(wildcards.species))
    output:
        directory("{species}/results/dynamics/{feature_library}/seqvista/species_level/{species}_plots_facet")
    conda:
        "../../envs/python_and_r.yaml"
    threads: 10
    params:
        log_threshhold = 25
    message:
        "Running seqvista visualization for {wildcards.species}."
    shell:
        """
        python workflow/scripts/dynamics/seqvista/run_plotable.py --folders {input} --outdir {output} --log {params.log_threshhold} --threads {threads}
        """
