"""
Example: Compare Ground Measurements with CAMS CRS Satellite Data

This script loads one BSRN station-month via :class:`~bsrn.dataset.BSRNDataset`,
runs the recommended pipeline (``solpos`` → ``clear_sky`` REST2 / MERRA-2 HF →
``qc_test`` → ``qc_mask``), adds CAMS CRS all-sky columns from Hugging Face,
time-averages with :meth:`~bsrn.dataset.BSRNDataset.average`, and plots a
calendar comparison.
"""

import os

import bsrn
from bsrn.io.crs import add_crs_columns
from bsrn.visualization import plot_calendar

# 1. Input path (change to your local archive)
INPUT_FILE = "/Volumes/Macintosh Research/Data/bsrn-qc/data/QIQ/qiq0824.dat.gz"

print(f"--- Processing {INPUT_FILE} ---")

if not os.path.exists(INPUT_FILE):
    raise FileNotFoundError(f"File not found: {INPUT_FILE}")

# 2. Load validated station-month (LR0100 + metadata)
ds = bsrn.BSRNDataset.from_file(INPUT_FILE)
print(f"Station {ds.station_code}: loaded {len(ds.data())} rows.")

# 3. Pipeline: geometry, REST2 clear-sky, QC flags, then mask failures
print("solpos() …")
ds.solpos()
print("clear_sky(model='rest2') …")
ds.clear_sky(model="rest2")
print("qc_test() …")
ds.qc_test()
print("qc_mask() …")
ds.qc_mask()

# 4. CRS all-sky columns (1-min; add before averaging)
print("add_crs_columns (Hugging Face) …")
add_crs_columns(ds.data(), station_code=ds.station_code)

# 5. Time averaging (30-min centered windows)
print("average(freq='30min', alignment='center') …")
df_avg = ds.average(
    "30min",
    alignment="center",
    match_ceiling_labels=True,
)

print("\nProcessing complete. Sample averaged data:")
print(df_avg[["ghi", "ghi_clear", "ghi_crs"]].head())

# 6. Calendar plot (expects floor-aligned labels for this helper)
output_plot = "qiq_hf_comparison.pdf"
print(f"\nGenerating calendar plot: {output_plot} …")

plot_calendar(
    df=df_avg,
    output_file=output_plot,
    station_code=ds.station_code,
    meas_col="ghi",
    clear_col="ghi_clear",
    other_cols=["ghi_crs"],
    labels=[
        "Measured GHI",
        "REST2 Clear-sky GHI",
        "CAMS CRS Satellite GHI",
    ],
)

print(f"Plot saved to {output_plot}")
