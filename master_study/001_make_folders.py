# ==================================================================================================
# --- Imports
# ==================================================================================================
from tree_maker import initialize
import time
import os
import itertools
import numpy as np
import yaml
import shutil
from user_defined_functions import generate_run_sh_htc, get_worst_bunch

# ==================================================================================================
# --- Initial particle distribution parameters
#
# Below, the user defines the parameters for the initial particles distribution.
# Path for the distribution config: master_study/master_jobs/000_build_distr_and_collider/config_distrib.yaml
# ==================================================================================================

# Define dictionary for the initial particle distribution
d_config_particles = {}

# Radius of the initial particle distribution
d_config_particles["r_min"] = 2
d_config_particles["r_max"] = 10
d_config_particles["n_r"] = 2 * 16 * (d_config_particles["r_max"] - d_config_particles["r_min"])

# Number of angles for the initial particle distribution
d_config_particles["n_angles"] = 5

# Number of split for parallelization
d_config_particles["n_split"] = 5

# ==================================================================================================
# --- Base collider parameters
#
# Below, the user defines the base collider parameters. That is, only the parameters that are
# subject to change are present here. More parameters can be added from the collider config.yaml,
# as needed. One needs to ensure that the remaining (default) parameters are set properly in the
# machine. Path for the collider config:
# master_study/master_jobs/000_build_distr_and_machine/config_collider.yaml
# ==================================================================================================

### Mad configuration

# Define dictionary for the Mad configuration
d_config_mad = {"beam_config": {"lhcb1": {}, "lhcb2": {}}}

# Optic file path (round or flat)
d_config_mad["optics_file"] = "acc-models-lhc/flatcc/opt_flathv_75_180_1500_thin.madx"

# Beam energy (for both beams)
beam_energy_tot = 7000
d_config_mad["beam_config"]["lhcb1"]["beam_energy_tot"] = beam_energy_tot
d_config_mad["beam_config"]["lhcb2"]["beam_energy_tot"] = beam_energy_tot

### Tune and chroma configuration

# Define dictionnary for tune and chroma
d_config_tune_and_chroma = {
    "qx": {},
    "qy": {},
    "dqx": {},
    "dqy": {},
}
for beam in ["lhcb1", "lhcb2"]:
    d_config_tune_and_chroma["qx"][beam] = 62.31
    d_config_tune_and_chroma["qy"][beam] = 60.32
    d_config_tune_and_chroma["dqx"][beam] = 5.0
    d_config_tune_and_chroma["dqy"][beam] = 5.0

# Value to be added to linear coupling knobs
d_config_tune_and_chroma["delta_cmr"] = 0.001
d_config_tune_and_chroma["delta_cmi"] = 0.0

### Knobs configuration

# Define dictionary for the knobs settings
d_config_knobs = {}

# Knobs at IPs
d_config_knobs["on_x1"] = 250
d_config_knobs["on_sep1"] = 0
d_config_knobs["on_x2"] = -170
d_config_knobs["on_sep2"] = 0.138
d_config_knobs["on_x5"] = 250
d_config_knobs["on_sep5"] = 0
d_config_knobs["on_x8h"] = 0.0
d_config_knobs["on_x8v"] = 170

# Crab cavities
d_config_knobs["on_crab1"] = -190
d_config_knobs["on_crab5"] = -190

# Octupoles
d_config_knobs["i_oct_b1"] = 60.0
d_config_knobs["i_oct_b2"] = 60.0

### leveling configuration

# Define dictionary for the leveling settings
d_config_leveling = {"ip2": {}, "ip8": {}}

# Luminosity and particles

# skip_leveling_base_collider should be set to True if:
# - the leveling will be done in the 2_tune_and_track script, i.e. a parameter belonging to group 1 is being scanned
# - the leveling is not wanted, i.e. the study is done at start of leveling
skip_leveling_base_collider = False
# Ask the user if he indeed wants to skip the leveling
if skip_leveling_base_collider:
    print(
        "You chose to skip the leveling in the base collider. This could be either because the"
        " parameter you want to scan requires recomputing leveling, or because the study you're"
        " doing is at start of leveling. Do you confirm? (y/n)"
    )
    answer = input()
    if answer != "y":
        raise ValueError(
            "You did not confirm that you want to skip the leveling in the base collider. Aborting."
        )

