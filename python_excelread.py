import pandas as pd
import os
import json

EXCEL_FILE_PATH = os.path.join("backend", "DATASET1.xlsx")
OUTPUT_DIR = "output_data"  # Folder to save JSON & CSV files

def ensure_output_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def process_excel_sheets(excel_path, output_dir):
    if not os.path.exists(excel_path):
        print(f"ERROR: Excel file not found at: {os.path.abspath(excel_path)}")
        return

    ensure_output_dir(output_dir)

    xls = pd.ExcelFile(excel_path)
    print(f"Excel file found at: {os.path.abspath(excel_path)}\n")

    for sheet_name in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            print(f"Sheet '{sheet_name}':")
            print(f" Columns ({len(df.columns)}): {df.columns.tolist()}")
            print(f" Number of rows: {len(df)}")
            print(f" Sample data (first 3 rows):")
            print(df.head(3))
            print("-" * 40)

            # Save full sheet data as JSON
            json_path = os.path.join(output_dir, f"{sheet_name}.json")
            df.to_json(json_path, orient="records", indent=2, force_ascii=False)

            # Save full sheet data as CSV
            csv_path = os.path.join(output_dir, f"{sheet_name}.csv")
            df.to_csv(csv_path, index=False)

        except Exception as e:
            print(f"Error processing sheet '{sheet_name}': {e}")

if __name__ == "__main__":
    process_excel_sheets(EXCEL_FILE_PATH, OUTPUT_DIR)
