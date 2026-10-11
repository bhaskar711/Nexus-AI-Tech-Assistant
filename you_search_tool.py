import os
import re
import time
from urllib.parse import urlparse, quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YDC_API_KEY")

YDC_BASE_URL = "https://ydc-index.io/v1/search"

REQUEST_TIMEOUT = 15
PAGE_TIMEOUT = 12

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/153.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}


# ============================================================
# SEARCH SOURCE PRIORITY
# ============================================================

TRUSTED_SOURCE_PRIORITY = {
    "apple.com": 100,
    "samsung.com": 100,
    "google.com": 100,
    "oneplus.com": 100,
    "xiaomi.com": 100,
    "mi.com": 100,
    "motorola.com": 100,
    "nothing.tech": 100,
    "oppo.com": 100,
    "vivo.com": 100,
    "realme.com": 100,
    "iqoo.com": 100,
    "iqoo.in": 100,
    "honor.com": 100,
    "asus.com": 100,
    "sony.com": 100,
    "poco.net": 100,
    "tecno-mobile.com": 100,
    "infinixmobility.com": 100,

    "gsmarena.com": 90,
    "91mobiles.com": 85,
    "gadgets360.com": 80,

    "androidauthority.com": 70,
    "phonearena.com": 70,
    "theverge.com": 70,
    "techradar.com": 70,
    "digit.in": 65,
    "smartprix.com": 60
}


LOW_QUALITY_DOMAINS = {
    "youtube.com",
    "youtu.be",
    "wikipedia.org",
    "devicespecifications.com",
    "kimovil.com"
}


# ============================================================
# DOMAIN
# ============================================================

def get_domain(url):

    if not url or url == "Unknown":
        return ""

    try:
        hostname = urlparse(url).hostname

        if not hostname:
            return ""

        hostname = hostname.lower()

        if hostname.startswith("www."):
            hostname = hostname[4:]

        return hostname

    except Exception:
        return ""


def domain_matches(domain, target):

    if not domain or not target:
        return False

    domain = domain.lower().strip()
    target = target.lower().strip()

    return (
        domain == target
        or domain.endswith("." + target)
    )


def source_priority(domain):

    domain = (domain or "").lower()

    for trusted_domain, priority in TRUSTED_SOURCE_PRIORITY.items():

        if domain_matches(domain, trusted_domain):
            return priority

    return 0


def is_low_quality_domain(domain):

    domain = (domain or "").lower()

    for bad_domain in LOW_QUALITY_DOMAINS:

        if domain_matches(domain, bad_domain):
            return True

    return False


# ============================================================
# BASIC YDC SEARCH
# ============================================================

def ydc_web_search(query, count=5):

    if not API_KEY:
        raise RuntimeError(
            "YDC_API_KEY was not found in the environment."
        )

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT
    }

    data = {
        "query": query,
        "count": count
    }

    last_error = None

    for attempt in range(2):

        try:

            response = requests.post(
                YDC_BASE_URL,
                headers=headers,
                json=data,
                timeout=REQUEST_TIMEOUT
            )

            response.raise_for_status()

            return response.json()

        except Exception as error:

            last_error = error

            if attempt == 0:
                time.sleep(0.5)

    raise RuntimeError(
        f"YDC search failed: {last_error}"
    )


# ============================================================
# DUCKDUCKGO FALLBACK SEARCH
# ============================================================

def duckduckgo_search(query, count=8):

    url = (
        "https://html.duckduckgo.com/html/?q="
        + quote_plus(query)
    )

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        results = []

        for item in soup.select(".result"):

            link = item.select_one(
                ".result__a"
            )

            if not link:
                continue

            href = link.get("href", "")

            title = link.get_text(
                " ",
                strip=True
            )

            snippet_element = item.select_one(
                ".result__snippet"
            )

            description = ""

            if snippet_element:
                description = snippet_element.get_text(
                    " ",
                    strip=True
                )

            if not href:
                continue

            domain = get_domain(href)

            results.append({
                "type": "WEB",
                "title": title or "Unknown",
                "url": href,
                "domain": domain,
                "date": "Unknown",
                "description": description,
                "snippets": [description]
                if description else [],
                "search_source": "DuckDuckGo"
            })

            if len(results) >= count:
                break

        return results

    except Exception as error:

        print(
            f"[FALLBACK SEARCH WARNING] "
            f"DuckDuckGo: {error}"
        )

        return []


