"""
Universal Google Maps Scraper
CLI & Interactive Tool to extract business leads (Name, Address, Phone, Website, Email, etc.)
for ANY business type (gyms, cafes, petrol pumps, parking, cinemas, etc.) across any city or area.
"""

import sys
import os
import argparse
import re
from typing import List, Dict, Any

from core.gmaps_scraper import scrape_google_maps
from core.email_extractor import batch_extract_emails
from core.excel_exporter import export_to_excel

BANNER = r"""
========================================================================
   ____                   _        __  __                  ____                                
  / ___| ___   ___   __ _| | ___  |  \/  | __ _ _ __  ___ / ___|  ___ _ __ __ _ _ __   ___ _ __ 
 | |  _ / _ \ / _ \ / _` | |/ _ \ | |\/| |/ _` | '_ \/ __| |     / __| '__/ _` | '_ \ / _ \ '__|
 | |_| | (_) | (_) | (_| | |  __/ | |  | | (_| | |_) \__ \ |___ | (__| | | (_| | |_) |  __/ |   
  \____|\___/ \___/ \__, |_|\___| |_|  |_|\__,_| .__/|___/\____|  \___|_|  \__,_| .__/ \___|_|   
                    |___/                      |_|                              |_|              
========================================================================
   Universal Business Extractor: Gyms, Cafes, Petrol Pumps, Parking, etc.
========================================================================
"""

def sanitize_filename(name: str) -> str:
    """Sanitize query string into a safe file name."""
    s = re.sub(r"[^\w\s-]", "", name).strip().lower()
    return re.sub(r"[-\s]+", "_", s)

def run_scraper(
    query: str,
    max_results: int = 50,
    extract_emails: bool = True,
    headless: bool = True,
    output_path: str = None,
    workers: int = 8
) -> str:
    """Run the complete scrape, enrich, and export workflow."""
    print(BANNER)
    print(f"[*] Query:          {query}")
    print(f"[*] Max Results:    {max_results}")
    print(f"[*] Email Mining:   {'Enabled' if extract_emails else 'Disabled'}")
    print(f"[*] Browser Mode:   {'Headless (Background)' if headless else 'Visible (Headed)'}")
    print("-" * 72)

    # Step 1: Scrape Google Maps
    print("\n>>> STEP 1: Scraping Google Maps...")
    places = scrape_google_maps(
        query=query,
        max_results=max_results,
        headless=headless,
        status_callback=lambda msg: print(f"  [G-Maps] {msg}")
    )

    if not places:
        print("\n[!] No listings found or scraping returned 0 results.")
        return ""

    print(f"\n[+] Successfully extracted {len(places)} business listings.")

    # Step 2: Website Email Extraction
    if extract_emails:
        websites = [p.get("website") for p in places if p.get("website")]
        print(f"\n>>> STEP 2: Mining emails from {len(websites)} business websites (parallel workers={workers})...")
        if websites:
            email_map = batch_extract_emails(websites, max_workers=workers)
            found_count = 0
            for p in places:
                site = p.get("website")
                if site and site in email_map:
                    p["emails"] = email_map[site]
                    if p["emails"]:
                        found_count += 1
            print(f"[+] Found contact emails for {found_count} businesses.")
        else:
            print("  No websites available in scraped listings to extract emails from.")

    # Step 3: Determine output path & Export to Excel
    print("\n>>> STEP 3: Generating styled Excel spreadsheet...")
    if not output_path:
        os.makedirs("output", exist_ok=True)
        safe_name = sanitize_filename(query)
        output_path = os.path.join("output", f"{safe_name}.xlsx")

    final_excel_path = export_to_excel(places, output_path)
    final_csv_path = os.path.splitext(final_excel_path)[0] + ".csv"

    print("\n" + "=" * 72)
    print("EXTRACTION COMPLETED SUCCESSFULLY!")
    print(f"Total Records: {len(places)}")
    print(f"Excel Sheet:   {final_excel_path}")
    print(f"CSV File:      {final_csv_path}")
    print("=" * 72 + "\n")

    # Display preview sample of top results
    print("Quick Preview (Top 3 Results):")
    for i, p in enumerate(places[:3], 1):
        print(f" {i}. {p.get('name')} | Cat: {p.get('category')} | Phone: {p.get('phone')} | Rating: {p.get('rating')} ({p.get('reviews_count')})")
        if p.get('website'):
            print(f"    Website: {p.get('website')}")
        if p.get('emails'):
            print(f"    Emails:  {p.get('emails')}")
        print(f"    Address: {p.get('address')[:70]}...")
    print("-" * 72)

    return final_excel_path

def interactive_mode():
    """Interactive wizard if user runs script without CLI flags."""
    print(BANNER)
    print("Welcome to Google Maps Lead Scraper!")
    print("You can extract data for ANY business domain or location:")
    print("  - Gyms in Chandigarh")
    print("  - Cafes in Bangalore")
    print("  - Petrol pumps near Jaipur")
    print("  - Parking spots in Connaught Place, Delhi")
    print("  - Cinemas in Mumbai")
    print("-" * 72)

    try:
        query = input("\nEnter search query (e.g. 'gyms in chandigarh'): ").strip()
        while not query:
            query = input("Please enter a valid search query: ").strip()

        limit_input = input("Max results to fetch [default: 20]: ").strip()
        max_results = int(limit_input) if limit_input.isdigit() else 20

        email_choice = input("Extract emails from business websites? (y/n) [default: y]: ").strip().lower()
        extract_emails = (email_choice != "n")

        headless_choice = input("Run browser in background? (y/n) [default: y]: ").strip().lower()
        headless = (headless_choice != "n")

        run_scraper(
            query=query,
            max_results=max_results,
            extract_emails=extract_emails,
            headless=headless
        )
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(
        description="Universal Google Maps Scraper for any business type (gyms, cafes, petrol pumps, parking, etc.)"
    )
    parser.add_argument("-q", "--query", type=str, help="Search query (e.g. 'gyms in chandigarh', 'cafes in bandra')")
    parser.add_argument("-m", "--max-results", type=int, default=50, help="Max listings to extract (default: 50)")
    parser.add_argument("-o", "--output", type=str, default=None, help="Output .xlsx file path")
    parser.add_argument("--no-emails", action="store_true", help="Skip crawling websites for emails")
    parser.add_argument("--headed", action="store_true", help="Display the browser UI while scraping")
    parser.add_argument("--workers", type=int, default=8, help="Parallel worker threads for email extraction")

    args = parser.parse_args()

    # If no search query provided via CLI, launch interactive mode
    if not args.query:
        interactive_mode()
    else:
        run_scraper(
            query=args.query,
            max_results=args.max_results,
            extract_emails=not args.no_emails,
            headless=not args.headed,
            output_path=args.output,
            workers=args.workers
        )

if __name__ == "__main__":
    main()
