# bsrn: Quality Control for BSRN Files

`bsrn` is a Python package designed for automated quality control (QC) on Baseline Surface Radiation Network (BSRN) station-to-archive files (e.g., .001, .002, etc.).

## 📂 File Structure

```text
/Volumes/Macintosh Research/Data/bsrn-qc/
├── .gitignore
├── README.md
├── pyproject.toml
├── src/
│   └── bsrn/
│       ├── __init__.py
│       ├── constants.py         # BSRN station database & physical constants
│       ├── io/
│       │   ├── __init__.py
│       │   ├── readers.py       # Functions to read .001, .002 datasets
│       │   ├── retrieval.py     # FTP automated downloads & inventory
│       │   └── writers.py       # Exporting results
│       ├── physics/
│       │   ├── __init__.py
│       │   ├── geometry.py      # Solar position (Zenith, Azimuth via pvlib)
│       │   └── clearsky.py      # Theoretical reference models
│       ├── qc/
│       │   ├── __init__.py
│       │   ├── physical.py      # Physically possible limits (Level 1)
│       │   ├── rare.py          # Extremely rare limits (Level 2)
│       │   └── consistency.py   # Internal consistency checks (Level 3)
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
│   └── sample_bsrn_file.001     # Example file for testing/demo
└── notebooks/                   # Example usage notebooks
```

## 🛠 Features (Planned)

Based on the [BSRN Operations Manual (2018)](https://bsrn.awi.de/):

- **Level 1 (Physically Possible):** Checks if values stay within absolute physical bounds.
- **Level 2 (Extremely Rare):** Checks if values fall within very infrequent ranges, typical for specific climatic conditions.
- **Level 3 (Internal Consistency):** Cross-comparison between complementary radiation components (GHI vs. DHI + DNI).
- **Automation:** Easy ingestion of station-to-archive files from multiple sites.

## 🚀 Getting Started

1.  **Installation:** (Planned)
    ```bash
    pip install .
    ```

2.  **Usage Example:** (Placeholder)
    ```python
    import bsrn
    
    # Load BSRN data
    data = bsrn.io.read_station_file("data/sample_bsrn_file.001")
    
    # Perform QC
    results = bsrn.qc.run_standard_checks(data)
    ```

## 📜 License

MIT License (Planned)