# ============================================================
# BING FALLBACK SEARCH
# ============================================================

def bing_search(query, count=8):

    url = (
        "https://www.bing.com/search?q="
        + quote_plus(query)
    )

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        results = []

        for item in soup.select("li.b_algo"):

            link = item.select_one("h2 a")

            if not link:
                continue

            href = link.get("href", "")

            title = link.get_text(
                " ",
                strip=True
            )

            snippet_element = item.select_one(
                ".b_caption p"
            )

            description = ""

            if snippet_element:
                description = snippet_element.get_text(
                    " ",
                    strip=True
                )

            if not href:
                continue

            domain = get_domain(href)

            results.append({
                "type": "WEB",
                "title": title or "Unknown",
                "url": href,
                "domain": domain,
                "date": "Unknown",
                "description": description,
                "snippets": [description]
                if description else [],
                "search_source": "Bing"
            })

            if len(results) >= count:
                break

        return results

    except Exception as error:

        print(
            f"[FALLBACK SEARCH WARNING] "
            f"Bing: {error}"
        )

        return []


# ============================================================
# NORMALIZE RESULT
# ============================================================

def normalize_result(result, search_source="YDC"):

    if not isinstance(result, dict):
        return None

    url = result.get(
        "url",
        ""
    )

    if not url:
        return None

    snippets = result.get(
        "snippets",
        []
    )

    if isinstance(snippets, str):
        snippets = [snippets]

    if not isinstance(snippets, list):
        snippets = []

    return {
        "type": result.get(
            "type",
            "WEB"
        ),
        "title": result.get(
            "title",
            "Unknown"
        ),
        "url": url,
        "domain": get_domain(url),
        "date": result.get(
            "date",
            result.get(
                "page_age",
                "Unknown"
            )
        ),
        "description": result.get(
            "description",
            ""
        ),
        "snippets": snippets,
        "search_source": result.get(
            "search_source",
            search_source
        )
    }


# ============================================================
# EXTRACT ALL YDC SEARCH RESULTS
# ============================================================

def get_all_web_results(data):

    if not isinstance(data, dict):
        return []

    results = data.get(
        "results",
        {}
    )

    if not isinstance(results, dict):
        return []

    web_results = results.get(
        "web",
        []
    )

    news_results = results.get(
        "news",
        []
    )

    if not isinstance(web_results, list):
        web_results = []

    if not isinstance(news_results, list):
        news_results = []

    all_results = []

    for result in web_results:

        normalized = normalize_result(
            result,
            "YDC"
        )

        if normalized:
            all_results.append(
                normalized
            )

    for result in news_results:

        normalized = normalize_result(
            result,
            "YDC"
        )

        if normalized:

            normalized["type"] = "NEWS"

            all_results.append(
                normalized
            )

    return all_results


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def deduplicate_results(results):

    if not results:
        return []

    unique = {}

    for result in results:

        if not isinstance(result, dict):
            continue

        url = result.get(
            "url",
            ""
        )

        if not url:
            continue

        normalized_url = url.split("#")[0].rstrip("/")

        if normalized_url not in unique:
            unique[normalized_url] = result

    return list(
        unique.values()
    )


# ============================================================
# SORT RESULTS
# ============================================================

