import shutil
import os
from pathlib import Path

# Paths to the generated images in the brain directory
brain_dir = r"C:\Users\Lenovo\.gemini\antigravity\brain\6c5b2afa-ed6f-49de-a43b-30174ecaab5f"
# Path to the project's assets folder
target_dir = os.path.join(os.getcwd(), "assets")

# Ensure the assets directory exists
os.makedirs(target_dir, exist_ok=True)

# Mapping of generated filenames to the names expected by the dashboard
files = {
    "badge_gold_png_1777471541216.png": "badge_gold.png",
    "badge_silver_png_1777471556468.png": "badge_silver.png",
    "badge_bronze_png_1777471571033.png": "badge_bronze.png",
    "badge_progress_png_1777471600149.png": "badge_progress.png",
    "badge_support_png_1777471614419.png": "badge_support.png",
    "certificate_gold_png_1777471634639.png": "certificate_gold.png",
    "certificate_silver_png_1777471656415.png": "certificate_silver.png",
    "certificate_bronze_png_1777471671330.png": "certificate_bronze.png",
    "certificate_progress_png_1777471689878.png": "certificate_progress.png",
    "certificate_support_png_1777471708845.png": "certificate_support.png",
    "fairness_high_png_1777472037888.png": "fairness_high.png",
    "fairness_consistent_png_1777472052849.png": "fairness_consistent.png",
    "fairness_growth_png_1777472070126.png": "fairness_growth.png",
}

print(f"Initializing assets in: {target_dir}")

count = 0
for src, dst in files.items():
    src_path = os.path.join(brain_dir, src)
    dst_path = os.path.join(target_dir, dst)
    
    if os.path.exists(src_path):
        try:
            shutil.copy(src_path, dst_path)
            print(f"  [OK] Created {dst}")
            count += 1
        except Exception as e:
            print(f"  [ERROR] Could not copy {dst}: {e}")
    else:
        print(f"  [SKIP] Source asset not found: {src}")

if count > 0:
    print(f"\nSuccess! {count} assets ready. Please refresh your Streamlit dashboard.")
else:
    print("\nNo assets were moved. Please ensure you are running this from the project root.")
