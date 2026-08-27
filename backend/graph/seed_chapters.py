"""
Seed Data — 10 Pilot Chapters (Grade 8 Science + Maths)
========================================================
Adds SubConcept knowledge graphs for:
  Science : Friction, Sound, Light, Combustion & Flame,
            Chemical Effects of Electric Current
  Maths   : Linear Equations, Factorisation, Cubes & Cube Roots,
            Understanding Quadrilaterals, Squares & Square Roots

Run all chapters:
    python -m backend.graph.seed_chapters

Run one chapter:
    python -m backend.graph.seed_chapters --chapter ch_friction

Each SubConcept carries:
  - map_x / map_y  : position on SVG canvas (viewBox "0 0 340 510")
  - bloom_target   : ceiling Bloom level for GPS done-state
  - vark_hint      : dominant learning style (V/A/R/K)

PREREQUISITE edges form a DAG — master the "from" node to unlock "to" node.
"""

import asyncio
import sys
from neo4j import AsyncGraphDatabase
from backend.config.settings import get_settings
from backend.graph.schema import create_constraints


# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER DATA
# Each entry: (chapter_id, [concepts], [subconcepts], [prerequisites])
#
# subconcept format:  (concept_id, {id, name, bloom_target, vark_hint, map_x, map_y})
# prerequisite format: (from_sc_id, to_sc_id)
# ─────────────────────────────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════════════════
# SCIENCE 1 — FRICTION  (ch_friction)
# ══════════════════════════════════════════════════════════════════════════════

FRICTION_CONCEPTS = [
    {"id": "con_fric_types",   "name": "Types of Friction",        "weight": 0.55},
    {"id": "con_fric_effects", "name": "Effects and Applications", "weight": 0.45},
]

FRICTION_SUBCONCEPTS = [
    ("con_fric_types", {
        "id": "sc_fric_what",
        "name": "What is Friction",
        "bloom_target": "Remember",
        "vark_hint": "K",
        "map_x": 170.0, "map_y": 52.0,
    }),
    ("con_fric_types", {
        "id": "sc_fric_types",
        "name": "Types of Friction",
        "bloom_target": "Understand",
        "vark_hint": "V",
        "map_x": 170.0, "map_y": 130.0,
    }),
    ("con_fric_types", {
        "id": "sc_fric_static",
        "name": "Static Friction",
        "bloom_target": "Understand",
        "vark_hint": "R",
        "map_x": 75.0, "map_y": 210.0,
    }),
    ("con_fric_types", {
        "id": "sc_fric_kinetic",
        "name": "Kinetic Friction",
        "bloom_target": "Understand",
        "vark_hint": "K",
        "map_x": 170.0, "map_y": 210.0,
    }),
    ("con_fric_types", {
        "id": "sc_fric_rolling",
        "name": "Rolling Friction",
        "bloom_target": "Understand",
        "vark_hint": "K",
        "map_x": 265.0, "map_y": 210.0,
    }),
    ("con_fric_effects", {
        "id": "sc_fric_factors",
        "name": "Factors Affecting Friction",
        "bloom_target": "Apply",
        "vark_hint": "K",
        "map_x": 170.0, "map_y": 300.0,
    }),
    ("con_fric_effects", {
        "id": "sc_fric_advantages",
        "name": "Advantages of Friction",
        "bloom_target": "Apply",
        "vark_hint": "R",
        "map_x": 95.0, "map_y": 390.0,
    }),
    ("con_fric_effects", {
        "id": "sc_fric_reducing",
        "name": "Increasing and Reducing Friction",
        "bloom_target": "Analyse",
        "vark_hint": "K",
        "map_x": 245.0, "map_y": 390.0,
    }),
]

FRICTION_PREREQS = [
    ("sc_fric_what",     "sc_fric_types"),
    ("sc_fric_types",    "sc_fric_static"),
    ("sc_fric_types",    "sc_fric_kinetic"),
    ("sc_fric_types",    "sc_fric_rolling"),
    ("sc_fric_static",   "sc_fric_factors"),
    ("sc_fric_kinetic",  "sc_fric_factors"),
    ("sc_fric_rolling",  "sc_fric_factors"),
    ("sc_fric_factors",  "sc_fric_advantages"),
    ("sc_fric_factors",  "sc_fric_reducing"),
]


# ══════════════════════════════════════════════════════════════════════════════
# SCIENCE 2 — SOUND  (ch_sound)
# ══════════════════════════════════════════════════════════════════════════════

SOUND_CONCEPTS = [
    {"id": "con_sound_nature",  "name": "Nature of Sound",      "weight": 0.55},
    {"id": "con_sound_props",   "name": "Sound Properties",     "weight": 0.45},
]