def rank_results(results):

    if not results:
        return []

    def ranking(result):

        domain = result.get(
            "domain",
            ""
        )

        priority = source_priority(
            domain
        )

        low_quality = (
            0
            if is_low_quality_domain(domain)
            else 1
        )

        has_description = (
            1
            if result.get(
                "description",
                ""
            )
            else 0
        )

        has_snippets = (
            1
            if result.get(
                "snippets",
                []
            )
            else 0
        )

        return (
            low_quality,
            priority,
            has_description,
            has_snippets
        )

    return sorted(
        results,
        key=ranking,
        reverse=True
    )


# ============================================================
# BASIC WEB SEARCH WITH FALLBACK
# ============================================================

def web_search(query, count=5):

    print(
        f"[WEB SEARCH] {query}"
    )

    ydc_results = []

    # --------------------------------------------------------
    # 1. PRIMARY: YDC
    # --------------------------------------------------------

    try:

        data = ydc_web_search(
            query,
            count=count
        )

        ydc_results = get_all_web_results(
            data
        )

        if ydc_results:

            ydc_results = rank_results(
                deduplicate_results(
                    ydc_results
                )
            )

            print(
                f"[WEB SEARCH] YDC returned "
                f"{len(ydc_results)} results."
            )

            return {
                "results": {
                    "web": ydc_results,
                    "news": []
                },
                "search_source": "YDC"
            }

        print(
            "[WEB SEARCH] YDC returned no results."
        )

    except Exception as error:

        print(
            f"[WEB SEARCH WARNING] "
            f"YDC failed: {error}"
        )

    # --------------------------------------------------------
    # 2. FALLBACK: DUCKDUCKGO
    # --------------------------------------------------------

    print(
        "[WEB SEARCH] Trying DuckDuckGo fallback..."
    )

    ddg_results = duckduckgo_search(
        query,
        count=count
    )

    if ddg_results:

        ddg_results = rank_results(
            deduplicate_results(
                ddg_results
            )
        )

        print(
            f"[WEB SEARCH] DuckDuckGo returned "
            f"{len(ddg_results)} results."
        )

        return {
            "results": {
                "web": ddg_results,
                "news": []
            },
            "search_source": "DuckDuckGo"
        }

    # --------------------------------------------------------
    # 3. FALLBACK: BING
    # --------------------------------------------------------

    print(
        "[WEB SEARCH] Trying Bing fallback..."
    )

    bing_results = bing_search(
        query,
        count=count
    )

    if bing_results:

        bing_results = rank_results(
            deduplicate_results(
                bing_results
            )
        )

        print(
            f"[WEB SEARCH] Bing returned "
            f"{len(bing_results)} results."
        )

        return {
            "results": {
                "web": bing_results,
                "news": []
            },
            "search_source": "Bing"
        }

    # --------------------------------------------------------
    # COMPLETE FAILURE
    # --------------------------------------------------------

    print(
        "[WEB SEARCH] All search providers failed."
    )

    return {
        "results": {
            "web": [],
            "news": []
        },
        "search_source": "NONE"
    }


# ============================================================
# FORMAT SEARCH RESULT EVIDENCE
# ============================================================

def format_search_results(data):

    all_results = get_all_web_results(
        data
    )

    all_results = rank_results(
        deduplicate_results(
            all_results
        )
    )

    ordered_results = all_results[:8]

    formatted = []

    formatted.append(
        "WEB SEARCH RESULT EVIDENCE\n"
    )

    if not ordered_results:

        formatted.append(
            "NO SEARCH RESULTS FOUND\n"
        )

        return "\n".join(
            formatted
        )

    for index, result in enumerate(
        ordered_results,
        start=1
    ):

        formatted.append(
            f"SOURCE {index}\n"
        )

        formatted.append(
            f"SEARCH SOURCE: "
            f"{result.get('search_source', 'Unknown')}\n"
        )

        formatted.append(
            f"TYPE: {result['type']}\n"
        )

        formatted.append(
            f"TITLE: {result['title']}\n"
        )

        formatted.append(
            f"URL: {result['url']}\n"
        )

        formatted.append(
            f"DOMAIN: {result['domain']}\n"
        )

        formatted.append(
            f"DATE: {result['date']}\n"
        )

        formatted.append(
            f"DESCRIPTION: "
            f"{result['description']}\n"
        )

        snippets = result.get(
            "snippets",
            []
        )

        if isinstance(
            snippets,
            list
        ) and snippets:

            formatted.append(
                "EVIDENCE:\n"
            )

            for snippet in snippets[:3]:

                formatted.append(
                    f"- {snippet}\n"
                )

        formatted.append(
            "\n------------------------------\n"
        )

    return "\n".join(
        formatted
    )


