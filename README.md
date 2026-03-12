# bsrn: Quality Control for BSRN Files

`bsrn` is a Python package designed for automated quality control (QC) on Baseline Surface Radiation Network (BSRN) station-to-archive files (e.g., .001, .002, etc.).

## 📂 File Structure

```text
/Volumes/Macintosh Research/Data/bsrn/
├── .gitignore
├── README.md
├── .agents/
│   └── skills/
│       └── project-rules/
│           └── SKILL.md         # Project standards & naming conventions
├── pyproject.toml
├── src/
│   └── bsrn/
│       ├── __init__.py
│       ├── constants.py         # BSRN station database & physical constants
│       ├── io/
│       │   ├── __init__.py
│       │   ├── readers.py       # Functions to read .001, .002 datasets
│       │   ├── retrieval.py     # FTP automated downloads with robust retries
│       │   └── writers.py       # Exporting results
│       ├── physics/
│       │   ├── __init__.py
│       │   ├── geometry.py      # Solar position (Zenith, Azimuth via pvlib)
│       │   └── clearsky.py      # Theoretical reference models
│       ├── qc/
│       │   ├── __init__.py
│       │   ├── ppl.py           # Physically possible limits (Level 1)
│       │   ├── erl.py           # Extremely rare limits (Level 2)
│       │   ├── closure.py       # Internal consistency checks (Level 3)
│       │   ├── k_index.py       # Radiometric index tests (kb, kt, k)
│       │   └── tracker.py       # Solar tracker status detection
│       ├── visualization/
│       │   ├── __init__.py
│       │   └── availability.py  # File coverage heatmaps
│       └── utils/
│           ├── __init__.py
│           └── calculations.py  # Supporting math
├── tests/
│   ├── __init__.py
│   ├── test_io.py
│   └── test_qc.py
├── data/
│   ├── QIQ/                     # Sample 2024 data for station QIQ
│   └── download_qiq.py          # Script to fetch QIQ 2024 data
└── notebooks/                   # Example usage notebooks
```

## 🛠 Features

Based on the [BSRN Operations Manual (2018)](https://bsrn.awi.de/) and [Forstinger et al. (2021)](https://doi.org/10.18086/swc.2021.36):

- **Level 1 (Physically Possible):** Absolute physical bounds for $G_h, B_n, D_h$, and $L_d$.
- **Level 2 (Extremely Rare):** Climatological limits for specific regimes.
- **Level 3 (Comparison):** Consistency checks ($G_h$ vs $B_n \cos Z + D_h$) with zenith-dependent thresholds.
- **Radiometric Indices:** Advanced checks using clearness index ($k_t$), beam transmittance ($k_b$), and diffuse fraction ($k$).
- **Tracker Detection:** Identify tracking errors by comparing measured values with clear-sky benchmarks.
- **Robust Retrieval:** High-level API for batch FTP downloads from BSRN-AWI with exponential backoff retries.

## 🚀 Getting Started

1.  **Installation:**
    ```bash
    pip install .
    ```

2.  **Data Retrieval:**
    To download all 2024 data for a station (e.g., QIQ):
    ```python
    from bsrn.io.retrieval import download_bsrn_stn
    
    # Downloads all available files for a station
    download_bsrn_stn("QIQ", "data/QIQ", username="your_user", password="your_password")
    ```

3.  **QC Example:**
    ```python
    import bsrn
    
    # Load BSRN data (placeholder for the full runner)
    # data = bsrn.io.read_station_file("data/QIQ/qiq0124.dat.gz")
    ```

## 📜 License

MIT License
