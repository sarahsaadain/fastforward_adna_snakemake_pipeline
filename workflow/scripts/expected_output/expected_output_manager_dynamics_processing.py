
import logging


def get_expected_output_dynamics_processing(species):
    all_inputs = []

    if config.get("pipeline", {}).get("dynamics", {}).get("execute", True) == False:
        logging.info(f"Skipping dynamics processing for {species}. Disabled in config.")
        return []

    dyn_cfg = config.get("pipeline", {}).get("dynamics", {})
    scg_sel_cfg = dyn_cfg.get("scg_selector", {})
    scg_sel_active = scg_sel_cfg.get("execute", False)

    # ── SCG selector outputs ──────────────────────────────────────────────────
    # Requested whenever scg_selector.execute is true AND no user-provided SCG
    # exists.  This supports "only create SCGs" workflows (no feature libraries
    # required) as well as the full dynamics pipeline.
    if scg_sel_active and should_auto_determine_scg(species):
        all_inputs.append(f"{species}/results/dynamics/scg/{species}_scg_ranked.tsv")
        all_inputs.append(f"{species}/results/dynamics/scg/{species}_scg_ranked.json")

    # ── Feature-library / seqvista outputs ───────────────────────────────────
    try:
        feature_libraries = get_feature_library_ids_for_species(species)
    except Exception:
        logging.warning(
            f"No feature libraries found for {species}. "
            f"Skipping seqvista dynamics."
        )
        return all_inputs  # may still contain SCG ranking outputs

    # Determine whether an SCG library is available (user-provided or auto-determined)
    user_scgs = get_scg_library_file_list_for_species(species)
    has_scg = bool(user_scgs) or scg_sel_active

    if not has_scg:
        logging.warning(
            f"No SCG library available for {species} and scg_selector.execute is false. "
            f"Skipping seqvista dynamics. Provide a FASTA in "
            f"{species}/raw/dynamics/scg/ or set pipeline.dynamics.scg_selector.execute: true."
        )
        return all_inputs

    # Only one user-provided SCG library is supported
    if len(user_scgs) > 1:
        raise ValueError(
            f"Multiple SCG libraries provided for {species}. "
            f"Only one SCG library is supported at a time."
        )

    seqvista_settings = dyn_cfg.get("seqvista", {}).get("settings", {})
    individual_plots_mode = seqvista_settings.get("individual_plots", "plot")
    comparison_plots_mode = seqvista_settings.get("comparison_plots", "plot")

    individuals = get_individuals_for_species(species)

    all_inputs.append(f"{species}/results/dynamics/{species}_seqvista_stats_comparison.tsv")

    for feature_library in feature_libraries:

        if dyn_cfg.get("seqvista", {}).get("execute", True):

            # Species-level stats (always produced when seqvista is enabled)
            all_inputs.append(
                f"{species}/results/dynamics/{feature_library}/seqvista/species_level/{species}_{feature_library}_stats_comparison.tsv"
            )
            all_inputs.append(
                f"{species}/results/dynamics/{feature_library}/seqvista/species_level/{species}_{feature_library}_flagged_seqids.tsv"
            )

            if comparison_plots_mode == "plot":
                all_inputs.append(
                    f"{species}/results/dynamics/{feature_library}/seqvista/species_level/{species}_plots_facet/"
                )
                all_inputs.append(
                    f"{species}/results/dynamics/{feature_library}/seqvista/species_level/{species}_plotables_facet.tar.gz"
                )
            elif comparison_plots_mode == "plotable_only":
                all_inputs.append(
                    f"{species}/results/dynamics/{feature_library}/seqvista/species_level/{species}_plotables_facet.tar.gz"
                )

            for individual in individuals:
                all_inputs.append(
                    f"{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_coverage.tsv.gz"
                )
                all_inputs.append(
                    f"{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_coverage.normalized.tsv.gz"
                )
                all_inputs.append(
                    f"{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_coverage.normalized.stats.tsv"
                )

                if individual_plots_mode == "plot":
                    all_inputs.append(
                        f"{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_plotable.tar.gz"
                    )
                    all_inputs.append(
                        f"{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_plots/"
                    )
                elif individual_plots_mode == "plotable_only":
                    all_inputs.append(
                        f"{species}/results/dynamics/{feature_library}/seqvista/individual_level/{individual}_plotable.tar.gz"
                    )

        if dyn_cfg.get("pf_normalization", {}).get("execute", False):
            all_inputs.append(
                f"{species}/results/dynamics/{feature_library}/normalization/plots/"
            )
            all_inputs.append(
                f"{species}/results/dynamics/{feature_library}/normalization/{species}_normalized_coverage.combined.tsv"
            )

    return all_inputs
