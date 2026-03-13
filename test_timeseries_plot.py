import sys
import os
import pandas as pd
sys.path.append(os.path.join(os.getcwd(), 'src'))

from bsrn.io.readers import read_bsrn_station_to_archive
from bsrn.visualization.timeseries import plot_bsrn_timeseries_booklet

def main():
    # Test for station QIQ, July 2024
    file_path = "data/QIQ/qiq0724.dat.gz"
    if not os.path.exists(file_path):
        print(f"Skipping test: {file_path} not found.")
        return

    print(f"Generating booklet with QC for {file_path}...")
    plot_bsrn_timeseries_booklet(file_path, "test_qiq_booklet_qc.pdf", station_code="QIQ", apply_qc=True)
    print("Saved: test_qiq_booklet_qc.pdf")

    print(f"Generating booklet without QC for {file_path}...")
    plot_bsrn_timeseries_booklet(file_path, "test_qiq_booklet_noqc.pdf", station_code="QIQ", apply_qc=False)
    print("Saved: test_qiq_booklet_noqc.pdf")

if __name__ == "__main__":
    main()