# ============================================================
# TRUSTED SOURCE SEARCH
# ============================================================

def search_one_trusted_source(
    query,
    domain,
    count=5
):

    domain_query = (
        f"{query} site:{domain}"
    )

    # --------------------------------------------------------
    # PRIMARY SEARCH
    # --------------------------------------------------------

    try:

        data = web_search(
            domain_query,
            count=count
        )

        results = get_all_web_results(
            data
        )

        trusted_results = []

        for result in results:

            result_domain = result.get(
                "domain",
                ""
            )

            if domain_matches(
                result_domain,
                domain
            ):

                trusted_results.append(
                    result
                )

        if trusted_results:
            return trusted_results

    except Exception as error:

        print(
            f"[SEARCH WARNING] "
            f"{domain}: {error}"
        )

    # --------------------------------------------------------
    # DIRECT DUCKDUCKGO FALLBACK
    # --------------------------------------------------------

    try:

        print(
            f"[SEARCH FALLBACK] "
            f"Direct DuckDuckGo search for {domain}"
        )

        results = duckduckgo_search(
            domain_query,
            count=count
        )

        trusted_results = []

        for result in results:

            result_domain = result.get(
                "domain",
                ""
            )

            if domain_matches(
                result_domain,
                domain
            ):

                trusted_results.append(
                    result
                )

        return trusted_results

    except Exception as error:

        print(
            f"[SEARCH WARNING] "
            f"{domain}: {error}"
        )

        return []


def search_trusted_sources(
    query,
    trusted_domains,
    count=5
):

    if not trusted_domains:
        return []

    trusted_results = []

    worker_count = min(
        len(trusted_domains),
        8
    )

    with ThreadPoolExecutor(
        max_workers=worker_count
    ) as executor:

        futures = [
            executor.submit(
                search_one_trusted_source,
                query,
                domain,
                count
            )
            for domain in trusted_domains
        ]

        for future in as_completed(
            futures
        ):

            try:

                results = future.result()

                if results:
                    trusted_results.extend(
                        results
                    )

            except Exception as error:

                print(
                    f"[SEARCH WARNING] "
                    f"{error}"
                )

    trusted_results = deduplicate_results(
        trusted_results
    )

    trusted_results = rank_results(
        trusted_results
    )

    return trusted_results


# ============================================================
# FORMAT TRUSTED RESULTS
# ============================================================

def format_trusted_results(
    results
):

    results = rank_results(
        deduplicate_results(
            results
        )
    )

    formatted = []

    formatted.append(
        "TRUSTED WEB EVIDENCE\n"
    )

    if not results:

        formatted.append(
            "NO TRUSTED SOURCE RESULTS FOUND\n"
        )

        return "\n".join(
            formatted
        )

    for index, result in enumerate(
        results,
        start=1
    ):

        formatted.append(
            f"SOURCE {index}\n"
        )

        formatted.append(
            f"SEARCH SOURCE: "
            f"{result.get('search_source', 'Unknown')}\n"
        )

        formatted.append(
            f"TYPE: "
            f"{result.get('type', 'WEB')}\n"
        )

        formatted.append(
            f"TITLE: "
            f"{result.get('title', 'Unknown')}\n"
        )

        formatted.append(
            f"URL: "
            f"{result.get('url', 'Unknown')}\n"
        )

        formatted.append(
            f"DOMAIN: "
            f"{result.get('domain', 'Unknown')}\n"
        )

        formatted.append(
            f"DATE: "
            f"{result.get('date', 'Unknown')}\n"
        )

        formatted.append(
            f"DESCRIPTION: "
            f"{result.get('description', '')}\n"
        )

        snippets = result.get(
            "snippets",
            []
        )

        if isinstance(
            snippets,
            list
        ) and snippets:

            formatted.append(
                "EVIDENCE:\n"
            )

            for snippet in snippets[:3]:

                formatted.append(
                    f"- {snippet}\n"
                )

        formatted.append(
            "\n------------------------------\n"
        )

    return "\n".join(
        formatted
    )