SOUND_SUBCONCEPTS = [
    ("con_sound_nature", {
        "id": "sc_sound_prod",
        "name": "Sound Production",
        "bloom_target": "Remember",
        "vark_hint": "A",
        "map_x": 170.0, "map_y": 45.0,
    }),
    ("con_sound_nature", {
        "id": "sc_sound_prop",
        "name": "Sound Propagation",
        "bloom_target": "Understand",
        "vark_hint": "A",
        "map_x": 170.0, "map_y": 120.0,
    }),
    ("con_sound_nature", {
        "id": "sc_sound_waves",
        "name": "Sound Waves",
        "bloom_target": "Understand",
        "vark_hint": "V",
        "map_x": 170.0, "map_y": 195.0,
    }),
    ("con_sound_props", {
        "id": "sc_sound_ampl",
        "name": "Amplitude and Loudness",
        "bloom_target": "Understand",
        "vark_hint": "A",
        "map_x": 90.0, "map_y": 275.0,
    }),
    ("con_sound_props", {
        "id": "sc_sound_freq",
        "name": "Frequency and Pitch",
        "bloom_target": "Understand",
        "vark_hint": "A",
        "map_x": 250.0, "map_y": 275.0,
    }),
    ("con_sound_props", {
        "id": "sc_sound_speed",
        "name": "Speed of Sound",
        "bloom_target": "Apply",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 350.0,
    }),
    ("con_sound_props", {
        "id": "sc_sound_echo",
        "name": "Echo and Reflection",
        "bloom_target": "Apply",
        "vark_hint": "K",
        "map_x": 90.0, "map_y": 425.0,
    }),
    ("con_sound_props", {
        "id": "sc_sound_range",
        "name": "Audible Range and Ultrasound",
        "bloom_target": "Understand",
        "vark_hint": "R",
        "map_x": 250.0, "map_y": 425.0,
    }),
    ("con_sound_props", {
        "id": "sc_sound_noise",
        "name": "Noise Pollution",
        "bloom_target": "Analyse",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 480.0,
    }),
]

SOUND_PREREQS = [
    ("sc_sound_prod",  "sc_sound_prop"),
    ("sc_sound_prop",  "sc_sound_waves"),
    ("sc_sound_waves", "sc_sound_ampl"),
    ("sc_sound_waves", "sc_sound_freq"),
    ("sc_sound_freq",  "sc_sound_speed"),
    ("sc_sound_speed", "sc_sound_echo"),
    ("sc_sound_speed", "sc_sound_range"),
    ("sc_sound_echo",  "sc_sound_noise"),
    ("sc_sound_range", "sc_sound_noise"),
]


# ══════════════════════════════════════════════════════════════════════════════
# SCIENCE 3 — LIGHT  (ch_light)
# ══════════════════════════════════════════════════════════════════════════════

LIGHT_CONCEPTS = [
    {"id": "con_light_reflection", "name": "Reflection of Light", "weight": 0.40},
    {"id": "con_light_refraction", "name": "Refraction of Light", "weight": 0.35},
    {"id": "con_light_vision",     "name": "Human Vision",        "weight": 0.25},
]

LIGHT_SUBCONCEPTS = [
    ("con_light_reflection", {
        "id": "sc_light_straight",
        "name": "Light Travels in Straight Lines",
        "bloom_target": "Remember",
        "vark_hint": "V",
        "map_x": 170.0, "map_y": 45.0,
    }),
    ("con_light_reflection", {
        "id": "sc_light_reflect",
        "name": "Laws of Reflection",
        "bloom_target": "Understand",
        "vark_hint": "V",
        "map_x": 170.0, "map_y": 118.0,
    }),
    ("con_light_reflection", {
        "id": "sc_light_plane",
        "name": "Plane Mirror and Image",
        "bloom_target": "Understand",
        "vark_hint": "V",
        "map_x": 90.0, "map_y": 195.0,
    }),
    ("con_light_reflection", {
        "id": "sc_light_curved",
        "name": "Curved Mirrors",
        "bloom_target": "Apply",
        "vark_hint": "V",
        "map_x": 250.0, "map_y": 195.0,
    }),
    ("con_light_refraction", {
        "id": "sc_light_refract",
        "name": "Refraction of Light",
        "bloom_target": "Understand",
        "vark_hint": "V",
        "map_x": 170.0, "map_y": 270.0,
    }),
    ("con_light_refraction", {
        "id": "sc_light_lens",
        "name": "Lenses",
        "bloom_target": "Apply",
        "vark_hint": "V",
        "map_x": 90.0, "map_y": 345.0,
    }),
    ("con_light_refraction", {
        "id": "sc_light_dispers",
        "name": "Dispersion of Light",
        "bloom_target": "Understand",
        "vark_hint": "V",
        "map_x": 250.0, "map_y": 345.0,
    }),
    ("con_light_vision", {
        "id": "sc_light_eye",
        "name": "Human Eye",
        "bloom_target": "Apply",
        "vark_hint": "K",
        "map_x": 170.0, "map_y": 415.0,
    }),
    ("con_light_vision", {
        "id": "sc_light_defects",
        "name": "Defects of Vision",
        "bloom_target": "Analyse",
        "vark_hint": "R",
        "map_x": 90.0, "map_y": 478.0,
    }),
    ("con_light_vision", {
        "id": "sc_light_care",
        "name": "Care of Eyes and Braille",
        "bloom_target": "Apply",
        "vark_hint": "R",
        "map_x": 250.0, "map_y": 478.0,
    }),
]

