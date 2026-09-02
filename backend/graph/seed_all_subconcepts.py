"""
seed_all_subconcepts.py
=======================
Seeds subconcepts for ALL Grade 8-10 Science + Maths chapters.
Run AFTER seed_data.py has already seeded the Chapter nodes.

Usage:
    python -m backend.graph.seed_all_subconcepts            # all chapters
    python -m backend.graph.seed_all_subconcepts --chapter ch_g9_motion

Each chapter is defined as:
    (chapter_id, concept_id, [(sc_id, name, bloom, vark), ...], prereq_pairs)

Positions are auto-generated using a standard 6-node DAG layout
(viewBox "0 0 340 510"). Override by passing explicit (x, y) in the tuple.

Bloom levels: Remember | Understand | Apply | Analyse | Evaluate
VARK hints:   V | A | R | K
"""

import asyncio
import sys
from neo4j import AsyncGraphDatabase
from backend.config.settings import get_settings
from backend.graph.schema import create_constraints

# ─────────────────────────────────────────────────────────────────────────────
# POSITION HELPERS
# ─────────────────────────────────────────────────────────────────────────────
# Standard DAG positions keyed by number of subconcepts
_POS = {
    4: [(170,52),(85,170),(255,170),(170,360)],
    5: [(170,52),(85,160),(255,160),(85,340),(255,340)],
    6: [(170,52),(85,160),(255,160),(85,300),(255,300),(170,420)],
    7: [(170,52),(85,140),(255,140),(170,240),(85,340),(255,340),(170,450)],
    8: [(170,52),(85,140),(255,140),(85,240),(255,240),(85,360),(255,360),(170,460)],
}
_PREREQ = {
    4: [(0,1),(0,2),(1,3),(2,3)],
    5: [(0,1),(0,2),(1,3),(2,4)],
    6: [(0,1),(0,2),(1,3),(2,4),(3,5),(4,5)],
    7: [(0,1),(0,2),(1,3),(2,3),(3,4),(3,5),(4,6),(5,6)],
    8: [(0,1),(0,2),(1,3),(2,4),(3,5),(4,6),(5,7),(6,7)],
}

def _build(ch_id: str, con_suffix: str, scs: list, custom_prereqs=None):
    """Build (chapter_id, concept_id, subconcepts, prerequisites) from compact data."""
    n      = len(scs)
    pos    = _POS.get(n, _POS[6])[:n]
    preqs  = custom_prereqs if custom_prereqs is not None else _PREREQ.get(n, _PREREQ[6])
    con_id = f"con_{con_suffix}"
    subconcepts = []
    for i, item in enumerate(scs):
        sc_id, name, bloom, vark = item[:4]
        x, y = item[4] if len(item) > 4 else pos[i]
        subconcepts.append((con_id, {
            "id": sc_id, "name": name,
            "bloom_target": bloom, "vark_hint": vark,
            "map_x": float(x), "map_y": float(y),
        }))
    prereqs = [(scs[a][0], scs[b][0]) for a, b in preqs if a < n and b < n]
    return (ch_id, [{"id": con_id, "name": name.title(), "weight": 1.0}], subconcepts, prereqs)


