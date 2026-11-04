# Universal Google Maps Scraper & Lead Extractor

A robust, domain-agnostic tool to extract business details from **Google Maps** for **any domain or location** (e.g., *gyms in Chandigarh, cafes in Mumbai, petrol pumps in Delhi, parking in Bangalore, cinemas, hospitals, etc.*), discover business emails from their official websites, and replicate all data into a professionally formatted **Excel sheet (.xlsx)** and **CSV file**.

---

## Features

- **Domain-Agnostic**: Works with any search query (gyms, cafes, restaurants, gas stations, parking, cinemas, clinics, real estate, etc.).
- **Comprehensive Data Fields**:
  - Business Name
  - Category / Industry
  - Rating & Review Count
  - Phone Number
  - Official Website URL
  - **Emails** (extracted from official website homepage & `/contact` subpages)
  - Full Postal Address
  - Operating Hours / Open Status
  - Google Maps Direct Link
  - Latitude & Longitude Coordinates
- **Automated Email Extraction**: Because Google Maps listings do not provide emails directly, this scraper crawls each business's official website concurrently to extract contact and `mailto:` email addresses.
- **Styled Excel (.xlsx) Output**:
  - Color-coded headers with freeze-panes.
  - Auto-fitted column widths.
  - Clickable hyperlinks for Websites and Google Maps pins.
  - Companion `.csv` automatically generated for spreadsheet tools.
- **Dual Mode**:
  - **Interactive Wizard**: Simply run `python main.py` or double-click `run.bat`.
  - **CLI Automation**: Pass command-line arguments for scripts and automation.

---

## Quick Start

### 1. Requirements & Setup
Dependencies are already installed. If running in a fresh environment:
```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Run Interactive Mode
Double click `run.bat` or run:
```bash
python main.py
```
You will be prompted to enter:
1. Search query (e.g., `gyms in chandigarh`, `cafes in baner pune`, `cinemas in south delhi`)
2. Max results (e.g., `50`)
3. Whether to extract emails from websites (`y/n`)
4. Whether to run in background headless mode (`y/n`)

### 3. Run Command-Line Mode
```bash
# Example 1: Gyms in Chandigarh
python main.py -q "gyms in chandigarh" -m 50

# Example 2: Cafes in Bandra, Mumbai
python main.py -q "cafes in bandra mumbai" -m 30

# Example 3: Petrol pumps in Noida
python main.py -q "petrol pumps in noida" -m 20

# Example 4: Cinemas in Hyderabad with visible browser
python main.py -q "cinemas in hyderabad" -m 15 --headed
```

### CLI Arguments
| Flag | Description | Default |
|------|-------------|---------|
| `-q, --query` | Search query for Google Maps | Prompted if omitted |
| `-m, --max-results` | Maximum businesses to extract | `50` |
| `-o, --output` | Custom path for `.xlsx` file | `output/<query_slug>.xlsx` |
| `--no-emails` | Skip crawling websites for emails | Disabled (emails extracted) |
| `--headed` | Open visible browser window | False (headless) |
| `--workers` | Parallel worker threads for email crawler | `8` |

---

## Output Files
Generated files are stored in the `output/` folder:
- `output/<query_name>.xlsx` (Styled Excel file with auto-sized columns and hyperlinks)
- `output/<query_name>.csv` (Standard CSV file for CRM or spreadsheet import)