LIGHT_PREREQS = [
    ("sc_light_straight", "sc_light_reflect"),
    ("sc_light_reflect",  "sc_light_plane"),
    ("sc_light_reflect",  "sc_light_curved"),
    ("sc_light_straight", "sc_light_refract"),
    ("sc_light_refract",  "sc_light_lens"),
    ("sc_light_refract",  "sc_light_dispers"),
    ("sc_light_lens",     "sc_light_eye"),
    ("sc_light_curved",   "sc_light_eye"),
    ("sc_light_eye",      "sc_light_defects"),
    ("sc_light_eye",      "sc_light_care"),
]


# ══════════════════════════════════════════════════════════════════════════════
# SCIENCE 4 — COMBUSTION AND FLAME  (ch_combustion)
# ══════════════════════════════════════════════════════════════════════════════

COMBUSTION_CONCEPTS = [
    {"id": "con_comb_process", "name": "Combustion Process", "weight": 0.55},
    {"id": "con_comb_control", "name": "Fire Control",       "weight": 0.45},
]

COMBUSTION_SUBCONCEPTS = [
    ("con_comb_process", {
        "id": "sc_comb_what",
        "name": "What is Combustion",
        "bloom_target": "Remember",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 52.0,
    }),
    ("con_comb_process", {
        "id": "sc_comb_conditions",
        "name": "Conditions for Combustion",
        "bloom_target": "Understand",
        "vark_hint": "K",
        "map_x": 170.0, "map_y": 130.0,
    }),
    ("con_comb_process", {
        "id": "sc_comb_types",
        "name": "Types of Combustion",
        "bloom_target": "Understand",
        "vark_hint": "R",
        "map_x": 90.0, "map_y": 210.0,
    }),
    ("con_comb_control", {
        "id": "sc_comb_triangle",
        "name": "Fire Triangle",
        "bloom_target": "Understand",
        "vark_hint": "V",
        "map_x": 250.0, "map_y": 210.0,
    }),
    ("con_comb_process", {
        "id": "sc_comb_flame",
        "name": "Structure of a Flame",
        "bloom_target": "Understand",
        "vark_hint": "V",
        "map_x": 90.0, "map_y": 300.0,
    }),
    ("con_comb_control", {
        "id": "sc_comb_fuel",
        "name": "Fuels and Calorific Value",
        "bloom_target": "Apply",
        "vark_hint": "R",
        "map_x": 250.0, "map_y": 300.0,
    }),
    ("con_comb_control", {
        "id": "sc_comb_extinguish",
        "name": "Fire Extinguishers",
        "bloom_target": "Apply",
        "vark_hint": "K",
        "map_x": 170.0, "map_y": 385.0,
    }),
    ("con_comb_control", {
        "id": "sc_comb_pollution",
        "name": "Combustion and Air Pollution",
        "bloom_target": "Analyse",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 462.0,
    }),
]

COMBUSTION_PREREQS = [
    ("sc_comb_what",       "sc_comb_conditions"),
    ("sc_comb_conditions", "sc_comb_types"),
    ("sc_comb_conditions", "sc_comb_triangle"),
    ("sc_comb_conditions", "sc_comb_flame"),
    ("sc_comb_conditions", "sc_comb_fuel"),
    ("sc_comb_triangle",   "sc_comb_extinguish"),
    ("sc_comb_fuel",       "sc_comb_extinguish"),
    ("sc_comb_extinguish", "sc_comb_pollution"),
    ("sc_comb_flame",      "sc_comb_pollution"),
]


# ══════════════════════════════════════════════════════════════════════════════
# SCIENCE 5 — CHEMICAL EFFECTS OF ELECTRIC CURRENT  (ch_chemical_effects)
# ══════════════════════════════════════════════════════════════════════════════