# Leveling parameters (ignored if skip_leveling_base_collider is True, and no leveling is done in the 2_tune_and_track script)
d_config_leveling["ip2"]["separation_in_sigmas"] = 5
d_config_leveling["ip8"]["luminosity"] = 2.0e33
# "num_colliding_bunches" is set in the 1_build_distr_and_collider script, depending on the filling scheme

### Beam beam configuration

# Define dictionary for the beam beam settings
d_config_beambeam = {"mask_with_filling_pattern": {}}

# Beam settings
d_config_beambeam["num_particles_per_bunch"] = 1.4e11
d_config_beambeam["nemitt_x"] = 2.5e-6
d_config_beambeam["nemitt_y"] = 2.5e-6

# Filling scheme (in json or csv format)
# Several filling schemes are available here: https://lpc.web.cern.ch/cgi-bin/fillTable.py?year=2023
filling_scheme_path = os.path.abspath(
    "master_jobs/filling_scheme/8b4e_1972b_1960_1178_1886_224bpi_12inj_800ns_bs200ns.json"
)

# Convert filling scheme to json if needed
if filling_scheme_path.endswith(".csv"):
    # TODO
    raise NotImplementedError(
        "The conversion of csv to json is not implemented yet. Please convert the file manually."
    )

# Add to config file
d_config_beambeam["mask_with_filling_pattern"][
    "pattern_fname"
] = filling_scheme_path  # If None, a full fill is assumed


# Bunch number (ignored if pattern_fname is None (in which case the simulation considers all bunch
# elements), must be specified otherwise)
# If the bunch number is None and pattern_name is defined, the bunch with the largest number of
# long-range interactions will be used
d_config_beambeam["mask_with_filling_pattern"]["i_bunch_b1"] = None
d_config_beambeam["mask_with_filling_pattern"]["i_bunch_b2"] = None

if d_config_beambeam["mask_with_filling_pattern"]["i_bunch_b1"] is None:
    # Case the bunch number has not been provided
    worst_bunch_b1 = get_worst_bunch(filling_scheme_path, numberOfLRToConsider=26, beam="beam_1")
    while d_config_beambeam["mask_with_filling_pattern"]["i_bunch_b1"] is None:
        bool_inp = input(
            "The bunch number for beam 1 has not been provided. Do you want to use the bunch with"
            " the largest number of long-range interactions? It is the bunch number "
            + str(worst_bunch_b1)
            + " (y/n): "
        )
        if bool_inp == "y":
            d_config_beambeam["mask_with_filling_pattern"]["i_bunch_b1"] = worst_bunch_b1
        elif bool_inp == "n":
            d_config_beambeam["mask_with_filling_pattern"]["i_bunch_b1"] = int(
                input("Please enter the bunch number for beam 1: ")
            )

if d_config_beambeam["mask_with_filling_pattern"]["i_bunch_b2"] is None:
    # For beam 2, just select the worst bunch by default, as the tracking of b2 is not available yet anyway
    print(
        "The bunch number for beam 2 has not been provided. Bunch tracking for beam 2 is not"
        " implemented yet in this script, so you can ignore this warning."
    )
    worst_bunch_b2 = get_worst_bunch(filling_scheme_path, numberOfLRToConsider=26, beam="beam_2")
    d_config_beambeam["mask_with_filling_pattern"]["i_bunch_b2"] = worst_bunch_b2

# ==================================================================================================
# --- Machine parameters being scanned
#
# Below, the user defines the grid for the machine parameters that must be scanned to find the
# optimal DA (e.g. tune, chroma, etc).
# ==================================================================================================
# Scan tune with step of 0.001 (need to round to correct for numpy numerical instabilities)
array_qx = np.round(np.arange(62.305, 62.330, 0.001), decimals=4)[:6]
array_qy = np.round(np.arange(60.305, 60.330, 0.001), decimals=4)[:6]

