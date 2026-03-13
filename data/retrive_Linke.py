import os
import sys
from PIL import Image

# Add src to path / 将 src 添加到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from bsrn.constants import BSRN_STATIONS

DATA_DIR = "/Volumes/Macintosh Research/Data/bsrn-qc/data/Linke_turbidity"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def get_linke_turbidity():
    results = {}
    
    width = 4320
    height = 2160
    res = 360.0 / width
    
    for month in MONTHS:
        file_path = os.path.join(DATA_DIR, f"TL2010_{month}_gf.tif")
        if not os.path.exists(file_path):
            print(f"Warning: File not found {file_path}")
            continue
            
        img = Image.open(file_path)
        pix = img.load()
        
        for stn_code, info in BSRN_STATIONS.items():
            if stn_code not in results:
                results[stn_code] = {}
            
            lat = info["lat"]
            lon = info["lon"]
            
            # Normalize lon to [-180, 180] / 将经度归一化到 [-180, 180]
            if lon > 180:
                lon -= 360
            elif lon < -180:
                lon += 360
                
            px = int((lon + 180.0) / res)
            py = int((90.0 - lat) / res)
            
            # Clip to image bounds / 裁剪到图像边界
            px = max(0, min(px, width - 1))
            py = max(0, min(py, height - 1))
            
            val = pix[px, py]
            # Scale is 20 for these Linke maps / 这些 Linke 地图的比例尺为 20
            results[stn_code][month] = round(val / 20.0, 2)
            
        img.close()
        
    return results

if __name__ == "__main__":
    lt_data = get_linke_turbidity()
    
    # Print as a python dictionary for constants.py / 打印为 constants.py 的 python 字典
    print("\nLINKE_TURBIDITY = {")
    for stn, values in sorted(lt_data.items()):
        vals_str = ", ".join([f'"{m}": {v}' for m, v in values.items()])
        print(f'    "{stn}": {{{vals_str}}},')
    print("}")
