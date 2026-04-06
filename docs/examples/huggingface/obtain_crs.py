"""
Example: Compare Ground Measurements with CAMS CRS Satellite Data
示例：比较地面测量与 CAMS CRS 卫星数据

This script loads one BSRN station-month via :class:`~bsrn.dataset.BSRNDataset`,
runs the recommended pipeline (``solpos`` → ``clear_sky`` REST2 / MERRA-2 HF →
``qc_test`` → ``qc_mask``), adds CAMS CRS all-sky columns from Hugging Face,
time-averages with :meth:`~bsrn.dataset.BSRNDataset.average`, and plots a
calendar comparison.
本脚本通过 :class:`~bsrn.dataset.BSRNDataset` 加载单月台站数据，执行推荐管线
（``solpos`` → REST2 晴空（MERRA-2 HF）→ ``qc_test`` → ``qc_mask``），从
Hugging Face 加入 CRS 全天空列，再用 :meth:`~bsrn.dataset.BSRNDataset.average`
时间平均并绘制日历对比图。
"""

import os

import bsrn
from bsrn.io.crs import add_crs_columns
from bsrn.visualization import plot_calendar

# 1. Input path (change to your local archive)
# 输入路径（请改为本地存档路径）
INPUT_FILE = "/Volumes/Macintosh Research/Data/bsrn-qc/data/QIQ/qiq0824.dat.gz"

print(f"--- Processing {INPUT_FILE} ---")

if not os.path.exists(INPUT_FILE):
    raise FileNotFoundError(f"File not found: {INPUT_FILE}")

# 2. Load validated station-month (LR0100 + metadata)
# 加载已校验的单月站点（LR0100 + 元数据）
ds = bsrn.BSRNDataset.from_file(INPUT_FILE)
print(f"Station {ds.station_code}: loaded {len(ds.data())} rows.")

# 3. Pipeline: geometry, REST2 clear-sky, QC flags, then mask failures
# 管线：几何、REST2 晴空、QC 标记、再掩膜未通过点
print("solpos() …")
ds.solpos()
print("clear_sky(model='rest2') …")
ds.clear_sky(model="rest2")
print("qc_test() …")
ds.qc_test()
print("qc_mask() …")
ds.qc_mask()

# 4. CRS all-sky columns (1-min; add before averaging)
# CRS 全天空列（1 分钟；在平均前加入）
print("add_crs_columns (Hugging Face) …")
add_crs_columns(ds.data(), station_code=ds.station_code)

# 5. Time averaging (30-min centered windows)
# 时间平均（30 分钟居中窗）
print("average(freq='30min', alignment='center') …")
df_avg = ds.average(
    "30min",
    alignment="center",
    match_ceiling_labels=True,
)

print("\nProcessing complete. Sample averaged data:")
print(df_avg[["ghi", "ghi_clear", "ghi_crs"]].head())

# 6. Calendar plot (expects floor-aligned labels for this helper)
# 日历图（该辅助函数期望 start-of-interval 对齐标签）
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
