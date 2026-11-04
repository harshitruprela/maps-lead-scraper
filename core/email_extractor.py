"""
Email Extractor Module
Extracts verified contact emails from business websites by inspecting
homepages and contact/about subpages.
"""

import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Set, Dict, Optional
import requests
from bs4 import BeautifulSoup

EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,12}\b"
)

# Common extensions or domains to filter out
IGNORE_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".ico",
    ".css", ".js", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3"
)

IGNORE_DOMAINS = {
    "example.com", "domain.com", "yourdomain.com", "test.com", "email.com",
    "mysite.com", "wixpress.com", "sentry.io", "github.com", "google.com",
    "facebook.com", "instagram.com", "twitter.com", "youtube.com", "linkedin.com",
    "schema.org", "w3.org", "cloudflare.com", "wordpress.org"
}

IGNORE_PREFIXES = {
    "bootstrap", "jquery", "fontawesome", "npm", "webpack", "react", "vue", "angular"
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def clean_email(email_str: str) -> Optional[str]:
    """Clean and validate an extracted email string."""
    if not email_str:
        return None
    email = email_str.strip().lower().rstrip(".,;:)'\"")
    
    # Structural check
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        return None
    
    # Reject static asset filenames mistakenly captured
    for ext in IGNORE_EXTENSIONS:
        if email.endswith(ext):
            return None
            
    parts = email.split("@")
    if len(parts) != 2:
        return None
    
    user_part, domain = parts[0], parts[1]
    
    # Filter common dev/framework tags like bootstrap@5.3.0
    if user_part in IGNORE_PREFIXES or any(domain.startswith(p) for p in IGNORE_PREFIXES):
        return None

    if domain in IGNORE_DOMAINS:
        return None
    
    if "." not in domain:
        return None
        
    # Check TLD: must be purely alphabetic letters (e.g. .com, .in, .org, .co, .net)
    tld = domain.split(".")[-1]
    if not re.match(r"^[a-z]{2,12}$", tld):
        return None
        
    return email

def extract_emails_from_html(html_text: str) -> Set[str]:
    """Extract email addresses from HTML text and mailto: links."""
    found_emails: Set[str] = set()
    if not html_text:
        return found_emails

    try:
        soup = BeautifulSoup(html_text, "html.parser")
        
        # 1. Look for mailto: links
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if href.lower().startswith("mailto:"):
                raw_mail = href[7:].split("?")[0]
                cleaned = clean_email(raw_mail)
                if cleaned:
                    found_emails.add(cleaned)

        # 2. Look in entire page text and raw content via regex
        matches = EMAIL_REGEX.findall(html_text)
        for match in matches:
            cleaned = clean_email(match)
            if cleaned:
                found_emails.add(cleaned)
    except Exception:
        pass

    return found_emails

def fetch_url_html(url: str, timeout: int = 6) -> Optional[str]:
    """Fetch HTML content of a URL safely with timeout."""
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True,
            verify=False  # Avoid SSL failure on local business certificates
        )
        if response.status_code == 200 and "text/html" in response.headers.get("Content-Type", "").lower():
            return response.text
    except Exception:
        pass
    return None

def extract_emails_for_website(website_url: str, timeout: int = 6) -> List[str]:
    """
    Given a business website URL, crawl the homepage and candidate contact/about
    pages to find business email addresses.
    """
    if not website_url or not isinstance(website_url, str):
        return []

    url = website_url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    # Skip social media platforms where business email won't be on the main page
    parsed = urllib.parse.urlparse(url)
    netloc = parsed.netloc.lower()
    if any(sm in netloc for sm in ["instagram.com", "facebook.com", "wa.me", "maps.google.com"]):
        return []

    all_emails: Set[str] = set()

    # 1. Fetch homepage
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    home_html = fetch_url_html(url, timeout=timeout)
    if home_html:
        all_emails.update(extract_emails_from_html(home_html))

    # 2. If no email or only 1 found, check contact and about pages
    if len(all_emails) < 2:
        candidate_paths = ["/contact", "/contact-us", "/about", "/about-us"]
        for path in candidate_paths:
            target_url = urllib.parse.urljoin(base_url, path)
            if target_url == url:
                continue
            sub_html = fetch_url_html(target_url, timeout=timeout)
            if sub_html:
                all_emails.update(extract_emails_from_html(sub_html))
            if all_emails:
                break  # Stop as soon as we found contact info

    return sorted(list(all_emails))

def batch_extract_emails(websites: List[str], max_workers: int = 8) -> Dict[str, str]:
    """
    Extract emails for a list of website URLs concurrently.
    Returns a dict mapping website_url -> comma-separated emails.
    """
    results: Dict[str, str] = {}
    unique_sites = list({w for w in websites if w and isinstance(w, str) and w.strip()})
    
    if not unique_sites:
        return results

    # Suppress InsecureRequestWarning for verify=False requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(extract_emails_for_website, site): site
            for site in unique_sites
        }
        for future in as_completed(future_to_url):
            site = future_to_url[future]
            try:
                emails = future.result()
                results[site] = ", ".join(emails) if emails else ""
            except Exception:
                results[site] = ""

    return results