# ─────────────────────────────────────────────────────────────────────────────
# GRADE 8 — remaining chapters (24 chapters not in seed_chapters.py)
# ─────────────────────────────────────────────────────────────────────────────
G8 = [

  _build("ch_crop_production","crop",[
    ("sc_crop_types",       "Types of Crops",               "Remember",  "V"),
    ("sc_crop_prep",        "Soil Preparation",             "Understand","K"),
    ("sc_crop_sowing",      "Sowing and Irrigation",        "Understand","K"),
    ("sc_crop_protection",  "Crop Protection",              "Apply",     "R"),
    ("sc_crop_harvest",     "Harvesting and Storage",       "Apply",     "K"),
    ("sc_crop_improve",     "Crop Improvement Methods",     "Analyse",   "R"),
  ]),

  _build("ch_microorganisms","micro",[
    ("sc_micro_types",      "Types of Microorganisms",      "Remember",  "V"),
    ("sc_micro_useful",     "Useful Microorganisms",        "Understand","R"),
    ("sc_micro_harmful",    "Harmful Microorganisms",       "Understand","R"),
    ("sc_micro_disease",    "Diseases by Microorganisms",   "Apply",     "R"),
    ("sc_micro_food",       "Microorganisms in Food",       "Apply",     "K"),
    ("sc_micro_control",    "Controlling Microorganisms",   "Analyse",   "K"),
  ]),

  _build("ch_synthetic_fibres","fibre",[
    ("sc_fibre_natural",    "Natural vs Synthetic Fibres",  "Remember",  "V"),
    ("sc_fibre_types",      "Types of Synthetic Fibres",    "Understand","V"),
    ("sc_fibre_plastics",   "Types of Plastics",            "Understand","R"),
    ("sc_fibre_props",      "Properties of Synthetics",     "Apply",     "K"),
    ("sc_fibre_uses",       "Uses and Applications",        "Apply",     "K"),
    ("sc_fibre_hazards",    "Hazards of Synthetics",        "Analyse",   "R"),
  ]),

  _build("ch_metals_nonmetals","metals8",[
    ("sc_metal_props",      "Properties of Metals",         "Remember",  "V"),
    ("sc_nonmetal_props",   "Properties of Non-Metals",     "Understand","V"),
    ("sc_metal_uses",       "Uses of Metals",               "Apply",     "K"),
    ("sc_metal_reactions",  "Reactions of Metals",          "Apply",     "K"),
    ("sc_alloys",           "Alloys and Their Uses",        "Analyse",   "R"),
    ("sc_corrosion8",       "Corrosion and Prevention",     "Analyse",   "K"),
  ]),

  _build("ch_coal_petroleum","fossil",[
    ("sc_fossil_fuels",     "What are Fossil Fuels",        "Remember",  "R"),
    ("sc_coal_form",        "Formation of Coal",            "Understand","V"),
    ("sc_petro_form",       "Formation of Petroleum",       "Understand","V"),
    ("sc_coal_products",    "Products from Coal",           "Apply",     "R"),
    ("sc_petro_refine",     "Petroleum Refining",           "Apply",     "V"),
    ("sc_natural_gas",      "Natural Gas and Conservation", "Analyse",   "R"),
  ]),

  _build("ch_combustion","combust",[
    ("sc_combust_what",     "What is Combustion",           "Remember",  "K"),
    ("sc_combust_types",    "Types of Combustion",          "Understand","V"),
    ("sc_fire_triangle",    "Fire Triangle",                "Understand","V"),
    ("sc_fuels8",           "Types of Fuels",               "Apply",     "R"),
    ("sc_flame_struct",     "Structure of a Flame",         "Apply",     "V"),
    ("sc_fire_control",     "Fire Control and Extinguishers","Analyse",  "K"),
  ]),

  _build("ch_conservation","conserve",[
    ("sc_biodiversity",     "Biodiversity and Importance",  "Remember",  "V"),
    ("sc_deforestation",    "Deforestation and Effects",    "Understand","R"),
    ("sc_wildlife",         "Wildlife Conservation",        "Understand","V"),
    ("sc_biosphere",        "Biosphere Reserves",           "Apply",     "R"),
    ("sc_red_data",         "Endangered Species",           "Apply",     "R"),
    ("sc_migration",        "Migration and Conservation",   "Analyse",   "R"),
  ]),

  _build("ch_cell","cell8",[
    ("sc_cell8_discovery",  "Cell Theory",                  "Remember",  "R"),
    ("sc_cell8_types",      "Prokaryotic vs Eukaryotic",    "Understand","V"),
    ("sc_cell8_struct",     "Cell Structure and Organelles","Understand","V"),
    ("sc_cell8_func",       "Organelle Functions",          "Apply",     "R"),
    ("sc_plant_animal8",    "Plant vs Animal Cell",         "Apply",     "V"),
    ("sc_cell8_div",        "Cell Division Overview",       "Analyse",   "R"),
  ]),

  _build("ch_reproduction","repro8",[
    ("sc_repro_types",      "Types of Reproduction",        "Remember",  "R"),
    ("sc_sexual_repro",     "Sexual Reproduction",          "Understand","V"),
    ("sc_fertilisation",    "Fertilisation and Development","Understand","V"),
    ("sc_embryo",           "Embryo and Foetus Development","Apply",     "R"),
    ("sc_viviparous",       "Viviparous vs Oviparous",      "Apply",     "V"),
    ("sc_asexual_animals",  "Asexual Reproduction",         "Analyse",   "R"),
  ]),

  _build("ch_adolescence","adol",[
    ("sc_puberty",          "Changes at Puberty",           "Remember",  "R"),
    ("sc_hormones8",        "Role of Hormones",             "Understand","R"),
    ("sc_secondary_sex",    "Secondary Sexual Characters",  "Understand","V"),
    ("sc_repro_health",     "Reproductive Health",          "Apply",     "R"),
    ("sc_nutrition_adol",   "Nutrition during Adolescence", "Apply",     "K"),
  ]),

  _build("ch_chemical_effects","chemeff",[
    ("sc_conductors8",      "Conductors and Insulators",    "Remember",  "K"),
    ("sc_electrolysis8",    "Electrolysis Basics",          "Understand","V"),
    ("sc_electroplating",   "Electroplating",               "Apply",     "K"),
    ("sc_led_tester",       "LED Tester Applications",      "Apply",     "K"),
    ("sc_chem_changes",     "Chemical Changes by Current",  "Apply",     "R"),
    ("sc_industrial_apps",  "Industrial Applications",      "Analyse",   "R"),
  ]),

  _build("ch_natural_phenomena","natphen",[
    ("sc_static_elec",      "Static Electricity",           "Remember",  "K"),
    ("sc_thunder_light",    "Thunder and Lightning",        "Understand","V"),
    ("sc_earthquake8",      "Earthquakes",                  "Understand","V"),
    ("sc_richter",          "Richter Scale",                "Apply",     "R"),
    ("sc_eq_safety",        "Earthquake Safety",            "Apply",     "K"),
    ("sc_lightning_prot",   "Lightning Protection",         "Analyse",   "K"),
  ]),

  _build("ch_light","light8",[
    ("sc_light_reflect8",   "Reflection of Light",          "Remember",  "V"),
    ("sc_mirrors8",         "Laws of Reflection and Mirrors","Understand","V"),
    ("sc_refraction8",      "Refraction of Light",          "Understand","V"),
    ("sc_lenses8",          "Lenses and their Types",       "Apply",     "V"),
    ("sc_dispersion8",      "Dispersion of Light",          "Apply",     "V"),
    ("sc_human_eye8",       "The Human Eye",                "Analyse",   "R"),
  ]),

  _build("ch_stars_solar","stars",[
    ("sc_night_sky",        "Night Sky and Celestial Objects","Remember", "V"),
    ("sc_moon_phases",      "Moon and its Phases",          "Understand","V"),
    ("sc_stars8",           "Stars and Constellations",     "Understand","V"),
    ("sc_solar_system8",    "The Solar System",             "Apply",     "V"),
    ("sc_sun8",             "Sun and Solar Energy",         "Apply",     "R"),
    ("sc_beyond_solar",     "Beyond the Solar System",      "Analyse",   "V"),
  ]),

  _build("ch_pollution","pollut",[
    ("sc_air_pollut",       "Air Pollution",                "Remember",  "R"),
    ("sc_air_pollutants",   "Air Pollutants and Sources",   "Understand","R"),
    ("sc_water_pollut",     "Water Pollution",              "Understand","R"),
    ("sc_water_sources",    "Water Pollutants and Sources", "Apply",     "R"),
    ("sc_pollut_effects",   "Effects on Health",            "Apply",     "R"),
    ("sc_pollut_prevent",   "Pollution Prevention",         "Analyse",   "K"),
  ]),

  # ── Grade 8 Maths ──────────────────────────────────────────────────────────
  _build("ch_rational_numbers","rational",[
    ("sc_rational_intro",   "Rational Numbers Basics",      "Remember",  "R"),
    ("sc_rational_numline", "Number Line Representation",   "Understand","V"),
    ("sc_rational_ops",     "Operations on Rationals",      "Apply",     "K"),
    ("sc_rational_props",   "Properties of Rationals",      "Apply",     "R"),
    ("sc_rational_between", "Rationals Between Two Numbers","Analyse",   "R"),
  ]),

  _build("ch_linear_equations","lineq8",[
    ("sc_lineq8_intro",     "Linear Equations Basics",      "Remember",  "R"),
    ("sc_lineq8_solve",     "Solving Linear Equations",     "Understand","R"),
    ("sc_lineq8_trans",     "Transposing Method",           "Apply",     "K"),
    ("sc_lineq8_word",      "Word Problems",                "Apply",     "K"),
    ("sc_lineq8_apps",      "Applications",                 "Analyse",   "K"),
  ]),

  _build("ch_quadrilaterals","quad8",[
    ("sc_polygon_intro",    "Introduction to Polygons",     "Remember",  "V"),
    ("sc_quad8_types",      "Types of Quadrilaterals",      "Understand","V"),
    ("sc_angle_sum8",       "Angle Sum Property",           "Apply",     "R"),
    ("sc_parallelogram8",   "Properties of Parallelogram",  "Apply",     "R"),
    ("sc_special_quads8",   "Special Quadrilaterals",       "Analyse",   "V"),
  ]),

  _build("ch_practical_geometry","practgeo",[
    ("sc_pgeo_basics",      "Construction Basics",          "Remember",  "K"),
    ("sc_pgeo_quad",        "Constructing Quadrilaterals",  "Understand","K"),
    ("sc_pgeo_special",     "Special Constructions",        "Apply",     "K"),
    ("sc_pgeo_rough",       "Rough Figure and Steps",       "Apply",     "R"),
  ]),

  _build("ch_data_handling","datah",[
    ("sc_datah_collect",    "Data Collection and Organisation","Remember","R"),
    ("sc_datah_bar",        "Bar Graphs and Histograms",    "Understand","V"),
    ("sc_datah_pie",        "Pie Charts",                   "Understand","V"),
    ("sc_datah_avg",        "Mean, Median and Mode",        "Apply",     "K"),
    ("sc_datah_prob",       "Introduction to Probability",  "Apply",     "R"),
  ]),

  _build("ch_squares_roots","sqroots",[
    ("sc_perfect_sq",       "Perfect Squares",              "Remember",  "R"),
    ("sc_sq_patterns",      "Patterns in Squares",          "Understand","V"),
    ("sc_sqrt_methods",     "Methods to Find Square Root",  "Apply",     "K"),
    ("sc_sqrt_division",    "Division Method",              "Apply",     "K"),
    ("sc_sqrt_pyth",        "Pythagorean Triplets",         "Analyse",   "R"),
  ]),

  _build("ch_cubes_roots","cbroots",[
    ("sc_perfect_cubes",    "Perfect Cubes",                "Remember",  "R"),
    ("sc_cube_patterns",    "Patterns in Cubes",            "Understand","V"),
    ("sc_cube_root8",       "Cube Root",                    "Apply",     "K"),
    ("sc_cube_prime",       "Prime Factorisation Method",   "Apply",     "K"),
    ("sc_cube_apps",        "Applications",                 "Analyse",   "R"),
  ]),

  _build("ch_comparing_quantities","compq",[
    ("sc_ratio_prop8",      "Ratio and Proportion",         "Remember",  "R"),
    ("sc_percent8",         "Percentages",                  "Understand","K"),
    ("sc_profit_loss8",     "Profit and Loss",              "Apply",     "K"),
    ("sc_discount8",        "Discount and Tax",             "Apply",     "K"),
    ("sc_compound_int",     "Compound Interest",            "Analyse",   "K"),
  ]),

  _build("ch_algebraic_expressions","algexp",[
    ("sc_algexp_intro",     "Algebraic Expressions Basics", "Remember",  "R"),
    ("sc_algexp_mult",      "Multiplication of Expressions","Understand","K"),
    ("sc_identities8",      "Standard Identities",          "Apply",     "R"),
    ("sc_identity_apps8",   "Applying Identities",          "Apply",     "K"),
    ("sc_factor_intro8",    "Introduction to Factorisation","Analyse",   "R"),
  ]),

  _build("ch_solid_shapes","solid",[
    ("sc_3d_shapes8",       "3D Shapes and Properties",     "Remember",  "V"),
    ("sc_nets8",            "Nets of 3D Shapes",            "Understand","V"),
    ("sc_euler8",           "Euler's Formula",              "Apply",     "R"),
    ("sc_mapping8",         "Mapping 3D to 2D",             "Apply",     "V"),
  ]),

  _build("ch_mensuration","mensur",[
    ("sc_perimeter8",       "Perimeter of Rectilinear Figures","Remember","K"),
    ("sc_area_trap",        "Area of Trapezoid and Polygon","Understand","K"),
    ("sc_area_circle8",     "Area of Circle",               "Apply",     "K"),
    ("sc_sa_cuboid",        "Surface Area of Cuboid",       "Apply",     "K"),
    ("sc_sa_cylinder",      "Surface Area of Cylinder",     "Apply",     "K"),
    ("sc_volume8",          "Volume of Cuboid and Cylinder","Analyse",   "K"),
  ]),

  _build("ch_exponents","expon",[
    ("sc_powers_intro",     "Powers and Exponents",         "Remember",  "R"),
    ("sc_laws_exp",         "Laws of Exponents",            "Understand","R"),
    ("sc_neg_exp",          "Negative Exponents",           "Apply",     "K"),
    ("sc_sci_notation",     "Scientific Notation",          "Apply",     "R"),
    ("sc_compare_large",    "Comparing Large Numbers",      "Analyse",   "R"),
  ]),

  _build("ch_proportions","propn",[
    ("sc_direct_prop",      "Direct Proportion",            "Remember",  "R"),
    ("sc_direct_probs",     "Direct Proportion Problems",   "Understand","K"),
    ("sc_inverse_prop",     "Inverse Proportion",           "Apply",     "K"),
    ("sc_inverse_probs",    "Inverse Proportion Problems",  "Apply",     "K"),
    ("sc_propn_apps",       "Real-world Applications",      "Analyse",   "K"),
  ]),

  _build("ch_factorisation","factor8",[
    ("sc_factor8_intro",    "Factorisation Introduction",   "Remember",  "R"),
    ("sc_factor8_common",   "Common Factor Method",         "Understand","K"),
    ("sc_factor8_identity", "Using Identities",             "Apply",     "K"),
    ("sc_factor8_tri",      "Trinomial Factorisation",      "Apply",     "K"),
    ("sc_div_poly8",        "Division of Polynomials",      "Analyse",   "K"),
  ]),

  _build("ch_intro_graphs","ingraph",[
    ("sc_graph_intro8",     "Graphs and Their Uses",        "Remember",  "V"),
    ("sc_bar_line8",        "Bar and Line Graphs",          "Understand","V"),
    ("sc_pie_graph8",       "Pie Graphs",                   "Apply",     "V"),
    ("sc_lin_graph8",       "Linear Graphs",                "Apply",     "R"),
    ("sc_graph_analysis8",  "Interpreting Graphs",          "Analyse",   "V"),
  ]),

  _build("ch_playing_numbers","playnums",[
    ("sc_num_patterns",     "Number Patterns and Games",    "Remember",  "R"),
    ("sc_divisibility8",    "Divisibility Rules",           "Understand","R"),
    ("sc_letter_digits",    "Letters for Digits",           "Apply",     "K"),
    ("sc_test_divis",       "Tests of Divisibility",        "Apply",     "K"),
  ]),
]