# In case one is doing a tune-tune scan, to decrease the size of the scan, we can ignore the
# working points too close to resonance. Otherwise just delete this variable in the loop at the end
# of the script
only_keep_upper_triangle = True
# ==================================================================================================
# --- Tracking parameters
#
# Below, the user defines the parameters for the tracking.
# ==================================================================================================
n_turns = 500
delta_max = 27.0e-5  # initial off-momentum

# ==================================================================================================
# --- Build base tree for the simulations
#
# The tree is built as a hierarchy of dictionnaries. We add a first generation (named as the
# study being done) to the root. This first generation is used set the initial particle
# distribution, and the parameters of the base machine which will later be used for simulations.
# ==================================================================================================

# Build empty tree: first generation (later added to the root), and second generation
children = {"base_collider": {"config_particles": {}, "config_collider": {}, "children": {}}}

# Add particles distribution parameters to the first generation
children["base_collider"]["config_particles"] = d_config_particles

# Add base machine parameters to the first generation
children["base_collider"]["config_collider"] = d_config_mad

# Add tunes and chromas to the first generation
children["base_collider"]["config_collider"]["config_knobs_and_tuning"] = d_config_tune_and_chroma

# Add knobs to the first generation
children["base_collider"]["config_collider"]["config_knobs_and_tuning"][
    "knob_settings"
] = d_config_knobs

# Add luminosity configuration to the first generation
children["base_collider"]["config_collider"][
    "skip_leveling_base_collider"
] = skip_leveling_base_collider
children["base_collider"]["config_collider"]["config_lumi_leveling"] = d_config_leveling

# Add beam beam configuration to the first generation
children["base_collider"]["config_collider"]["config_beambeam"] = d_config_beambeam

# ==================================================================================================
# --- Generate second generation of the tree, with the machine parameters being scanned, and
# tracking parameters being set.
# Parameters are separated in three groups, depending how they affect the configuration of the
# collider:
# - group_1: parameters that require to retune and redo the leveling, and retune again
#            (e.g. separation at the IP)
# - group_2: parameters that require to retune
#            (e.g. chromaticity, octupoles)
# - group_3: parameters that require to reconfigure bb lenses
#            (e.g. bunch_nb)
# Collider lines composition can not be reconfigured at this step, at least for now.
# ==================================================================================================
track_array = np.arange(d_config_particles["n_split"])
for idx_job, (track, qx, qy) in enumerate(itertools.product(track_array, array_qx, array_qy)):
    if only_keep_upper_triangle:
        # Ignore conditions below the upper diagonal as this can't exist in the real machine
        if qy < (qx - 2 + 0.0039):  # 0.039 instead of 0.04 to avoid rounding errors
            continue
    children["base_collider"]["children"][f"xtrack_{idx_job:04}"] = {
        "parameters_scanned": {"group_2": {"qx": float(qx), "qy": float(qy)}},
        "particle_file": f"../particles/{track:02}.parquet",
        "collider_file": f"../collider/collider.json",
        "n_turns": n_turns,
        "delta_max": delta_max,
        "log_file": f"tree_maker.log",
    }

# ==================================================================================================
# --- Simulation configuration
# ==================================================================================================
# Load the tree_maker simulation configuration
config = yaml.safe_load(open("config.yaml"))

# # Set the root children to the ones defined above
config["root"]["children"] = children


# Set miniconda environment path in the config
config["root"]["setup_env_script"] = os.getcwd() + "/../miniconda/bin/activate"

# ==================================================================================================
# --- Build tree and write it to the filesystem
# ==================================================================================================
# Define study name
study_name = "example_HL_tunescan"

# Creade folder that will contain the tree
if not os.path.exists("scans/" + study_name):
    os.makedirs("scans/" + study_name)

# Move to the folder that will contain the tree
os.chdir("scans/" + study_name)

# Create tree object
start_time = time.time()
root = initialize(config)
print("Done with the tree creation.")
print("--- %s seconds ---" % (time.time() - start_time))

# From python objects we move the nodes to the filesystem.
start_time = time.time()
root.make_folders(generate_run_sh_htc)
print("The tree folders are ready.")
print("--- %s seconds ---" % (time.time() - start_time))

# Rename log files according to study
shutil.move("tree_maker.json", f"tree_maker_{study_name}.json")
shutil.move("tree_maker.log", f"tree_maker_{study_name}.log")