CHEM_EFFECTS_CONCEPTS = [
    {"id": "con_cec_conductivity", "name": "Electrical Conductivity", "weight": 0.45},
    {"id": "con_cec_electrolysis", "name": "Electrolysis",            "weight": 0.55},
]

CHEM_EFFECTS_SUBCONCEPTS = [
    ("con_cec_conductivity", {
        "id": "sc_cec_conductors",
        "name": "Conductors and Insulators",
        "bloom_target": "Remember",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 52.0,
    }),
    ("con_cec_conductivity", {
        "id": "sc_cec_liquids",
        "name": "Liquids as Conductors",
        "bloom_target": "Understand",
        "vark_hint": "K",
        "map_x": 170.0, "map_y": 130.0,
    }),
    ("con_cec_conductivity", {
        "id": "sc_cec_effects",
        "name": "Chemical Effects of Current",
        "bloom_target": "Understand",
        "vark_hint": "V",
        "map_x": 170.0, "map_y": 210.0,
    }),
    ("con_cec_electrolysis", {
        "id": "sc_cec_electrolysis",
        "name": "Electrolysis Process",
        "bloom_target": "Understand",
        "vark_hint": "R",
        "map_x": 90.0, "map_y": 295.0,
    }),
    ("con_cec_electrolysis", {
        "id": "sc_cec_electrodes",
        "name": "Electrodes and Electrolyte",
        "bloom_target": "Understand",
        "vark_hint": "V",
        "map_x": 250.0, "map_y": 295.0,
    }),
    ("con_cec_electrolysis", {
        "id": "sc_cec_deposition",
        "name": "Metal Deposition",
        "bloom_target": "Apply",
        "vark_hint": "K",
        "map_x": 90.0, "map_y": 378.0,
    }),
    ("con_cec_electrolysis", {
        "id": "sc_cec_plating",
        "name": "Electroplating",
        "bloom_target": "Apply",
        "vark_hint": "K",
        "map_x": 250.0, "map_y": 378.0,
    }),
    ("con_cec_electrolysis", {
        "id": "sc_cec_uses",
        "name": "Uses of Electroplating",
        "bloom_target": "Analyse",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 460.0,
    }),
]

CHEM_EFFECTS_PREREQS = [
    ("sc_cec_conductors",   "sc_cec_liquids"),
    ("sc_cec_liquids",      "sc_cec_effects"),
    ("sc_cec_effects",      "sc_cec_electrolysis"),
    ("sc_cec_effects",      "sc_cec_electrodes"),
    ("sc_cec_electrolysis", "sc_cec_deposition"),
    ("sc_cec_electrodes",   "sc_cec_plating"),
    ("sc_cec_deposition",   "sc_cec_plating"),
    ("sc_cec_plating",      "sc_cec_uses"),
]


# ══════════════════════════════════════════════════════════════════════════════
# MATHS 1 — LINEAR EQUATIONS IN ONE VARIABLE  (ch_linear_equations)
# ══════════════════════════════════════════════════════════════════════════════

LINEAR_EQ_CONCEPTS = [
    {"id": "con_le_concept",  "name": "Linear Equations",   "weight": 0.50},
    {"id": "con_le_solving",  "name": "Solving Techniques", "weight": 0.50},
]

LINEAR_EQ_SUBCONCEPTS = [
    ("con_le_concept", {
        "id": "sc_le_variables",
        "name": "Variables and Constants",
        "bloom_target": "Remember",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 52.0,
    }),
    ("con_le_concept", {
        "id": "sc_le_expressions",
        "name": "Algebraic Expressions",
        "bloom_target": "Remember",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 130.0,
    }),
    ("con_le_concept", {
        "id": "sc_le_equations",
        "name": "Equations vs Expressions",
        "bloom_target": "Understand",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 205.0,
    }),
    ("con_le_concept", {
        "id": "sc_le_linear",
        "name": "Linear Equations",
        "bloom_target": "Understand",
        "vark_hint": "V",
        "map_x": 90.0, "map_y": 280.0,
    }),
    ("con_le_solving", {
        "id": "sc_le_balance",
        "name": "Solving by Balancing",
        "bloom_target": "Apply",
        "vark_hint": "K",
        "map_x": 250.0, "map_y": 280.0,
    }),
    ("con_le_solving", {
        "id": "sc_le_transpose",
        "name": "Transposition Method",
        "bloom_target": "Apply",
        "vark_hint": "R",
        "map_x": 90.0, "map_y": 365.0,
    }),
    ("con_le_solving", {
        "id": "sc_le_word",
        "name": "Word Problems",
        "bloom_target": "Apply",
        "vark_hint": "R",
        "map_x": 250.0, "map_y": 365.0,
    }),
    ("con_le_solving", {
        "id": "sc_le_fractions",
        "name": "Equations with Fractions",
        "bloom_target": "Analyse",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 452.0,
    }),
]

