"""Offline rows used when a network source is missing or refused.

These numbers are a built-in sample. Reports that use them say 离线回退.
"""

# Twelve Cu single-atom rows. Energies are a teaching sample, not a download.
CATALYSIS = [
    {"name": "Cu-Ni", "element": "Ni", "en": 1.91, "ea": 1.15, "period": 4, "group": 10, "E": -1.42},
    {"name": "Cu-Co", "element": "Co", "en": 1.88, "ea": 0.66, "period": 4, "group": 9, "E": -1.21},
    {"name": "Cu-Fe", "element": "Fe", "en": 1.83, "ea": 0.15, "period": 4, "group": 8, "E": -1.55},
    {"name": "Cu-Pt", "element": "Pt", "en": 2.28, "ea": 2.13, "period": 6, "group": 10, "E": -0.71},
    {"name": "Cu-Pd", "element": "Pd", "en": 2.20, "ea": 0.56, "period": 5, "group": 10, "E": -0.64},
    {"name": "Cu-Rh", "element": "Rh", "en": 2.28, "ea": 1.14, "period": 5, "group": 9, "E": -0.88},
    {"name": "Cu-Ru", "element": "Ru", "en": 2.20, "ea": 1.05, "period": 5, "group": 8, "E": -1.05},
    {"name": "Cu-Ag", "element": "Ag", "en": 1.93, "ea": 1.30, "period": 5, "group": 11, "E": -0.41},
    {"name": "Cu-Au", "element": "Au", "en": 2.54, "ea": 2.31, "period": 6, "group": 11, "E": -0.22},
    {"name": "Cu-Zn", "element": "Zn", "en": 1.65, "ea": 0.00, "period": 4, "group": 12, "E": -0.35},
    {"name": "Cu-Mo", "element": "Mo", "en": 2.16, "ea": 0.75, "period": 5, "group": 6, "E": -1.33},
    {"name": "Cu-W", "element": "W", "en": 2.36, "ea": 0.82, "period": 6, "group": 6, "E": -1.18},
]

FEATURES = ("en", "ea", "period", "group")


def generic_rows(seed):
    """Deterministic stand-in table for a field that has no downloaded file."""
    rows = []
    for index in range(12):
        value = ((seed + 1) * (index + 3)) % 17
        rows.append({
            "name": "样本-{:02d}".format(index + 1),
            "f1": round(0.2 * index + (value % 5) * 0.1, 3),
            "f2": round(1.5 - 0.08 * index, 3),
            "f3": round((value % 7) / 3, 3),
            "E": round(-1.4 + 0.11 * index + (value % 3) * 0.05, 3),
        })
    return rows
