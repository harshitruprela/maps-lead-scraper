"""
Excel and CSV Exporter Module
Exports scraped Google Maps places and contact info into beautifully formatted
Excel (.xlsx) and CSV files using openpyxl.
"""

import os
import csv
from typing import List, Dict, Any
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

COLUMNS = [
    ("Name", "name", 30),
    ("Category", "category", 20),
    ("Rating", "rating", 10),
    ("Reviews", "reviews_count", 12),
    ("Phone", "phone", 18),
    ("Emails", "emails", 32),
    ("Address", "address", 45),
    ("Website", "website", 30),
    ("Google Maps Link", "google_maps_url", 35),
    ("Latitude", "latitude", 14),
    ("Longitude", "longitude", 14),
    ("Hours / Status", "hours", 25),
]

def export_to_excel(places: List[Dict[str, Any]], output_filepath: str) -> str:
    """
    Exports a list of place dictionaries to an Excel file with styling.
    Returns the absolute path of the generated Excel file.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Google Maps Data"

    # Styling definitions
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    data_font = Font(name="Calibri", size=10)
    link_font = Font(name="Calibri", size=10, color="0563C1", underline="single")
    center_alignment = Alignment(horizontal="center", vertical="center")
    left_alignment = Alignment(horizontal="left", vertical="center")
    wrap_left_alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    even_row_fill = PatternFill(start_color="F2F5F9", end_color="F2F5F9", fill_type="solid")
    odd_row_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    thin_border_side = Side(border_style="thin", color="D9D9D9")
    cell_border = Border(
        left=thin_border_side,
        right=thin_border_side,
        top=thin_border_side,
        bottom=thin_border_side,
    )

    # 1. Write Header Row
    ws.row_dimensions[1].height = 28
    for col_idx, (col_name, _, _) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = cell_border

    # 2. Write Data Rows
    for row_idx, place in enumerate(places, start=2):
        ws.row_dimensions[row_idx].height = 22
        current_fill = even_row_fill if row_idx % 2 == 0 else odd_row_fill

        for col_idx, (_, field_key, _) in enumerate(COLUMNS, start=1):
            val = place.get(field_key, "")
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.fill = current_fill
            cell.border = cell_border
            cell.font = data_font

            # Hyperlinks formatting for URLs
            if field_key in ("website", "google_maps_url") and val and str(val).startswith("http"):
                cell.value = str(val)
                cell.hyperlink = str(val)
                cell.font = link_font
                cell.alignment = left_alignment
            elif field_key in ("rating", "reviews_count", "latitude", "longitude"):
                cell.value = val
                cell.alignment = center_alignment
            elif field_key in ("address", "hours"):
                cell.value = str(val) if val is not None else ""
                cell.alignment = wrap_left_alignment
            else:
                cell.value = str(val) if val is not None else ""
                cell.alignment = left_alignment

    # 3. Freeze Header Row
    ws.freeze_panes = "A2"

    # 4. Set Column Widths based on configuration or contents
    for col_idx, (_, _, default_width) in enumerate(COLUMNS, start=1):
        col_letter = get_column_letter(col_idx)
        max_len = default_width
        ws.column_dimensions[col_letter].width = max_len

    # Save Excel workbook
    wb.save(output_filepath)

    # Also save companion CSV file
    csv_filepath = os.path.splitext(output_filepath)[0] + ".csv"
    export_to_csv(places, csv_filepath)

    return os.path.abspath(output_filepath)

def export_to_csv(places: List[Dict[str, Any]], csv_filepath: str) -> str:
    """Exports places to a clean CSV file."""
    os.makedirs(os.path.dirname(os.path.abspath(csv_filepath)), exist_ok=True)
    fieldnames = [col_name for col_name, _, _ in COLUMNS]
    keys = [field_key for _, field_key, _ in COLUMNS]

    with open(csv_filepath, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in places:
            row_dict = {
                col_name: p.get(field_key, "")
                for col_name, field_key, _ in COLUMNS
            }
            writer.writerow(row_dict)

    return os.path.abspath(csv_filepath)