LINEAR_EQ_PREREQS = [
    ("sc_le_variables",   "sc_le_expressions"),
    ("sc_le_expressions", "sc_le_equations"),
    ("sc_le_equations",   "sc_le_linear"),
    ("sc_le_equations",   "sc_le_balance"),
    ("sc_le_linear",      "sc_le_transpose"),
    ("sc_le_balance",     "sc_le_word"),
    ("sc_le_transpose",   "sc_le_word"),
    ("sc_le_transpose",   "sc_le_fractions"),
    ("sc_le_word",        "sc_le_fractions"),
]


# ══════════════════════════════════════════════════════════════════════════════
# MATHS 2 — FACTORISATION  (ch_factorisation)
# ══════════════════════════════════════════════════════════════════════════════

FACT_CONCEPTS = [
    {"id": "con_fact_basic",    "name": "Basic Factorisation",    "weight": 0.50},
    {"id": "con_fact_advanced", "name": "Advanced Factorisation", "weight": 0.50},
]

FACT_SUBCONCEPTS = [
    ("con_fact_basic", {
        "id": "sc_fact_intro",
        "name": "What is Factorisation",
        "bloom_target": "Remember",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 52.0,
    }),
    ("con_fact_basic", {
        "id": "sc_fact_common",
        "name": "Common Factor Method",
        "bloom_target": "Apply",
        "vark_hint": "K",
        "map_x": 90.0, "map_y": 135.0,
    }),
    ("con_fact_basic", {
        "id": "sc_fact_grouping",
        "name": "Factorisation by Grouping",
        "bloom_target": "Apply",
        "vark_hint": "R",
        "map_x": 250.0, "map_y": 135.0,
    }),
    ("con_fact_advanced", {
        "id": "sc_fact_id1",
        "name": "Identity: (a+b)² and (a−b)²",
        "bloom_target": "Apply",
        "vark_hint": "R",
        "map_x": 90.0, "map_y": 220.0,
    }),
    ("con_fact_advanced", {
        "id": "sc_fact_id2",
        "name": "Identity: a² − b²",
        "bloom_target": "Apply",
        "vark_hint": "R",
        "map_x": 250.0, "map_y": 220.0,
    }),
    ("con_fact_advanced", {
        "id": "sc_fact_id3",
        "name": "Identity: (x+a)(x+b)",
        "bloom_target": "Apply",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 305.0,
    }),
    ("con_fact_advanced", {
        "id": "sc_fact_division",
        "name": "Division of Polynomials",
        "bloom_target": "Analyse",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 385.0,
    }),
    ("con_fact_advanced", {
        "id": "sc_fact_errors",
        "name": "Common Errors in Factorisation",
        "bloom_target": "Analyse",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 462.0,
    }),
]

FACT_PREREQS = [
    ("sc_fact_intro",    "sc_fact_common"),
    ("sc_fact_intro",    "sc_fact_grouping"),
    ("sc_fact_common",   "sc_fact_id1"),
    ("sc_fact_common",   "sc_fact_id2"),
    ("sc_fact_grouping", "sc_fact_id1"),
    ("sc_fact_grouping", "sc_fact_id2"),
    ("sc_fact_id1",      "sc_fact_id3"),
    ("sc_fact_id2",      "sc_fact_id3"),
    ("sc_fact_id3",      "sc_fact_division"),
    ("sc_fact_division", "sc_fact_errors"),
]


# ══════════════════════════════════════════════════════════════════════════════
# MATHS 3 — CUBES AND CUBE ROOTS  (ch_cubes_roots)
# ══════════════════════════════════════════════════════════════════════════════

CUBES_CONCEPTS = [
    {"id": "con_cube_cubes", "name": "Cubes",       "weight": 0.55},
    {"id": "con_cube_roots", "name": "Cube Roots",  "weight": 0.45},
]