# ─────────────────────────────────────────────────────────────────────────────
# GRADE 9 — Science (14 chapters)
# ─────────────────────────────────────────────────────────────────────────────
G9_SCI = [

  _build("ch_g9_matter","matter9",[
    ("sc_states_matter",    "States of Matter",             "Remember",  "V"),
    ("sc_matter_props",     "Properties of States",         "Understand","R"),
    ("sc_interconversion",  "Interconversion of States",    "Understand","V"),
    ("sc_evaporation9",     "Evaporation and Factors",      "Apply",     "K"),
    ("sc_latent_heat9",     "Latent Heat",                  "Apply",     "R"),
    ("sc_plasma9",          "Plasma and BEC",               "Analyse",   "R"),
  ]),

  _build("ch_g9_matter_pure","matterpure",[
    ("sc_pure_mixture",     "Pure Substances vs Mixtures",  "Remember",  "R"),
    ("sc_solutions9",       "Solutions and their Types",    "Understand","R"),
    ("sc_separation9",      "Separation Techniques",        "Understand","K"),
    ("sc_phys_chem9",       "Physical and Chemical Changes","Apply",     "K"),
    ("sc_compounds_elems",  "Compounds vs Elements",        "Apply",     "R"),
    ("sc_colloids9",        "Colloids and Suspensions",     "Analyse",   "V"),
  ]),

  _build("ch_g9_atoms","atoms9",[
    ("sc_dalton9",          "Dalton's Atomic Theory",       "Remember",  "R"),
    ("sc_atoms_mols9",      "Atoms and Molecules",          "Understand","R"),
    ("sc_atomic_mass9",     "Atomic Mass",                  "Understand","R"),
    ("sc_mole9",            "Mole Concept",                 "Apply",     "K"),
    ("sc_formula_mass9",    "Formula and Molecular Mass",   "Apply",     "K"),
    ("sc_avogadro9",        "Avogadro's Number",            "Analyse",   "R"),
  ]),

  _build("ch_g9_atom_structure","atomstruct",[
    ("sc_e_discovery",      "Discovery of Electrons and Protons","Remember","R"),
    ("sc_atomic_models9",   "Atomic Models",                "Understand","V"),
    ("sc_neutron9",         "Neutron Discovery",            "Understand","R"),
    ("sc_at_num_mass",      "Atomic Number and Mass Number","Apply",     "R"),
    ("sc_isotopes9",        "Isotopes and Isobars",         "Apply",     "R"),
    ("sc_elec_config9",     "Electronic Configuration",     "Analyse",   "R"),
  ]),

  _build("ch_g9_cell","cell9",[
    ("sc_cell9_intro",      "Cell as a Basic Unit",         "Remember",  "R"),
    ("sc_cell9_types",      "Prokaryotic vs Eukaryotic",    "Understand","V"),
    ("sc_nucleus9",         "The Nucleus and DNA",          "Understand","R"),
    ("sc_organelles9",      "Cell Organelles and Functions","Apply",     "R"),
    ("sc_cell9_membrane",   "Cell Membrane and Wall",       "Apply",     "V"),
    ("sc_osmosis9",         "Osmosis and Diffusion",        "Analyse",   "K"),
  ]),

  _build("ch_g9_tissues","tissues9",[
    ("sc_tissue_intro9",    "What are Tissues",             "Remember",  "R"),
    ("sc_plant_tissues9",   "Plant Tissues",                "Understand","V"),
    ("sc_animal_tissues9",  "Animal Tissues",               "Understand","V"),
    ("sc_meristematic9",    "Meristematic Tissue",          "Apply",     "R"),
    ("sc_epithelial9",      "Epithelial and Connective",    "Apply",     "R"),
    ("sc_musc_nervous9",    "Muscular and Nervous Tissues", "Analyse",   "R"),
  ]),

  _build("ch_g9_motion","motion9",[
    ("sc_motion_rest9",     "Motion and Rest",              "Remember",  "V"),
    ("sc_dist_displace9",   "Distance and Displacement",    "Understand","R"),
    ("sc_speed_vel9",       "Speed and Velocity",           "Understand","R"),
    ("sc_acceleration9",    "Acceleration",                 "Apply",     "K"),
    ("sc_eq_motion9",       "Equations of Motion",          "Apply",     "K"),
    ("sc_graphs_motion9",   "Distance-Time and v-t Graphs", "Analyse",   "V"),
  ]),

  _build("ch_g9_force_laws","forcelaws",[
    ("sc_newton1st",        "Newton's First Law",           "Remember",  "R"),
    ("sc_inertia9",         "Inertia and Mass",             "Understand","K"),
    ("sc_newton2nd",        "Newton's Second Law",          "Apply",     "K"),
    ("sc_fma9",             "F = ma Problems",              "Apply",     "K"),
    ("sc_newton3rd",        "Newton's Third Law",           "Apply",     "K"),
    ("sc_momentum9",        "Conservation of Momentum",     "Analyse",   "R"),
  ]),

  _build("ch_g9_gravitation","gravit9",[
    ("sc_gravit_law",       "Universal Law of Gravitation", "Remember",  "R"),
    ("sc_g_const9",         "Gravitational Constant G",     "Understand","R"),
    ("sc_free_fall9",       "Free Fall and g",              "Apply",     "K"),
    ("sc_mass_weight9",     "Mass vs Weight",               "Apply",     "K"),
    ("sc_buoyancy9",        "Buoyancy and Archimedes",      "Apply",     "K"),
    ("sc_rel_density9",     "Relative Density",             "Analyse",   "R"),
  ]),

  _build("ch_g9_work_energy","workenergy",[
    ("sc_work_done9",       "Work Done",                    "Remember",  "K"),
    ("sc_energy_types9",    "Types of Energy",              "Understand","R"),
    ("sc_kinetic9",         "Kinetic Energy",               "Apply",     "K"),
    ("sc_potential9",       "Potential Energy",             "Apply",     "K"),
    ("sc_energy_cons9",     "Conservation of Energy",       "Analyse",   "R"),
    ("sc_power9",           "Power and Commercial Unit",    "Analyse",   "K"),
  ]),

  _build("ch_g9_sound","sound9",[
    ("sc_sound9_prod",      "Production of Sound",          "Remember",  "K"),
    ("sc_sound9_prop",      "Propagation and Medium",       "Understand","R"),
    ("sc_sound9_chars",     "Characteristics of Sound",     "Understand","R"),
    ("sc_echo9",            "Reflection of Sound and Echo", "Apply",     "K"),
    ("sc_hear_range9",      "Hearing Range and Ultrasound", "Apply",     "R"),
    ("sc_sonar9",           "SONAR and Applications",       "Analyse",   "R"),
  ]),

  _build("ch_g9_health","health9",[
    ("sc_health9_intro",    "Health and Disease",           "Remember",  "R"),
    ("sc_infectious9",      "Infectious Diseases",          "Understand","R"),
    ("sc_transmission9",    "Disease Transmission",         "Understand","R"),
    ("sc_immunity9",        "Immune System",                "Apply",     "R"),
    ("sc_treatment9",       "Treatment and Prevention",     "Apply",     "K"),
    ("sc_vaccination9",     "Vaccination and Antibiotics",  "Analyse",   "R"),
  ]),

  _build("ch_g9_natural_resources","natres9",[
    ("sc_atmosphere9",      "The Atmosphere",               "Remember",  "V"),
    ("sc_water_cycle9",     "Water Cycle",                  "Understand","V"),
    ("sc_nitrogen_cycle9",  "Nitrogen Cycle",               "Understand","V"),
    ("sc_carbon_cycle9",    "Carbon Cycle",                 "Apply",     "R"),
    ("sc_ozone9",           "Ozone Layer",                  "Apply",     "R"),
    ("sc_greenhouse9",      "Greenhouse Effect",            "Analyse",   "R"),
  ]),

  _build("ch_g9_food_resources","foodres9",[
    ("sc_food9_intro",      "Food Resources and Demand",    "Remember",  "R"),
    ("sc_crop_improve9",    "Crop Improvement Techniques",  "Understand","R"),
    ("sc_crop_prod9",       "Crop Production Management",   "Apply",     "K"),
    ("sc_animal_husb9",     "Animal Husbandry",             "Apply",     "K"),
    ("sc_fishing9",         "Fishing and Marine Resources", "Apply",     "K"),
    ("sc_bee_mushroom9",    "Bee Keeping and Mushrooms",    "Analyse",   "K"),
  ]),
]