# ============================================================
# WEBPAGE CONTENT EXTRACTION
# ============================================================

def clean_page_text(text):

    if not text:
        return ""

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def fetch_webpage(url):

    if not url or url == "Unknown":
        return ""

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=PAGE_TIMEOUT,
            allow_redirects=True
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type",
            ""
        ).lower()

        if (
            "text/html" not in content_type
            and "application/xhtml" not in content_type
        ):
            return ""

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # ----------------------------------------------------
        # Remove elements that are normally irrelevant
        # ----------------------------------------------------

        for tag in soup([
            "script",
            "style",
            "noscript",
            "svg",
            "nav",
            "footer",
            "header",
            "form",
            "iframe",
            "aside"
        ]):

            tag.decompose()

        # ----------------------------------------------------
        # Prefer main/article content when available
        # ----------------------------------------------------

        main = soup.find(
            "main"
        )

        if not main:
            main = soup.find(
                "article"
            )

        if main:

            text = main.get_text(
                separator=" ",
                strip=True
            )

        else:

            text = soup.get_text(
                separator=" ",
                strip=True
            )

        text = clean_page_text(
            text
        )

        return text

    except Exception as error:

        print(
            f"[PAGE WARNING] "
            f"{url}: {error}"
        )

        return ""


# ============================================================
# SMART PAGE CONTENT EXTRACTION
# ============================================================

def extract_relevant_page_text(
    text,
    query="",
    max_characters=18000
):

    if not text:
        return ""

    text = clean_page_text(
        text
    )

    if len(text) <= max_characters:
        return text

    # --------------------------------------------------------
    # Keep sections surrounding important specification words
    # --------------------------------------------------------

    keywords = [
        "display",
        "screen",
        "camera",
        "battery",
        "charging",
        "processor",
        "chipset",
        "soc",
        "refresh rate",
        "resolution",
        "oled",
        "amoled",
        "ltpo",
        "megapixel",
        "mp",
        "mah",
        "wireless charging",
        "wired charging"
    ]

    lower_text = text.lower()

    chunks = []

    for keyword in keywords:

        start = 0

        while True:

            position = lower_text.find(
                keyword,
                start
            )

            if position == -1:
                break

            chunk_start = max(
                0,
                position - 500
            )

            chunk_end = min(
                len(text),
                position + 1500
            )

            chunks.append(
                text[
                    chunk_start:chunk_end
                ]
            )

            start = (
                position
                + len(keyword)
            )

            if len(chunks) >= 30:
                break

        if len(chunks) >= 30:
            break

    if chunks:

        combined = " ".join(
            chunks
        )

        combined = clean_page_text(
            combined
        )

        # Remove excessive duplicate sections
        if len(combined) > max_characters:

            combined = combined[
                :max_characters
            ]

        return combined

    return text[
        :max_characters
    ]


