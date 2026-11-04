"""
Google Maps Scraper Engine
Generic, domain-agnostic crawler for Google Maps using Playwright.
Works for ANY business domain (gyms, cafes, petrol pumps, parking, cinemas, clinics, etc.)
"""

import re
import time
import urllib.parse
from typing import List, Dict, Any, Optional, Callable
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

COORDINATES_REGEX = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")
DATA_COORDINATES_REGEX = re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")

def parse_coordinates(url: str):
    """Extract (latitude, longitude) from Google Maps URL."""
    if not url:
        return None, None
    m = DATA_COORDINATES_REGEX.search(url)
    if m:
        try:
            return float(m.group(1)), float(m.group(2))
        except ValueError:
            pass
    m2 = COORDINATES_REGEX.search(url)
    if m2:
        try:
            return float(m2.group(1)), float(m2.group(2))
        except ValueError:
            pass
    return None, None

def clean_text(text: Optional[str]) -> str:
    """Trim and clean text whitespace."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()

def dismiss_popups(page: Page):
    """Dismiss cookie, sign-in, or regional consent banners if present."""
    consent_selectors = [
        "button:has-text('Accept all')",
        "button:has-text('I agree')",
        "button:has-text('Agree')",
        "form[action*='consent'] button",
        "button[aria-label*='Accept']",
    ]
    for sel in consent_selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1000):
                btn.click()
                page.wait_for_timeout(1000)
                break
        except Exception:
            pass

def extract_details_from_pane(page: Page) -> Dict[str, Any]:
    """
    Extracts high-fidelity details (address, phone, website, hours)
    from Google Maps detail pane when a place is opened.
    """
    details: Dict[str, Any] = {
        "address": "",
        "phone": "",
        "website": "",
        "hours": "",
        "category": ""
    }

    # 1. Address
    try:
        addr_el = page.locator("button[data-item-id='address']").first
        if addr_el.is_visible(timeout=1200):
            aria = addr_el.get_attribute("aria-label") or ""
            if aria.lower().startswith("address:"):
                details["address"] = clean_text(aria.split(":", 1)[1])
            else:
                details["address"] = clean_text(addr_el.inner_text())
    except Exception:
        pass

    # 2. Website
    try:
        web_el = page.locator("a[data-item-id='authority']").first
        if web_el.is_visible(timeout=1000):
            href = web_el.get_attribute("href") or ""
            details["website"] = href.strip()
    except Exception:
        pass

    # 3. Phone Number
    try:
        phone_el = page.locator("button[data-item-id^='phone:']").first
        if phone_el.is_visible(timeout=1000):
            aria = phone_el.get_attribute("aria-label") or ""
            if aria.lower().startswith("phone:"):
                details["phone"] = clean_text(aria.split(":", 1)[1])
            else:
                details["phone"] = clean_text(phone_el.inner_text())
    except Exception:
        pass

    # 4. Category
    try:
        cat_el = page.locator("button[jsaction*='pane.rating.category'], button[jsaction*='category']").first
        if cat_el.is_visible(timeout=800):
            details["category"] = clean_text(cat_el.inner_text())
    except Exception:
        pass

    # 5. Hours / Open status
    try:
        hours_el = page.locator("div[data-item-id='oh'], button[data-item-id='oh']").first
        if hours_el.is_visible(timeout=800):
            aria = hours_el.get_attribute("aria-label") or ""
            details["hours"] = clean_text(aria or hours_el.inner_text())
    except Exception:
        pass

    return details

def scrape_google_maps(
    query: str,
    max_results: int = 50,
    headless: bool = True,
    status_callback: Optional[Callable[[str], None]] = None
) -> List[Dict[str, Any]]:
    """
    Search Google Maps for any query/domain and scrape business listings.
    
    Args:
        query: Search term (e.g., 'gyms in chandigarh', 'cafes in bandra', 'petrol pumps in noida')
        max_results: Maximum number of businesses to extract (default 50)
        headless: Whether to run Chromium headlessly (default True)
        status_callback: Optional callback function for real-time progress logging
    """
    def log(msg: str):
        if status_callback:
            status_callback(msg)
        else:
            print(msg)

    log(f"Starting Google Maps search for: '{query}' (Max results: {max_results})")
    scraped_places: List[Dict[str, Any]] = []
    seen_urls = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-setuid-sandbox",
                "--no-zygote",
                "--lang=en-US"
            ]
        )
        context = browser.new_context(
            locale="en-US",
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        # Build search URL with English language forced for consistent parsing
        encoded_query = urllib.parse.quote_plus(query)
        search_url = f"https://www.google.com/maps/search/{encoded_query}/?hl=en"

        log(f"Navigating to Google Maps...")
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=40000)
        except Exception as e:
            log(f"Initial navigation notice: {e}")

        dismiss_popups(page)

        # Check if direct single-place redirect occurred
        if "/maps/place/" in page.url:
            log("Search redirected directly to a single place page.")
            name = clean_text(page.locator("h1").first.inner_text())
            rating = None
            try:
                rating_str = page.locator("span[aria-hidden='true']").first.inner_text()
                rating = float(rating_str)
            except Exception:
                pass
            reviews = None
            try:
                rev_text = page.locator("span:has-text('reviews')").first.inner_text()
                rev_m = re.search(r"(\d[\d,]*)", rev_text)
                if rev_m:
                    reviews = int(rev_m.group(1).replace(",", ""))
            except Exception:
                pass

            details = extract_details_from_pane(page)
            lat, lng = parse_coordinates(page.url)

            place_data = {
                "name": name,
                "category": details.get("category", ""),
                "rating": rating,
                "reviews_count": reviews,
                "phone": details.get("phone", ""),
                "emails": "",
                "address": details.get("address", ""),
                "website": details.get("website", ""),
                "google_maps_url": page.url,
                "latitude": lat,
                "longitude": lng,
                "hours": details.get("hours", "")
            }
            browser.close()
            return [place_data]

        # Wait for the results feed
        try:
            page.wait_for_selector("div[role='feed']", timeout=20000)
        except Exception:
            log("No feed container found. Checking if any results exist...")

        feed_selector = "div[role='feed']"
        
        # Infinite scroll to load results up to max_results
        log("Loading search results from feed...")
        stagnant_count = 0
        last_item_count = 0

        while True:
            # Get list of place links currently in the feed
            cards = page.locator("div[role='feed'] a.hfpxzc").all()
            current_count = len(cards)
            log(f"Found {current_count} listings loaded so far...")

            if current_count >= max_results:
                break

            # Check if end of list is reached
            try:
                end_marker = page.locator("p:has-text('reached the end of the list'), span:has-text('reached the end')").first
                if end_marker.is_visible(timeout=500):
                    log("Reached the end of the Google Maps results list.")
                    break
            except Exception:
                pass

            # Scroll down inside feed container
            page.evaluate(
                """() => {
                    const feed = document.querySelector('div[role="feed"]');
                    if (feed) {
                        feed.scrollTop += 2000;
                    } else {
                        window.scrollBy(0, 1000);
                    }
                }"""
            )
            page.wait_for_timeout(1800)

            # Check if count stopped increasing
            new_cards = page.locator("div[role='feed'] a.hfpxzc").all()
            if len(new_cards) == last_item_count:
                stagnant_count += 1
                if stagnant_count >= 4:
                    log("No additional listings loading. Proceeding with collected results.")
                    break
            else:
                stagnant_count = 0
                last_item_count = len(new_cards)

        # Now extract data for each listing
        cards = page.locator("div[role='feed'] a.hfpxzc").all()
        target_cards = cards[:max_results]
        log(f"Extracting detailed information for {len(target_cards)} businesses...")

        # Collect basic info first from feed elements
        collected_summaries = []
        for i, card in enumerate(target_cards):
            try:
                name = card.get_attribute("aria-label") or ""
                href = card.get_attribute("href") or ""
                if not href or href in seen_urls:
                    continue
                seen_urls.add(href)

                # Attempt to get rating & reviews from parent container
                rating = None
                reviews = None
                category = ""
                snippet_addr = ""

                try:
                    parent = card.locator("xpath=..")
                    # Rating
                    rating_el = parent.locator("span.MW4etd").first
                    if rating_el.is_visible(timeout=300):
                        try:
                            rating = float(rating_el.inner_text().strip())
                        except ValueError:
                            pass
                    
                    # Reviews
                    reviews_el = parent.locator("span.UY7F9").first
                    if reviews_el.is_visible(timeout=300):
                        rev_text = reviews_el.inner_text()
                        m_rev = re.search(r"(\d[\d,]*)", rev_text)
                        if m_rev:
                            reviews = int(m_rev.group(1).replace(",", ""))
                except Exception:
                    pass

                lat, lng = parse_coordinates(href)

                collected_summaries.append({
                    "name": clean_text(name),
                    "google_maps_url": href,
                    "rating": rating,
                    "reviews_count": reviews,
                    "latitude": lat,
                    "longitude": lng,
                    "card_index": i
                })
            except Exception:
                continue

        # Create a second page / tab to visit each place directly and extract full details
        # Visiting the place URL directly in a tab is fast, non-destructive, and doesn't disrupt feed scroll!
        detail_page = context.new_page()

        for idx, item in enumerate(collected_summaries, start=1):
            log(f"[{idx}/{len(collected_summaries)}] Fetching details: {item['name']}")
            try:
                detail_page.goto(item["google_maps_url"], wait_until="domcontentloaded", timeout=25000)
                detail_page.wait_for_timeout(1000)
                
                details = extract_details_from_pane(detail_page)
                
                # If rating or reviews were missing in feed, check detail pane
                if item["rating"] is None:
                    try:
                        r_el = detail_page.locator("div.fontDisplayLarge").first
                        if r_el.is_visible(timeout=500):
                            item["rating"] = float(r_el.inner_text().strip())
                    except Exception:
                        pass

                if item["reviews_count"] is None:
                    try:
                        rev_el = detail_page.locator("span:has-text('reviews')").first
                        if rev_el.is_visible(timeout=500):
                            m_rev = re.search(r"(\d[\d,]*)", rev_el.inner_text())
                            if m_rev:
                                item["reviews_count"] = int(m_rev.group(1).replace(",", ""))
                    except Exception:
                        pass

                # Update coordinates from final redirected URL if missing
                if not item["latitude"] or not item["longitude"]:
                    lat, lng = parse_coordinates(detail_page.url)
                    item["latitude"] = lat
                    item["longitude"] = lng

                item["category"] = details.get("category", "")
                item["address"] = details.get("address", "")
                item["phone"] = details.get("phone", "")
                item["website"] = details.get("website", "")
                item["hours"] = details.get("hours", "")
                item["emails"] = ""

                scraped_places.append(item)
            except Exception as e:
                log(f"  Notice fetching details for {item['name']}: {e}")
                # Append with whatever summary was captured
                item.setdefault("category", "")
                item.setdefault("address", "")
                item.setdefault("phone", "")
                item.setdefault("website", "")
                item.setdefault("hours", "")
                item.setdefault("emails", "")
                scraped_places.append(item)

        detail_page.close()
        browser.close()

    log(f"Successfully scraped {len(scraped_places)} places from Google Maps.")
    return scraped_places