# ─────────────────────────────────────────────────────────────────────────────
# GRADE 9 — Maths (15 chapters)
# ─────────────────────────────────────────────────────────────────────────────
G9_MATH = [

  _build("ch_g9_number_systems","numsys9",[
    ("sc_nat_int9",         "Natural Numbers and Integers", "Remember",  "R"),
    ("sc_rational9",        "Rational Numbers Revision",    "Understand","R"),
    ("sc_irrational9",      "Irrational Numbers",           "Understand","R"),
    ("sc_real9",            "Real Numbers",                 "Apply",     "R"),
    ("sc_surds9",           "Surds and Simplification",     "Apply",     "K"),
    ("sc_laws_rad9",        "Laws of Radicals",             "Analyse",   "K"),
  ]),

  _build("ch_g9_polynomials","poly9",[
    ("sc_poly9_intro",      "Introduction to Polynomials",  "Remember",  "R"),
    ("sc_poly9_degree",     "Degree and Types",             "Understand","R"),
    ("sc_poly9_zeros",      "Zeros of Polynomials",         "Understand","R"),
    ("sc_remainder9",       "Remainder Theorem",            "Apply",     "K"),
    ("sc_factor_thm9",      "Factor Theorem",               "Apply",     "K"),
    ("sc_alg_identity9",    "Algebraic Identities",         "Analyse",   "R"),
  ]),

  _build("ch_g9_coordinate_geo","coordgeo9",[
    ("sc_cartesian9",       "Cartesian System",             "Remember",  "V"),
    ("sc_quadrants9",       "Quadrants and Axes",           "Understand","V"),
    ("sc_plotting9",        "Plotting Points",              "Apply",     "K"),
    ("sc_dist_formula9",    "Distance Formula",             "Apply",     "K"),
  ]),

  _build("ch_g9_linear_2var","lin2var9",[
    ("sc_lin2var9_intro",   "Equations in Two Variables",   "Remember",  "R"),
    ("sc_lin2var9_sols",    "Solutions of Linear Equations","Understand","R"),
    ("sc_lin2var9_graph",   "Graph of Linear Equation",     "Apply",     "V"),
    ("sc_lin2var9_real",    "Real-world Problems",          "Apply",     "K"),
  ]),

  _build("ch_g9_euclid","euclid9",[
    ("sc_euclid9_hist",     "Euclid's Approach",            "Remember",  "R"),
    ("sc_axioms9",          "Axioms and Postulates",        "Understand","R"),
    ("sc_theorems9",        "Theorems and Proof",           "Apply",     "R"),
    ("sc_equivalent9",      "Equivalent Versions",          "Analyse",   "R"),
  ]),

  _build("ch_g9_lines_angles","linang9",[
    ("sc_linang9_basic",    "Basic Terms and Definitions",  "Remember",  "R"),
    ("sc_pairs_ang9",       "Pairs of Angles",              "Understand","V"),
    ("sc_parallel9",        "Parallel Lines and Transversal","Understand","V"),
    ("sc_angle_thm9",       "Angle Theorems",               "Apply",     "R"),
    ("sc_angle_probs9",     "Angle Problems",               "Apply",     "K"),
  ]),

  _build("ch_g9_triangles","tri9",[
    ("sc_congruence9",      "Congruence of Triangles",      "Remember",  "R"),
    ("sc_sss_sas9",         "SSS, SAS, ASA, AAS Rules",     "Understand","V"),
    ("sc_rhs9",             "RHS Rule",                     "Apply",     "K"),
    ("sc_tri_ineq9",        "Triangle Inequalities",        "Apply",     "R"),
    ("sc_tri_props9",       "Properties of Triangles",      "Analyse",   "R"),
  ]),

  _build("ch_g9_quadrilaterals","quad9",[
    ("sc_quad9_angle",      "Angle Sum Property",           "Remember",  "R"),
    ("sc_parallelgm9",      "Properties of Parallelogram",  "Understand","V"),
    ("sc_midpoint9",        "Mid-Point Theorem",            "Apply",     "R"),
    ("sc_quad9_cond",       "Quadrilateral Conditions",     "Apply",     "K"),
    ("sc_rhombus_rect9",    "Rhombus, Rectangle, Square",   "Analyse",   "V"),
  ]),

  _build("ch_g9_areas","areas9",[
    ("sc_areas9_basic",     "Area Basics",                  "Remember",  "K"),
    ("sc_parallelgm_area9", "Area of Parallelogram",        "Understand","K"),
    ("sc_tri_area9",        "Area of Triangle",             "Apply",     "K"),
    ("sc_same_base9",       "Figures on Same Base",         "Apply",     "R"),
    ("sc_area_thm9",        "Area Theorems",                "Analyse",   "R"),
  ]),

  _build("ch_g9_circles","circ9",[
    ("sc_circ9_terms",      "Circle Terms and Definitions", "Remember",  "V"),
    ("sc_chord_props9",     "Chord Properties",             "Understand","R"),
    ("sc_angle_circ9",      "Angle Subtended by Chord",     "Apply",     "R"),
    ("sc_cyclic_quad9",     "Cyclic Quadrilateral",         "Apply",     "R"),
    ("sc_circ9_thm",        "Circle Theorems",              "Analyse",   "R"),
  ]),

  _build("ch_g9_constructions","const9",[
    ("sc_basic_const9",     "Basic Constructions",          "Remember",  "K"),
    ("sc_angle_bisect9",    "Angle Bisector",               "Understand","K"),
    ("sc_perp_bisect9",     "Perpendicular Bisector",       "Apply",     "K"),
    ("sc_tri_const9",       "Constructing Triangles",       "Apply",     "K"),
  ]),

  _build("ch_g9_herons","herons9",[
    ("sc_tri_area9_intro",  "Area of Triangle Basics",      "Remember",  "K"),
    ("sc_herons9",          "Heron's Formula",              "Understand","K"),
    ("sc_herons9_apps",     "Applications of Heron's Formula","Apply",   "K"),
    ("sc_quad_area9",       "Area of Quadrilateral",        "Apply",     "K"),
  ]),

  _build("ch_g9_surface_volumes","surfvol9",[
    ("sc_cuboid_sa9",       "Cuboid Surface Area",          "Remember",  "K"),
    ("sc_cylinder_sa9",     "Cylinder Surface Area",        "Understand","K"),
    ("sc_cone_sa9",         "Cone Surface Area",            "Apply",     "K"),
    ("sc_sphere_sa9",       "Sphere Surface Area",          "Apply",     "K"),
    ("sc_volumes9",         "Volumes of 3D Shapes",         "Apply",     "K"),
    ("sc_combined9",        "Combined Shapes",              "Analyse",   "K"),
  ]),

  _build("ch_g9_statistics","stats9",[
    ("sc_stats9_collect",   "Data Collection",              "Remember",  "R"),
    ("sc_freq9",            "Frequency Distribution",       "Understand","R"),
    ("sc_graphical9",       "Graphical Representation",     "Understand","V"),
    ("sc_mmm9",             "Mean, Median and Mode",        "Apply",     "K"),
    ("sc_range9",           "Range and Measures",           "Analyse",   "K"),
  ]),

  _build("ch_g9_probability","prob9",[
    ("sc_prob9_intro",      "Introduction to Probability",  "Remember",  "R"),
    ("sc_expt_prob9",       "Experimental Probability",     "Understand","K"),
    ("sc_theor_prob9",      "Theoretical Probability",      "Apply",     "R"),
    ("sc_prob9_probs",      "Probability Problems",         "Apply",     "K"),
    ("sc_complementary9",   "Complementary Events",         "Analyse",   "R"),
  ]),
]