CUBES_SUBCONCEPTS = [
    ("con_cube_cubes", {
        "id": "sc_cube_perfect",
        "name": "Perfect Cubes",
        "bloom_target": "Remember",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 60.0,
    }),
    ("con_cube_cubes", {
        "id": "sc_cube_patterns",
        "name": "Patterns in Cubes",
        "bloom_target": "Understand",
        "vark_hint": "V",
        "map_x": 90.0, "map_y": 150.0,
    }),
    ("con_cube_cubes", {
        "id": "sc_cube_properties",
        "name": "Properties of Cubes",
        "bloom_target": "Understand",
        "vark_hint": "R",
        "map_x": 250.0, "map_y": 150.0,
    }),
    ("con_cube_roots", {
        "id": "sc_cube_root_concept",
        "name": "Cube Root Concept",
        "bloom_target": "Understand",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 245.0,
    }),
    ("con_cube_roots", {
        "id": "sc_cube_prime",
        "name": "Cube Root by Prime Factorisation",
        "bloom_target": "Apply",
        "vark_hint": "K",
        "map_x": 90.0, "map_y": 340.0,
    }),
    ("con_cube_roots", {
        "id": "sc_cube_estimate",
        "name": "Estimating Cube Roots",
        "bloom_target": "Apply",
        "vark_hint": "R",
        "map_x": 250.0, "map_y": 340.0,
    }),
    ("con_cube_roots", {
        "id": "sc_cube_applications",
        "name": "Applications of Cubes",
        "bloom_target": "Analyse",
        "vark_hint": "K",
        "map_x": 170.0, "map_y": 430.0,
    }),
]

CUBES_PREREQS = [
    ("sc_cube_perfect",      "sc_cube_patterns"),
    ("sc_cube_perfect",      "sc_cube_properties"),
    ("sc_cube_properties",   "sc_cube_root_concept"),
    ("sc_cube_root_concept", "sc_cube_prime"),
    ("sc_cube_root_concept", "sc_cube_estimate"),
    ("sc_cube_prime",        "sc_cube_applications"),
    ("sc_cube_estimate",     "sc_cube_applications"),
]


# ══════════════════════════════════════════════════════════════════════════════
# MATHS 4 — UNDERSTANDING QUADRILATERALS  (ch_quadrilaterals)
# ══════════════════════════════════════════════════════════════════════════════

QUAD_CONCEPTS = [
    {"id": "con_quad_polygon", "name": "Polygons",              "weight": 0.35},
    {"id": "con_quad_types",   "name": "Quadrilateral Types",   "weight": 0.65},
]

QUAD_SUBCONCEPTS = [
    ("con_quad_polygon", {
        "id": "sc_quad_polygons",
        "name": "Polygons and Classification",
        "bloom_target": "Remember",
        "vark_hint": "V",
        "map_x": 170.0, "map_y": 45.0,
    }),
    ("con_quad_polygon", {
        "id": "sc_quad_angle_sum",
        "name": "Angle Sum Property",
        "bloom_target": "Understand",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 118.0,
    }),
    ("con_quad_types", {
        "id": "sc_quad_types",
        "name": "Types of Quadrilaterals",
        "bloom_target": "Remember",
        "vark_hint": "V",
        "map_x": 170.0, "map_y": 195.0,
    }),
    ("con_quad_types", {
        "id": "sc_quad_parallelogram",
        "name": "Parallelogram Properties",
        "bloom_target": "Understand",
        "vark_hint": "V",
        "map_x": 90.0, "map_y": 272.0,
    }),
    ("con_quad_types", {
        "id": "sc_quad_trapezium",
        "name": "Trapezium and Kite",
        "bloom_target": "Understand",
        "vark_hint": "V",
        "map_x": 250.0, "map_y": 272.0,
    }),
    ("con_quad_types", {
        "id": "sc_quad_rectangle",
        "name": "Rectangle",
        "bloom_target": "Apply",
        "vark_hint": "K",
        "map_x": 55.0, "map_y": 355.0,
    }),
    ("con_quad_types", {
        "id": "sc_quad_rhombus",
        "name": "Rhombus",
        "bloom_target": "Apply",
        "vark_hint": "K",
        "map_x": 170.0, "map_y": 355.0,
    }),
    ("con_quad_types", {
        "id": "sc_quad_square",
        "name": "Square",
        "bloom_target": "Apply",
        "vark_hint": "K",
        "map_x": 285.0, "map_y": 355.0,
    }),
    ("con_quad_types", {
        "id": "sc_quad_special",
        "name": "Special Quadrilaterals Summary",
        "bloom_target": "Analyse",
        "vark_hint": "V",
        "map_x": 170.0, "map_y": 450.0,
    }),
]

QUAD_PREREQS = [
    ("sc_quad_polygons",     "sc_quad_angle_sum"),
    ("sc_quad_angle_sum",    "sc_quad_types"),
    ("sc_quad_types",        "sc_quad_parallelogram"),
    ("sc_quad_types",        "sc_quad_trapezium"),
    ("sc_quad_parallelogram","sc_quad_rectangle"),
    ("sc_quad_parallelogram","sc_quad_rhombus"),
    ("sc_quad_rectangle",    "sc_quad_square"),
    ("sc_quad_rhombus",      "sc_quad_square"),
    ("sc_quad_square",       "sc_quad_special"),
    ("sc_quad_trapezium",    "sc_quad_special"),
]