def fetch_one_search_page(
    result,
    max_characters_per_page
):

    if not isinstance(
        result,
        dict
    ):
        return None

    url = result.get(
        "url",
        ""
    )

    if not url or url == "Unknown":
        return None

    domain = result.get(
        "domain",
        ""
    )

    print(
        f"[PAGE] Opening: {url}"
    )

    page_text = fetch_webpage(
        url
    )

    if not page_text:

        print(
            "[PAGE] No readable content."
        )

        return None

    page_text = extract_relevant_page_text(
        page_text,
        max_characters=max_characters_per_page
    )

    print(
        f"[PAGE] Extracted "
        f"{len(page_text)} relevant characters "
        f"from {domain}."
    )

    return {
        "type": result.get(
            "type",
            "WEB"
        ),
        "title": result.get(
            "title",
            "Unknown"
        ),
        "url": url,
        "domain": domain,
        "date": result.get(
            "date",
            "Unknown"
        ),
        "description": result.get(
            "description",
            ""
        ),
        "snippets": result.get(
            "snippets",
            []
        ),
        "content": page_text,
        "search_source": result.get(
            "search_source",
            "Unknown"
        )
    }


def fetch_search_result_pages(
    results,
    max_pages=5,
    max_characters_per_page=12000
):

    if not results:
        return []

    results = deduplicate_results(
        results
    )

    results = rank_results(
        results
    )

    # --------------------------------------------------------
    # Prefer trusted sources
    # --------------------------------------------------------

    selected_results = results[
        :max_pages
    ]

    if not selected_results:
        return []

    pages = []

    worker_count = min(
        len(selected_results),
        5
    )

    with ThreadPoolExecutor(
        max_workers=worker_count
    ) as executor:

        futures = [
            executor.submit(
                fetch_one_search_page,
                result,
                max_characters_per_page
            )
            for result in selected_results
        ]

        for future in as_completed(
            futures
        ):

            try:

                page = future.result()

                if page:
                    pages.append(
                        page
                    )

            except Exception as error:

                print(
                    f"[PAGE WARNING] "
                    f"{error}"
                )

    # --------------------------------------------------------
    # Restore trusted-source ordering
    # --------------------------------------------------------

    pages.sort(
        key=lambda page: (
            source_priority(
                page.get(
                    "domain",
                    ""
                )
            )
        ),
        reverse=True
    )

    return pages


# ============================================================
# FETCH TRUSTED PAGES DIRECTLY
# ============================================================

def fetch_trusted_pages(
    results,
    max_pages=6,
    max_characters_per_page=14000
):

    if not results:
        return []

    trusted = []

    for result in results:

        domain = result.get(
            "domain",
            ""
        )

        if source_priority(
            domain
        ) > 0:

            trusted.append(
                result
            )

    trusted = rank_results(
        deduplicate_results(
            trusted
        )
    )

    return fetch_search_result_pages(
        trusted,
        max_pages=max_pages,
        max_characters_per_page=max_characters_per_page
    )


# ============================================================
# SEARCH RESULT FALLBACK EVIDENCE
# ============================================================

def format_result_fallback_evidence(
    results
):

    if not results:

        return (
            "NO SEARCH RESULT EVIDENCE "
            "AVAILABLE."
        )

    formatted = []

    formatted.append(
        "SEARCH RESULT FALLBACK EVIDENCE\n"
    )

    results = rank_results(
        deduplicate_results(
            results
        )
    )

    for index, result in enumerate(
        results,
        start=1
    ):

        formatted.append(
            f"SOURCE {index}\n"
        )

        formatted.append(
            f"SEARCH SOURCE: "
            f"{result.get('search_source', 'Unknown')}\n"
        )

        formatted.append(
            f"TITLE: "
            f"{result.get('title', 'Unknown')}\n"
        )

        formatted.append(
            f"DOMAIN: "
            f"{result.get('domain', 'Unknown')}\n"
        )

        formatted.append(
            f"URL: "
            f"{result.get('url', 'Unknown')}\n"
        )

        description = result.get(
            "description",
            ""
        )

        if description:

            formatted.append(
                f"DESCRIPTION: "
                f"{description}\n"
            )

        snippets = result.get(
            "snippets",
            []
        )

        if isinstance(
            snippets,
            list
        ):

            for snippet in snippets[:3]:

                formatted.append(
                    f"EVIDENCE: "
                    f"{snippet}\n"
                )

        formatted.append(
            "\n------------------------------\n"
        )

    return "\n".join(
        formatted
    )