# ─────────────────────────────────────────────────────────────────────────────
# GRADE 10 — Science (14 chapters)
# ─────────────────────────────────────────────────────────────────────────────
G10_SCI = [

  _build("ch_g10_chem_reactions","chemrxn10",[
    ("sc_chem_eq10",        "Chemical Equations",           "Remember",  "R"),
    ("sc_balancing10",      "Balancing Equations",          "Understand","K"),
    ("sc_rxn_types10",      "Types of Chemical Reactions",  "Apply",     "K"),
    ("sc_ox_red10",         "Oxidation and Reduction",      "Apply",     "R"),
    ("sc_corr_rancid10",    "Corrosion and Rancidity",      "Analyse",   "K"),
  ]),

  _build("ch_g10_acids_bases","acidbase10",[
    ("sc_acids10",          "Properties of Acids",          "Remember",  "K"),
    ("sc_bases10",          "Properties of Bases",          "Understand","K"),
    ("sc_neutralisation10", "Neutralisation and Salts",     "Apply",     "K"),
    ("sc_ph10",             "pH Scale",                     "Apply",     "R"),
    ("sc_everyday_salts10", "Salts in Everyday Life",       "Analyse",   "K"),
  ]),

  _build("ch_g10_metals","metals10",[
    ("sc_metal_phys10",     "Physical Properties of Metals","Remember",  "V"),
    ("sc_reactivity10",     "Reactivity Series",            "Understand","R"),
    ("sc_metal_rxns10",     "Reactions of Metals",          "Apply",     "K"),
    ("sc_ionic_bond10",     "Ionic Bond Formation",         "Apply",     "R"),
    ("sc_metallurgy10",     "Extraction of Metals",         "Analyse",   "R"),
    ("sc_corr10",           "Corrosion Prevention",         "Analyse",   "K"),
  ]),

  _build("ch_g10_carbon","carbon10",[
    ("sc_covalent10",       "Covalent Bonding in Carbon",   "Remember",  "R"),
    ("sc_allotropes10",     "Allotropes of Carbon",         "Understand","V"),
    ("sc_hydrocarbons10",   "Hydrocarbons",                 "Understand","R"),
    ("sc_func_groups10",    "Functional Groups",            "Apply",     "R"),
    ("sc_carbon_rxns10",    "Chemical Reactions of Carbon", "Apply",     "K"),
    ("sc_ethanol10",        "Ethanol and Ethanoic Acid",    "Analyse",   "K"),
  ]),

  _build("ch_g10_life_processes","lifeproc10",[
    ("sc_lifeproc10_intro", "Introduction to Life Processes","Remember", "R"),
    ("sc_nutrition10",      "Autotrophic and Heterotrophic","Understand","R"),
    ("sc_photosyn10",       "Photosynthesis in Detail",     "Understand","V"),
    ("sc_respiration10",    "Respiration",                  "Apply",     "K"),
    ("sc_transport10",      "Transportation in Living Organisms","Apply","V"),
    ("sc_excretion10",      "Excretion",                    "Analyse",   "R"),
  ]),

  _build("ch_g10_control","control10",[
    ("sc_nervous10",        "Nervous System",               "Remember",  "R"),
    ("sc_reflex10",         "Reflex Action",                "Understand","K"),
    ("sc_brain10",          "Human Brain",                  "Understand","V"),
    ("sc_hormones10",       "Hormones and Endocrine System","Apply",     "R"),
    ("sc_plant_horm10",     "Plant Hormones",               "Apply",     "R"),
    ("sc_tropic10",         "Tropic Movements in Plants",   "Analyse",   "K"),
  ]),

  _build("ch_g10_reproduction","repro10",[
    ("sc_asexual10",        "Asexual Reproduction",         "Remember",  "K"),
    ("sc_sex_plants10",     "Sexual Reproduction in Plants","Understand","V"),
    ("sc_flower10",         "Flower Parts and Pollination", "Understand","V"),
    ("sc_human_repro10",    "Human Reproductive System",    "Apply",     "R"),
    ("sc_std10",            "STDs and Contraception",       "Apply",     "R"),
    ("sc_repro_health10",   "Reproductive Health",          "Analyse",   "R"),
  ]),

  _build("ch_g10_heredity","heredity10",[
    ("sc_heredity10_intro", "Heredity and Variation",       "Remember",  "R"),
    ("sc_mendel10",         "Mendel's Laws",                "Understand","R"),
    ("sc_sex_det10",        "Sex Determination",            "Understand","R"),
    ("sc_evolution10",      "Theory of Evolution",          "Apply",     "R"),
    ("sc_nat_sel10",        "Natural Selection",            "Apply",     "R"),
    ("sc_human_evol10",     "Human Evolution",              "Analyse",   "R"),
  ]),

  _build("ch_g10_light","light10",[
    ("sc_reflect10",        "Laws of Reflection",           "Remember",  "V"),
    ("sc_mirrors10",        "Mirrors and Image Formation",  "Understand","V"),
    ("sc_mirror_formula10", "Mirror Formula",               "Apply",     "K"),
    ("sc_refract10",        "Refraction and Snell's Law",   "Apply",     "K"),
    ("sc_lenses10",         "Lenses and Lens Formula",      "Apply",     "K"),
    ("sc_power_lens10",     "Power of a Lens",              "Analyse",   "K"),
  ]),

  _build("ch_g10_human_eye","humaneye10",[
    ("sc_eye_struct10",     "Structure of Human Eye",       "Remember",  "V"),
    ("sc_accommodation10",  "Accommodation of Eye",         "Understand","R"),
    ("sc_defects10",        "Defects of Vision",            "Understand","R"),
    ("sc_correction10",     "Correction of Defects",        "Apply",     "K"),
    ("sc_atm_refract10",    "Atmospheric Refraction",       "Apply",     "R"),
    ("sc_scattering10",     "Scattering of Light",          "Analyse",   "R"),
  ]),

  _build("ch_g10_electricity","elec10",[
    ("sc_current10",        "Electric Charge and Current",  "Remember",  "K"),
    ("sc_potential10",      "Potential Difference and EMF", "Understand","R"),
    ("sc_ohms10",           "Ohm's Law",                    "Apply",     "K"),
    ("sc_resistance10",     "Resistance and Factors",       "Apply",     "K"),
    ("sc_series_par10",     "Series and Parallel Circuits", "Apply",     "K"),
    ("sc_heating10",        "Heating Effect of Current",    "Analyse",   "K"),
  ]),

  _build("ch_g10_magnetism","magnet10",[
    ("sc_magfield10",       "Magnetic Field and Field Lines","Remember", "V"),
    ("sc_curr_magnet10",    "Magnetic Field due to Current","Understand","V"),
    ("sc_solenoid10",       "Solenoid and Electromagnet",   "Apply",     "K"),
    ("sc_motor10",          "Electric Motor",               "Apply",     "K"),
    ("sc_em_induct10",      "Electromagnetic Induction",    "Apply",     "R"),
    ("sc_generator10",      "Generator and Transformer",    "Analyse",   "K"),
  ]),

  _build("ch_g10_environment","env10",[
    ("sc_ecosystem10",      "Ecosystem Components",         "Remember",  "V"),
    ("sc_food_chains10",    "Food Chains and Webs",         "Understand","V"),
    ("sc_trophic10",        "Trophic Levels",               "Apply",     "R"),
    ("sc_biodeg10",         "Biodegradable vs Non-Biodeg",  "Apply",     "R"),
    ("sc_ozone10",          "Ozone Depletion",              "Analyse",   "R"),
  ]),

  _build("ch_g10_natural_mgmt","natmgmt10",[
    ("sc_natres10",         "Natural Resources Overview",   "Remember",  "R"),
    ("sc_water_mgmt10",     "Water Management",             "Understand","K"),
    ("sc_forest10",         "Forest and Wildlife Resources","Understand","R"),
    ("sc_fossil10",         "Fossil Fuels and Alternatives","Apply",     "R"),
    ("sc_5r10",             "Reduce, Reuse, Recycle",       "Apply",     "K"),
  ]),
]