# ══════════════════════════════════════════════════════════════════════════════
# MATHS 5 — SQUARES AND SQUARE ROOTS  (ch_squares_roots)
# ══════════════════════════════════════════════════════════════════════════════

SQUARES_CONCEPTS = [
    {"id": "con_sq_squares", "name": "Squares",       "weight": 0.50},
    {"id": "con_sq_roots",   "name": "Square Roots",  "weight": 0.50},
]

SQUARES_SUBCONCEPTS = [
    ("con_sq_squares", {
        "id": "sc_sq_perfect",
        "name": "Perfect Squares",
        "bloom_target": "Remember",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 52.0,
    }),
    ("con_sq_squares", {
        "id": "sc_sq_properties",
        "name": "Properties of Perfect Squares",
        "bloom_target": "Understand",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 130.0,
    }),
    ("con_sq_squares", {
        "id": "sc_sq_patterns",
        "name": "Interesting Patterns in Squares",
        "bloom_target": "Understand",
        "vark_hint": "V",
        "map_x": 90.0, "map_y": 210.0,
    }),
    ("con_sq_squares", {
        "id": "sc_sq_pythagorean",
        "name": "Pythagorean Triplets",
        "bloom_target": "Apply",
        "vark_hint": "R",
        "map_x": 250.0, "map_y": 210.0,
    }),
    ("con_sq_roots", {
        "id": "sc_sq_root_concept",
        "name": "Square Root Concept",
        "bloom_target": "Understand",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 295.0,
    }),
    ("con_sq_roots", {
        "id": "sc_sq_prime",
        "name": "Square Root by Prime Factorisation",
        "bloom_target": "Apply",
        "vark_hint": "K",
        "map_x": 90.0, "map_y": 380.0,
    }),
    ("con_sq_roots", {
        "id": "sc_sq_long_div",
        "name": "Square Root by Long Division",
        "bloom_target": "Apply",
        "vark_hint": "K",
        "map_x": 250.0, "map_y": 380.0,
    }),
    ("con_sq_roots", {
        "id": "sc_sq_estimation",
        "name": "Estimating Square Roots",
        "bloom_target": "Apply",
        "vark_hint": "R",
        "map_x": 170.0, "map_y": 460.0,
    }),
]

SQUARES_PREREQS = [
    ("sc_sq_perfect",     "sc_sq_properties"),
    ("sc_sq_properties",  "sc_sq_patterns"),
    ("sc_sq_properties",  "sc_sq_pythagorean"),
    ("sc_sq_properties",  "sc_sq_root_concept"),
    ("sc_sq_root_concept","sc_sq_prime"),
    ("sc_sq_root_concept","sc_sq_long_div"),
    ("sc_sq_prime",       "sc_sq_estimation"),
    ("sc_sq_long_div",    "sc_sq_estimation"),
]


# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER REGISTRY  (id → chapter data + sub-data)
# ─────────────────────────────────────────────────────────────────────────────

PILOT_CHAPTERS = {
    "ch_friction": {
        "concepts":      FRICTION_CONCEPTS,
        "subconcepts":   FRICTION_SUBCONCEPTS,
        "prerequisites": FRICTION_PREREQS,
    },
    "ch_sound": {
        "concepts":      SOUND_CONCEPTS,
        "subconcepts":   SOUND_SUBCONCEPTS,
        "prerequisites": SOUND_PREREQS,
    },
    "ch_light": {
        "concepts":      LIGHT_CONCEPTS,
        "subconcepts":   LIGHT_SUBCONCEPTS,
        "prerequisites": LIGHT_PREREQS,
    },
    "ch_combustion": {
        "concepts":      COMBUSTION_CONCEPTS,
        "subconcepts":   COMBUSTION_SUBCONCEPTS,
        "prerequisites": COMBUSTION_PREREQS,
    },
    "ch_chemical_effects": {
        "concepts":      CHEM_EFFECTS_CONCEPTS,
        "subconcepts":   CHEM_EFFECTS_SUBCONCEPTS,
        "prerequisites": CHEM_EFFECTS_PREREQS,
    },
    "ch_linear_equations": {
        "concepts":      LINEAR_EQ_CONCEPTS,
        "subconcepts":   LINEAR_EQ_SUBCONCEPTS,
        "prerequisites": LINEAR_EQ_PREREQS,
    },
    "ch_factorisation": {
        "concepts":      FACT_CONCEPTS,
        "subconcepts":   FACT_SUBCONCEPTS,
        "prerequisites": FACT_PREREQS,
    },
    "ch_cubes_roots": {
        "concepts":      CUBES_CONCEPTS,
        "subconcepts":   CUBES_SUBCONCEPTS,
        "prerequisites": CUBES_PREREQS,
    },
    "ch_quadrilaterals": {
        "concepts":      QUAD_CONCEPTS,
        "subconcepts":   QUAD_SUBCONCEPTS,
        "prerequisites": QUAD_PREREQS,
    },
    "ch_squares_roots": {
        "concepts":      SQUARES_CONCEPTS,
        "subconcepts":   SQUARES_SUBCONCEPTS,
        "prerequisites": SQUARES_PREREQS,
    },
}