# ============================================================
# FINAL WEBPAGE EVIDENCE
# ============================================================

def format_webpage_evidence(
    pages
):

    if not pages:

        return (
            "NO WEBPAGE CONTENT WAS "
            "SUCCESSFULLY EXTRACTED."
        )

    formatted = []

    formatted.append(
        "FULL WEBPAGE EVIDENCE\n"
    )

    for index, page in enumerate(
        pages,
        start=1
    ):

        formatted.append(
            f"SOURCE {index}\n"
        )

        formatted.append(
            f"SEARCH SOURCE: "
            f"{page.get('search_source', 'Unknown')}\n"
        )

        formatted.append(
            f"TITLE: "
            f"{page.get('title', 'Unknown')}\n"
        )

        formatted.append(
            f"DOMAIN: "
            f"{page.get('domain', 'Unknown')}\n"
        )

        formatted.append(
            f"URL: "
            f"{page.get('url', 'Unknown')}\n"
        )

        formatted.append(
            "PAGE CONTENT:\n"
        )

        formatted.append(
            page.get(
                "content",
                ""
            )
        )

        formatted.append(
            "\n==============================\n"
        )

    return "\n".join(
        formatted
    )


# ============================================================
# COMPLETE SEARCH + PAGE RETRIEVAL
# ============================================================

def search_and_fetch(
    query,
    count=8,
    max_pages=5,
    max_characters_per_page=14000
):

    print(
        f"\n[RETRIEVAL] Searching: {query}"
    )

    search_data = web_search(
        query,
        count=count
    )

    results = get_all_web_results(
        search_data
    )

    results = rank_results(
        deduplicate_results(
            results
        )
    )

    if not results:

        print(
            "[RETRIEVAL] No search results."
        )

        return {
            "results": [],
            "pages": [],
            "search_source": search_data.get(
                "search_source",
                "NONE"
            )
        }

    print(
        f"[RETRIEVAL] Found "
        f"{len(results)} search results."
    )

    # --------------------------------------------------------
    # First attempt: trusted pages
    # --------------------------------------------------------

    pages = fetch_trusted_pages(
        results,
        max_pages=max_pages,
        max_characters_per_page=max_characters_per_page
    )

    # --------------------------------------------------------
    # Second attempt: any readable pages
    # --------------------------------------------------------

    if not pages:

        print(
            "[RETRIEVAL] Trusted pages unavailable."
        )

        pages = fetch_search_result_pages(
            results,
            max_pages=max_pages,
            max_characters_per_page=max_characters_per_page
        )

    print(
        f"[RETRIEVAL] Successfully opened "
        f"{len(pages)} pages."
    )

    return {
        "results": results,
        "pages": pages,
        "search_source": search_data.get(
            "search_source",
            "UNKNOWN"
        )
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "============================================"
    )

    print(
        " Nexus Web Retrieval Test"
    )

    print(
        "============================================\n"
    )

    query = (
        "Samsung Galaxy S25 Ultra "
        "display camera processor battery "
        "specifications"
    )

    print(
        f"[TEST QUERY]\n{query}\n"
    )

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    result = web_search(
        query,
        count=8
    )

    print(
        "\n\n"
    )

    print(
        format_search_results(
            result
        )
    )

    # --------------------------------------------------------
    # Extract results
    # --------------------------------------------------------

    results = get_all_web_results(
        result
    )

    # --------------------------------------------------------
    # Open actual pages
    # --------------------------------------------------------

    print(
        "\n\n"
        "============================================"
    )

    print(
        " Opening actual webpages..."
    )

    print(
        "============================================\n"
    )

    pages = fetch_search_result_pages(
        results,
        max_pages=5,
        max_characters_per_page=14000
    )

    print(
        "\n\n"
    )

    print(
        format_webpage_evidence(
            pages
        )
    )