# ─────────────────────────────────────────────────────────────────────────────
# GRADE 10 — Maths (14 chapters)
# ─────────────────────────────────────────────────────────────────────────────
G10_MATH = [

  _build("ch_g10_real_numbers","realnum10",[
    ("sc_euclid_div10",     "Euclid's Division Lemma",      "Remember",  "R"),
    ("sc_hcf_lcm10",        "HCF and LCM",                  "Understand","K"),
    ("sc_fund_thm10",       "Fundamental Theorem of Arith", "Apply",     "R"),
    ("sc_irrational10",     "Irrational Numbers Proof",     "Apply",     "R"),
    ("sc_decimal10",        "Decimal Expansions",           "Analyse",   "R"),
  ]),

  _build("ch_g10_polynomials","poly10",[
    ("sc_poly10_zeros",     "Zeros of Polynomials",         "Remember",  "R"),
    ("sc_poly10_relation",  "Zeros and Coefficients",       "Understand","R"),
    ("sc_div_algo10",       "Division Algorithm",           "Apply",     "K"),
    ("sc_quad_poly10",      "Quadratic Polynomial Zeros",   "Apply",     "K"),
    ("sc_cubic_poly10",     "Cubic Polynomial Zeros",       "Analyse",   "K"),
  ]),

  _build("ch_g10_linear_pair","linpair10",[
    ("sc_linpair10_intro",  "Pair of Linear Equations",     "Remember",  "R"),
    ("sc_graphical10",      "Graphical Method",             "Understand","V"),
    ("sc_substitution10",   "Substitution Method",          "Apply",     "K"),
    ("sc_elimination10",    "Elimination Method",           "Apply",     "K"),
    ("sc_cross_mult10",     "Cross Multiplication",         "Apply",     "K"),
    ("sc_word_linear10",    "Word Problems",                "Analyse",   "K"),
  ]),

  _build("ch_g10_quadratic","quadratic10",[
    ("sc_quad10_intro",     "Quadratic Equations",          "Remember",  "R"),
    ("sc_factor_meth10",    "Factoring Method",             "Understand","K"),
    ("sc_comp_sq10",        "Completing the Square",        "Apply",     "K"),
    ("sc_quad_formula10",   "Quadratic Formula",            "Apply",     "K"),
    ("sc_discriminant10",   "Nature of Roots",              "Analyse",   "R"),
  ]),

  _build("ch_g10_ap","ap10",[
    ("sc_ap10_intro",       "Introduction to AP",           "Remember",  "R"),
    ("sc_nth_term10",       "nth Term of AP",               "Understand","K"),
    ("sc_sum_ap10",         "Sum of n Terms",               "Apply",     "K"),
    ("sc_ap10_probs",       "AP Word Problems",             "Apply",     "K"),
    ("sc_special_sums10",   "Special Sums",                 "Analyse",   "K"),
  ]),

  _build("ch_g10_triangles","tri10",[
    ("sc_similar10",        "Similar Triangles",            "Remember",  "V"),
    ("sc_bpt10",            "Basic Proportionality Theorem","Understand","R"),
    ("sc_sim_criteria10",   "Criteria for Similarity",      "Apply",     "R"),
    ("sc_areas_sim10",      "Areas of Similar Triangles",   "Apply",     "K"),
    ("sc_pythagoras10",     "Pythagoras Theorem",           "Analyse",   "K"),
  ]),

  _build("ch_g10_coord_geom","coordgeo10",[
    ("sc_dist10",           "Distance Formula",             "Remember",  "K"),
    ("sc_section10",        "Section Formula",              "Understand","K"),
    ("sc_midpoint10",       "Midpoint Formula",             "Apply",     "K"),
    ("sc_area_tri_coord10", "Area of Triangle (Coordinates)","Apply",    "K"),
    ("sc_collinear10",      "Collinearity of Points",       "Analyse",   "K"),
  ]),

  _build("ch_g10_trig","trig10",[
    ("sc_trig_ratios10",    "Trigonometric Ratios",         "Remember",  "R"),
    ("sc_spec_angles10",    "Values at Specific Angles",    "Understand","K"),
    ("sc_comp_trig10",      "Complementary Angles",         "Apply",     "R"),
    ("sc_trig_id10",        "Trigonometric Identities",     "Apply",     "K"),
    ("sc_trig_proofs10",    "Proving Identities",           "Analyse",   "K"),
  ]),

  _build("ch_g10_trig_apps","trigapps10",[
    ("sc_height_dist10",    "Height and Distance",          "Remember",  "V"),
    ("sc_angle_elev10",     "Angle of Elevation",           "Understand","V"),
    ("sc_angle_dep10",      "Angle of Depression",          "Apply",     "K"),
    ("sc_trig_word10",      "Multi-step Problems",          "Apply",     "K"),
    ("sc_trig_adv10",       "Advanced Applications",        "Analyse",   "K"),
  ]),

  _build("ch_g10_circles","circ10",[
    ("sc_tangent10",        "Tangent to a Circle",          "Remember",  "V"),
    ("sc_tangent_props10",  "Properties of Tangents",       "Understand","R"),
    ("sc_num_tangents10",   "Number of Tangents",           "Apply",     "R"),
    ("sc_tangent_thm10",    "Tangent Theorems",             "Apply",     "R"),
    ("sc_angle_tang10",     "Angles with Tangents",         "Analyse",   "R"),
  ]),

  _build("ch_g10_circle_areas","circarea10",[
    ("sc_perim_circ10",     "Perimeter of Circle",          "Remember",  "K"),
    ("sc_sector10",         "Area of Sector",               "Understand","K"),
    ("sc_segment10",        "Area of Segment",              "Apply",     "K"),
    ("sc_combined_area10",  "Areas of Combinations",        "Apply",     "K"),
    ("sc_practical_area10", "Practical Applications",       "Analyse",   "K"),
  ]),

  _build("ch_g10_surface_vol","surfvol10",[
    ("sc_combo_solids10",   "Combinations of Solids",       "Remember",  "K"),
    ("sc_surface_combo10",  "Surface Area of Combined Solids","Understand","K"),
    ("sc_volume_combo10",   "Volume of Combined Solids",    "Apply",     "K"),
    ("sc_conversion10",     "Conversion of Solids",         "Apply",     "K"),
    ("sc_frustum10",        "Frustum of a Cone",            "Analyse",   "K"),
  ]),

  _build("ch_g10_statistics","stats10",[
    ("sc_mean_grouped10",   "Mean of Grouped Data",         "Remember",  "K"),
    ("sc_mode_grouped10",   "Mode of Grouped Data",         "Understand","K"),
    ("sc_median_grouped10", "Median of Grouped Data",       "Apply",     "K"),
    ("sc_ogive10",          "Cumulative Frequency and Ogive","Apply",    "V"),
    ("sc_empirical10",      "Empirical Relationship",       "Analyse",   "K"),
  ]),

  _build("ch_g10_probability","prob10",[
    ("sc_prob10_intro",     "Probability and Events",       "Remember",  "R"),
    ("sc_classical10",      "Classical Probability",        "Understand","K"),
    ("sc_comp10",           "Complementary Events",         "Apply",     "R"),
    ("sc_prob10_probs",     "Probability Problems",         "Apply",     "K"),
    ("sc_real_prob10",      "Real-life Applications",       "Analyse",   "K"),
  ]),
]