# Cross-chapter links (shown in overview map)
CHAPTER_LINKS = [
    ("ch_force_pressure",   "ch_friction",         "Friction is a contact force"),
    ("ch_squares_roots",    "ch_cubes_roots",       "Squares extend to cubes"),
    ("ch_linear_equations", "ch_factorisation",     "Algebraic foundations"),
]


# ─────────────────────────────────────────────────────────────────────────────
# SEEDER
# ─────────────────────────────────────────────────────────────────────────────

async def seed_chapter(session, chapter_id: str):
    data = PILOT_CHAPTERS[chapter_id]
    concepts      = data["concepts"]
    subconcepts   = data["subconcepts"]
    prerequisites = data["prerequisites"]

    # 1. Seed Concepts + PART_OF Chapter
    for c in concepts:
        await session.run(
            "MERGE (n:Concept {id:$id}) SET n += $props",
            id=c["id"], props=c,
        )
        await session.run(
            """
            MATCH (c:Concept {id:$c_id}), (ch:Chapter {id:$ch_id})
            MERGE (c)-[:PART_OF]->(ch)
            """,
            c_id=c["id"], ch_id=chapter_id,
        )

    # 2. Seed SubConcepts + PART_OF Concept
    for concept_id, sc in subconcepts:
        await session.run(
            "MERGE (n:SubConcept {id:$id}) SET n += $props",
            id=sc["id"], props=sc,
        )
        await session.run(
            """
            MATCH (sc:SubConcept {id:$sc_id}), (c:Concept {id:$c_id})
            MERGE (sc)-[:PART_OF]->(c)
            """,
            sc_id=sc["id"], c_id=concept_id,
        )

    # 3. Delete stale PREREQUISITE edges for this chapter then recreate
    await session.run(
        """
        MATCH (a:SubConcept)-[r:PREREQUISITE]->(b:SubConcept)
        WHERE (a)-[:PART_OF]->(:Concept)-[:PART_OF]->(:Chapter {id:$ch_id})
        DELETE r
        """,
        ch_id=chapter_id,
    )
    for from_id, to_id in prerequisites:
        await session.run(
            """
            MATCH (a:SubConcept {id:$from_id}), (b:SubConcept {id:$to_id})
            MERGE (a)-[:PREREQUISITE]->(b)
            """,
            from_id=from_id, to_id=to_id,
        )

    sc_count = len(subconcepts)
    pr_count = len(prerequisites)
    print(f"  ✅ {chapter_id:<25} → {sc_count} subconcepts, {pr_count} prerequisite edges")


async def seed_chapter_links(session):
    """Upsert cross-chapter CHAPTER_LINK edges."""
    for from_id, to_id, label in CHAPTER_LINKS:
        await session.run(
            """
            MATCH (a:Chapter {id:$from_id}), (b:Chapter {id:$to_id})
            MERGE (a)-[:CHAPTER_LINK {label:$label}]->(b)
            """,
            from_id=from_id, to_id=to_id, label=label,
        )
    print(f"  ✅ {len(CHAPTER_LINKS)} cross-chapter links seeded")


async def seed(driver, chapter_filter: str | None = None):
    async with driver.session() as session:
        chapters_to_seed = (
            [chapter_filter] if chapter_filter else list(PILOT_CHAPTERS.keys())
        )

        print(f"\n🌱 Seeding {len(chapters_to_seed)} chapter(s)...\n")
        for ch_id in chapters_to_seed:
            if ch_id not in PILOT_CHAPTERS:
                print(f"  ⚠️  Unknown chapter: {ch_id}")
                continue
            await seed_chapter(session, ch_id)

        print("\n🔗 Seeding cross-chapter links...")
        await seed_chapter_links(session)

    total_sc = sum(len(v["subconcepts"]) for k, v in PILOT_CHAPTERS.items()
                   if not chapter_filter or k == chapter_filter)
    print(f"\n🎉 Done! {total_sc} subconcepts seeded across {len(chapters_to_seed)} chapter(s).\n")


async def main():
    # Optional: --chapter ch_friction
    chapter_filter = None
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--chapter" and i + 1 < len(sys.argv) - 1:
            chapter_filter = sys.argv[i + 2]

    settings = get_settings()
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password),
    )
    await seed(driver, chapter_filter)
    await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
