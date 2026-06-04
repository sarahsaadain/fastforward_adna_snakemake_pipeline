
# SCG selector rules
include: "dynamics/scg/identify_scg_with_busco.smk"
include: "dynamics/scg/map_reads_to_scg_library.smk"
include: "dynamics/scg/rank_scg.smk"

# Seqvista / feature-library dynamics rules
include: "dynamics/seqvista/prepare_libraries.smk"
include: "dynamics/seqvista/map_reads_to_library.smk"
include: "dynamics/seqvista/determine_normalization_seqvista.smk"
include: "dynamics/seqvista/determine_normalization.smk"