# ─────────────────────────────────────────────────────────────────────────────
# ALL CHAPTERS
# ─────────────────────────────────────────────────────────────────────────────
ALL_CHAPTERS = G8 + G9_SCI + G9_MATH + G10_SCI + G10_MATH


# ─────────────────────────────────────────────────────────────────────────────
# NEO4J SEED LOGIC
# ─────────────────────────────────────────────────────────────────────────────
async def seed_chapter(driver, chapter_id, concepts, subconcepts, prereqs):
    async with driver.session() as session:
        # Upsert concepts
        for con in concepts:
            await session.run(
                """
                MATCH (ch:Chapter {id: $ch_id})
                MERGE (c:Concept {id: $id})
                SET c.name=$name, c.weight=$weight
                MERGE (ch)-[:HAS_CONCEPT]->(c)
                """,
                ch_id=chapter_id, **con
            )
        # Upsert subconcepts
        for con_id, sc in subconcepts:
            await session.run(
                """
                MATCH (c:Concept {id: $con_id})
                MERGE (s:SubConcept {id: $id})
                SET s.name=$name, s.bloom_target=$bloom_target,
                    s.vark_hint=$vark_hint, s.map_x=$map_x, s.map_y=$map_y
                MERGE (c)-[:HAS_SUBCONCEPT]->(s)
                """,
                con_id=con_id, **sc
            )
        # Upsert prerequisites
        for from_id, to_id in prereqs:
            await session.run(
                """
                MATCH (a:SubConcept {id: $from_id}), (b:SubConcept {id: $to_id})
                MERGE (a)-[:PREREQUISITE]->(b)
                """,
                from_id=from_id, to_id=to_id
            )
    print(f"  ✓ {chapter_id} — {len(subconcepts)} subconcepts, {len(prereqs)} prereqs")


async def main():
    target = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--chapter" else None
    cfg    = get_settings()
    driver = AsyncGraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_username, cfg.neo4j_password))

    chapters = ALL_CHAPTERS
    if target:
        chapters = [c for c in chapters if c[0] == target]
        if not chapters:
            print(f"Chapter '{target}' not found."); return

    print(f"Seeding {len(chapters)} chapters…")
    async with driver:
        await create_constraints(driver)
        for ch_id, concepts, subconcepts, prereqs in chapters:
            await seed_chapter(driver, ch_id, concepts, subconcepts, prereqs)

    total_sc = sum(len(c[2]) for c in chapters)
    print(f"\n✅ Done — {len(chapters)} chapters, {total_sc} subconcepts seeded.")


if __name__ == "__main__":
    asyncio.run(main())
