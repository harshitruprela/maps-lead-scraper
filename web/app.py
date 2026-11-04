"""
FastAPI Web Application for Google Maps Lead Scraper
Provides a sleek web interface with live scraping progress,
on-page results viewing, and one-click Excel/CSV downloads.
"""

import os
import sys
import uuid
import threading
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.gmaps_scraper import scrape_google_maps
from core.email_extractor import batch_extract_emails
from core.excel_exporter import export_to_excel

app = FastAPI(title="Google Maps Scraper Web")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# In-memory jobs tracking
jobs: Dict[str, Dict[str, Any]] = {}

class ScrapeRequest(BaseModel):
    query: str
    max_results: int = 20
    extract_emails: bool = True

def run_scraping_worker(job_id: str, query: str, max_results: int, extract_emails: bool):
    """Background worker executing the complete scrape and export pipeline."""
    job = jobs[job_id]
    try:
        job["status"] = "running"
        job["progress"] = 10
        job["message"] = f"Initializing Google Maps crawler for '{query}'..."

        def status_cb(msg: str):
            job["message"] = msg
            # Estimate progress based on step
            if "loaded so far" in msg:
                job["progress"] = min(35, job["progress"] + 5)
            elif "Fetching details:" in msg:
                job["progress"] = min(65, job["progress"] + 3)

        # 1. Scrape Google Maps
        places = scrape_google_maps(
            query=query,
            max_results=max_results,
            headless=True,
            status_callback=status_cb
        )

        if not places:
            job["status"] = "completed"
            job["progress"] = 100
            job["message"] = "No places found for the specified query."
            job["results"] = []
            return

        job["progress"] = 70
        job["message"] = f"Gathered {len(places)} listings. Checking websites for contact emails..."

        # 2. Extract emails from business websites if enabled
        if extract_emails:
            websites = [p.get("website") for p in places if p.get("website")]
            if websites:
                job["message"] = f"Mining emails from {len(websites)} business websites..."
                email_map = batch_extract_emails(websites, max_workers=8)
                for p in places:
                    site = p.get("website")
                    if site and site in email_map:
                        p["emails"] = email_map[site]

        job["progress"] = 90
        job["message"] = "Generating styled Excel spreadsheet..."

        # 3. Export to Excel & CSV
        clean_name = "".join(c if c.isalnum() else "_" for c in query.lower()).strip("_")
        excel_filename = f"{clean_name}_{job_id[:8]}.xlsx"
        excel_path = os.path.join(OUTPUT_DIR, excel_filename)
        export_to_excel(places, excel_path)

        csv_path = os.path.splitext(excel_path)[0] + ".csv"

        job["status"] = "completed"
        job["progress"] = 100
        job["message"] = f"Completed successfully! Extracted {len(places)} businesses."
        job["results"] = places
        job["excel_path"] = excel_path
        job["csv_path"] = csv_path
        job["excel_filename"] = excel_filename
        job["csv_filename"] = os.path.basename(csv_path)

    except Exception as e:
        job["status"] = "failed"
        job["message"] = f"Error during extraction: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the main web dashboard."""
    index_file = os.path.join(TEMPLATES_DIR, "index.html")
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/scrape")
async def start_scrape(req: ScrapeRequest, background_tasks: BackgroundTasks):
    """Start a new scraping job in background."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Search query is required.")

    limit = min(max(1, req.max_results), 100)
    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "job_id": job_id,
        "query": req.query.strip(),
        "max_results": limit,
        "status": "pending",
        "progress": 0,
        "message": "Job queued...",
        "results": [],
        "excel_path": None,
        "csv_path": None
    }

    # Start scraping in a dedicated thread
    worker_thread = threading.Thread(
        target=run_scraping_worker,
        args=(job_id, req.query.strip(), limit, req.extract_emails),
        daemon=True
    )
    worker_thread.start()

    return {"job_id": job_id, "status": "started"}

@app.get("/api/status/{job_id}")
async def get_job_status(job_id: str):
    """Poll scraping status and progress."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    
    job = jobs[job_id]
    return {
        "job_id": job_id,
        "query": job.get("query"),
        "status": job.get("status"),
        "progress": job.get("progress", 0),
        "message": job.get("message", ""),
        "total_results": len(job.get("results", [])),
        "has_excel": bool(job.get("excel_path")),
        "has_csv": bool(job.get("csv_path")),
    }

@app.get("/api/results/{job_id}")
async def get_job_results(job_id: str):
    """Fetch scraped business records for table display."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {"results": jobs[job_id].get("results", [])}

@app.get("/api/download/{job_id}")
async def download_file(job_id: str, format: str = "xlsx"):
    """Directly download generated Excel or CSV file."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    
    job = jobs[job_id]
    if job.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet.")

    if format.lower() == "csv":
        filepath = job.get("csv_path")
        filename = job.get("csv_filename", "export.csv")
        media_type = "text/csv"
    else:
        filepath = job.get("excel_path")
        filename = job.get("excel_filename", "export.xlsx")
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Requested file not found on disk.")

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type=media_type
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="127.0.0.1", port=8000, reload=True)
