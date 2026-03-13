import os
import sys

# Add src to python path to ensure bsrn is importable
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from bsrn.visualization import plot_bsrn_availability
    from bsrn.visualization.timeseries import plot_bsrn_timeseries_booklet
except ImportError:
    print("Error: Could not import bsrn. Make sure you are running from the project root.")
    sys.exit(1)

def test_availability():
    # --- CONFIGURATION ---
    # Put your BSRN FTP credentials here
    BSRN_USER = "bsrnftp" 
    BSRN_PASSWORD = "bsrn1"
    
    # List of stations you want to check
    STATIONS_TO_CHECK = ['PAY', 'NYA', 'GVN', 'ILO', 'TAT', 'QIQ'] 
    
    # Year range
    START_YEAR = 1992
    
    print(f"\n--- Testing Availability Heatmap ---")
    print(f"Initiating BSRN FTP search for: {STATIONS_TO_CHECK}")
    
    try:
        output_file = "bsrn_availability_heatmap.pdf"
        plot_bsrn_availability(
            stations=STATIONS_TO_CHECK,
            username=BSRN_USER,
            password=BSRN_PASSWORD,
            start_year=START_YEAR,
            output_file=output_file
        )
        print(f"Successfully generated heatmap: {output_file}")
    except Exception as e:
        print(f"Availability heatmap failed: {e}")

def test_timeseries():
    # Test for station QIQ, November 2024
    file_path = "data/QIQ/qiq1124.dat.gz"
    print(f"\n--- Testing Timeseries Booklet ---")
    
    if not os.path.exists(file_path):
        print(f"Skipping timeseries test: {file_path} not found.")
        return

    try:
        output_file = "test_qiq_booklet.pdf"
        print(f"Generating booklet for {file_path}...")
        plot_bsrn_timeseries_booklet(
            file_path, 
            output_file, 
            station_code="QIQ", 
            apply_qc=False
        )
        print(f"Successfully generated booklet: {output_file}")
    except Exception as e:
        print(f"Timeseries booklet failed: {e}")

def main():
    test_availability()
    test_timeseries()

if __name__ == "__main__":
    main()
