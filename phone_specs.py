
"""
Nexus smartphone specification pipeline (page-first).
 
Flow:
    exact product name
      -> find the exact 91mobiles page (variant-safe URL validation)
      -> download the FULL page and turn it into labelled rows
         (section, label, value)
      -> parse Display / Processor / Camera / Battery from those rows
         (each value is read from the row that owns it)
      -> do the same for GSMArena (fallback + cross-check)
      -> merge, report conflicts, format
 
No LLM is used anywhere in this file. It works with Ollama switched off.
 
Optional: set NEXUS_DEBUG=1 to save every downloaded page and its parsed
rows into C:\\Nexus\\debug so a parser can be tuned against real pages.
"""
 
import os
import re
import sys
import time
from urllib.parse import urlparse, urljoin, unquote
 
try:
    import requests
except ImportError:  # pragma: no cover
    requests = None
 
try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None
 
 
PRIMARY_DOMAIN = "91mobiles.com"
SECONDARY_DOMAIN = "gsmarena.com"
SOURCE_NAMES = {PRIMARY_DOMAIN: "91mobiles", SECONDARY_DOMAIN: "GSMArena"}
 
DEBUG = os.environ.get("NEXUS_DEBUG", "") == "1"
DEBUG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug")
 
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
 
 
# ============================================================
# SMALL HELPERS
# ============================================================
 
def clean(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()
 
 
def domain_of(url):
    try:
        return urlparse(str(url or "")).netloc.lower().removeprefix("www.")
    except Exception:
        return ""
 
 
def _norm_url(url):
    return clean(url).split("#")[0].split("?")[0]
 
 
def _num(value):
    m = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(m.group(0)) if m else None
 
 
def _web_search(query, count=10):
    from you_search_tool import web_search  # lazy: keeps this file testable
    return web_search(query, count=count)
 
 
def _results(search_result):
    if not isinstance(search_result, dict):
        return []
    results = search_result.get("results", {})
    if not isinstance(results, dict):
        return []
    return (results.get("web", []) or []) + (results.get("news", []) or [])
 
 
def result_text(result):
    parts = []
    for field in ("title", "description", "content", "text", "body", "raw_content"):
        value = result.get(field, "")
        if isinstance(value, str) and value.strip():
            parts.append(clean(value))
    snippets = result.get("snippets", [])
    if isinstance(snippets, list):
        for item in snippets:
            if isinstance(item, str):
                parts.append(clean(item))
            elif isinstance(item, dict):
                parts.append(clean(item.get("text") or item.get("snippet") or item.get("content") or ""))
    return clean(" ".join(parts))
 
 
# ============================================================
# EXACT-MODEL VALIDATION (variant safety)
# ============================================================
 
BRAND_WORDS = {
    "apple", "samsung", "google", "oneplus", "xiaomi", "vivo", "oppo",
    "realme", "motorola", "nothing", "iqoo", "honor", "asus", "sony",
    "tecno", "infinix", "huawei", "poco", "nokia", "lava", "itel", "moto",
}
NOISE_WORDS = {
    "price", "in", "india", "specs", "spec", "specifications", "specification",
    "full", "phone", "phones", "review", "reviews", "php", "html", "mobile",
    "mobiles", "features", "and", "the",
}
 
 
def model_tokens(text):
    """'vivo-t4-5g' -> ['t','4'];  'Apple iPhone 17e' -> ['iphone','17','e']."""
    text = clean(text).lower().replace("+", " plus ")
    tokens = []
    for word in re.split(r"[^a-z0-9]+", text):
        if not word or word in NOISE_WORDS or word in BRAND_WORDS:
            continue
        if word in {"4g", "5g"} or re.fullmatch(r"\d+(?:gb|tb)", word):
            continue
        tokens.extend(re.findall(r"[a-z]+|\d+", word))
    return tokens
 
 
def is_exact_page(url, product):
    """True only for the spec page of exactly this model (not Pro/Plus/e/R...)."""
    domain = domain_of(url)
    segment = unquote(urlparse(str(url)).path.rstrip("/").split("/")[-1]).lower()
 
    if domain == PRIMARY_DOMAIN:
        m = re.fullmatch(r"(.+?)-price-in-india", segment)
    elif domain == SECONDARY_DOMAIN:
        # spec page only: apple_iphone_17-14050.php  (not -reviews-, -pictures-)
        m = re.fullmatch(r"([a-z0-9_+]+?)(?:_\((?:global|india)\))?-(\d{3,6})\.php", segment)
    else:
        return False
 
    if not m:
        return False
    wanted = model_tokens(product)
    return bool(wanted) and model_tokens(m.group(1)) == wanted
 
 
# ============================================================
# PAGE RETRIEVAL
# ============================================================
 
def find_product_pages(product, domain):
    label = SOURCE_NAMES[domain]
    queries = [f"{product} full specifications site:{domain}", f"{product} {label}"]
    pages = {}
 
    for query in queries:
        print(f"[SEARCH] {query}")
        try:
            found = _results(_web_search(query, 10))
        except Exception as error:
            print(f"[SEARCH] error: {error}")
            continue
        for item in found:
            url = _norm_url(item.get("url", ""))
            if url and domain_of(url) == domain and is_exact_page(url, product):
                pages.setdefault(url, []).append(result_text(item))
        print(f"[SEARCH] {len(found)} results, {len(pages)} exact {label} page(s)")
        if pages:
            break
 
    out = [{"url": u, "snippet": " ".join(t)} for u, t in pages.items()]
    out.sort(key=lambda x: 0 if re.search(r"\((?:global|india)\)|%28(?:global|india)%29", x["url"], re.I) else 1)
 
    if not out and domain == PRIMARY_DOMAIN:
        slug = re.sub(r"[^a-z0-9]+", "-", product.lower()).strip("-")
        for candidate in (slug, slug + "-5g"):
            out.append({"url": f"https://www.91mobiles.com/{candidate}-price-in-india", "snippet": ""})
        print("[SEARCH] no search hit; trying direct 91mobiles URL guess")
 
    return out[:2]
 
 
def fetch_page(url, retries=1):
    if requests is None:
        print("[FETCH] 'requests' is not installed:  pip install requests beautifulsoup4")
        return ""
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
        except Exception as error:
            print(f"[FETCH] {url} failed: {error}")
            return ""
        if response.status_code == 200:
            html = response.content.decode("utf-8", errors="replace")
            head = html[:4000].lower()
            if "just a moment" in head or "attention required" in head or "cf-chl" in head:
                print(f"[FETCH] {url} -> blocked by bot protection")
                return ""
            print(f"[FETCH] {url} -> OK ({len(html)//1024} KB)")
            return html
        print(f"[FETCH] {url} -> HTTP {response.status_code}")
        if response.status_code == 429 and attempt < retries:
            time.sleep(3)
            continue
        return ""
    return ""
 
 
# ============================================================
# PAGE -> LABELLED ROWS
# ============================================================
 
def classify_section(section):
    s = clean(section).lower()
    if not s:
        return ""
    if re.search(r"selfie|front", s):
        return "front"
    if "camera" in s:
        return "rear"
    if re.search(r"display|screen", s):
        return "display"
    if re.search(r"platform|performance|processor|chipset|hardware", s):
        return "platform"
    if "battery" in s:
        return "battery"
    return "other"
 
 
def _make_row(section, label, value):
    section = clean(section).lower()
    return {
        "section": section,
        "pillar": classify_section(section),
        "label": clean(label).lower().rstrip(":"),
        "value": value,
    }
 
 
def _cell_text(cell):
    """Cell text. A table nested inside the cell becomes ONE LINE PER DATA ROW
    ('Primary, 50 MP, Wide Angle, f/1.8, ...') so a lens keeps its own numbers."""
    outer = cell.find_parent("table")
    lines = []
    nested = [t for t in cell.find_all("table") if t.find_parent("table") is outer]
    for t in nested:
        for tr in t.find_all("tr"):
            if tr.find_parent("table") is not t:
                continue
            cells = tr.find_all(["th", "td"], recursive=False)
            texts = [clean(c.get_text(" ")) for c in cells]
            texts = [x for x in texts if x]
            if not texts or all(c.name == "th" for c in cells):
                continue
            lines.append(", ".join(texts))
        t.decompose()
    for br in cell.find_all("br"):
        br.replace_with("\n")
    rest = [clean(x) for x in cell.get_text("").split("\n")]
    return "\n".join(lines + [x for x in rest if x])
 
 
def rows_from_html(html):
    """Read every 2-column row of every top-level table as (section, label, value)."""
    if BeautifulSoup is None:
        print("[PARSE] 'beautifulsoup4' is not installed:  pip install beautifulsoup4")
        return []
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
 
    rows = []
    for table in [t for t in soup.find_all("table") if t.find_parent("table") is None]:
        heading = table.find_previous(["h1", "h2", "h3", "h4", "h5"])
        section = clean(heading.get_text(" ")) if heading else ""
 
        for tr in table.find_all("tr"):
            if tr.find_parent("table") is not table:
                continue
            cells = tr.find_all(["th", "td"], recursive=False)
            ths = [c for c in cells if c.name == "th"]
            tds = [c for c in cells if c.name == "td"]
            th_text = clean(ths[0].get_text(" ")) if ths else ""
 
            if th_text and not tds:
                section = th_text
                continue
            if th_text and len(tds) >= 2:
                section = th_text
                label = clean(tds[0].get_text(" "))
                value = "\n".join(_cell_text(c) for c in tds[1:])
            elif th_text:
                label, value = th_text, _cell_text(tds[0])
            elif len(tds) >= 2:
                label = clean(tds[0].get_text(" "))
                value = "\n".join(_cell_text(c) for c in tds[1:])
            elif len(tds) == 1:
                text = clean(tds[0].get_text(" "))
                if text and len(text) < 45 and classify_section(text) not in ("", "other"):
                    section = text          # a section title rendered as a single cell
                continue
            else:
                continue
 
            value = "\n".join(x for x in value.split("\n") if x.strip())
            if not value:
                continue
            if not label and rows:          # GSMArena continuation line
                rows[-1]["value"] += "\n" + value
                continue
            rows.append(_make_row(section, label, value))
 
    return rows
 
 
def page_region(html):
    """'Oppo Reno15 (China) - Full phone specifications' -> 'china'; '' when no region."""
    m = re.search(r"<title>([^<]*)</title>", html or "", re.I)
    if not m:
        return ""
    r = re.search(r"\(([^)]+)\)\s*-\s*Full phone", m.group(1), re.I)
    return r.group(1).strip().lower() if r else ""
 
 
def find_regional_link(html, base_url, product):
    """On a GSMArena regional page (e.g. China) look for the global/India page of the same model."""
    for m in re.finditer(r"""href=["']([^"']*?(?:_\((?:global|india)\)|_%28(?:global|india)%29)-\d+\.php)["']""",
                         html or "", re.I):
        url = urljoin(base_url, m.group(1))
        if is_exact_page(url, product):
            return url
    return ""
 
 
BLOB_LABELS = [
    "Screen Size", "Display Size", "Display Type", "Refresh Rate",
    "Screen Resolution", "Chipset", "Processor", "Fabrication",
    "Battery Capacity", "Capacity", "Quick Charging", "Fast Charging",
    "Wired Charging", "Wireless Charging", "Reverse Charging",
]
 
 
def rows_from_blob(text):
    """Degraded mode: a flattened snippet such as 'Capacity | 5000 mAh Quick Charging | 45W'."""
    text = clean(text)
    if not text:
        return []
    pattern = re.compile(
        r"(?:^|\s)(" + "|".join(re.escape(x) for x in BLOB_LABELS) + r")\s*[|:]\s*",
        re.I,
    )
    hits = list(pattern.finditer(text))
    rows = []
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        value = clean(text[m.end():end])[:160]
        if value:
            rows.append(_make_row("", m.group(1), value))
    return rows
 
 
def _rows_for(rows, pillar):
    return [r for r in rows if r["pillar"] in (pillar, "")]
 
 
def _first_row(rows, label_pattern):
    for r in rows:
        if re.fullmatch(label_pattern, r["label"]):
            return r
    return None
 
 
# ============================================================
# DISPLAY
# ============================================================
 
TECH_RE = re.compile(
    r"(?:LTPO\s+)?(?:Super\s+Retina\s+XDR(?:\s+OLED)?|"
    r"Dynamic\s+(?:LTPO\s+)?AMOLED(?:\s+2X)?|Fluid\s+AMOLED|Super\s+AMOLED|"
    r"Foldable\s+AMOLED|P-?OLED|AMOLED|OLED|IPS\s+LCD|TFT\s+LCD|LCD|Liquid\s+Retina)",
    re.I,
)
 
 
def _max_hz(text):
    text = re.sub(r"touch[\s\-]*sampl\w*[^,;\n]*", " ", text, flags=re.I)
    values = [int(x) for x in re.findall(r"(?<![\d.])(\d{2,3})\s*Hz", text, re.I)]
    values = [v for v in values if 48 <= v <= 240]
    return max(values) if values else None
 
 
def _brightness(text):
    """Return (peak, typical, unspecified) using the words next to each number."""
    peak, typ, other = [], [], []
    for m in re.finditer(r"(?<![\d.,])(\d{3,5})\s*(?:nits?\b|cd/m)", text, re.I):
        value = int(m.group(1))
        if not 200 <= value <= 10000:
            continue
        before = re.split(r"[,;\n]", text[:m.start()])[-1]
        after = re.split(r"[,;\n]", text[m.end():], 1)[0]
        ctx = (before + " " + after).lower()
        if re.search(r"peak|hbm|high brightness|\bmax|outdoor|sunlight", ctx):
            peak.append(value)
        elif re.search(r"typ|normal|standard|manual", ctx):
            typ.append(value)
        else:
            other.append(value)
    return (max(peak) if peak else None, max(typ) if typ else None, max(other) if other else None)
 
 
def extract_display(rows):
    d = _rows_for(rows, "display")
    if not d:
        return {}
    out = {}
    all_text = "\n".join(f'{r["label"]}: {r["value"]}' for r in d)
 
    # technology
    tech = ""
    type_row = _first_row(d, r"(?:display |screen |panel )?(?:type|technology)|panel")
    if type_row:
        first = re.split(r"[,;\n]", type_row["value"])[0]
        m = TECH_RE.search(first) or TECH_RE.search(type_row["value"])
        tech = m.group(0) if m else ""
    if not tech:
        for r in d:
            if re.search(r"protect|glass", r["label"]):
                continue
            m = TECH_RE.search(r["value"])
            if m:
                tech = m.group(0)
                break
    out["display_type"] = clean(tech)
 
    # size
    size_row = _first_row(d, r"(?:screen |display )?size|diagonal|screen size")
    pools = ([size_row["value"]] if size_row else []) + [r["value"] for r in d]
    for text in pools:
        m = re.search(r'(?<![\d.])(\d{1,2}(?:\.\d{1,3})?)\s*(?:inches|inch|")', text, re.I)
        if m:
            size = f"{float(m.group(1)):.2f}".rstrip("0").rstrip(".")
            out["display_size"] = f"{size} inches"
            break
 
    # resolution
    res_row = _first_row(d, r"(?:screen |display )?resolution")
    pools = ([res_row["value"]] if res_row else []) + [r["value"] for r in d]
    for text in pools:
        m = re.search(r"(\d{3,5})\s*[x×X]\s*(\d{3,5})", text)
        if m:
            a, b = sorted((int(m.group(1)), int(m.group(2))))
            out["display_resolution"] = f"{a} × {b}"
            break
 
    # refresh rate
    hz = None
    rr = _first_row(d, r"(?:screen )?refresh rate")
    if rr:
        hz = _max_hz(rr["value"])
    if hz is None and type_row:
        hz = _max_hz(type_row["value"])
    if hz is None:
        hz = _max_hz(all_text)
    if hz:
        out["refresh_rate"] = f"{hz} Hz"
 
    # brightness
    peak, typ, other = _brightness(all_text)
    if peak:
        out["peak_brightness"] = f"{peak} nits"
    if typ:
        out["typical_brightness"] = f"{typ} nits"
    if other and not peak and not typ:
        out["brightness"] = f"{other} nits"
 
    # HDR
    values_text = "\n".join(r["value"] for r in d)      # values only: a LABEL like 'HDR 10 / HDR+ Support' is not evidence
    hdr = [name for name, pat in (
        ("HDR10+", r"HDR\s?10\s?\+"), ("Dolby Vision", r"Dolby\s+Vision"),
        ("HDR10", r"HDR\s?10(?!\s?\+)(?!\d)"), ("HLG", r"\bHLG\b"),
    ) if re.search(pat, values_text, re.I)]
    if hdr:
        out["hdr"] = ", ".join(hdr)
    elif re.search(r"\bHDR\b", values_text):
        out["hdr"] = "HDR"
 
    # touch sampling
    m = (re.search(r"touch[\s\-]*sampl\w*\s*(?:rate)?\s*[:|]?\s*(?:up to\s*)?(\d{2,4})\s*Hz", all_text, re.I)
         or re.search(r"(\d{2,4})\s*Hz\s*touch[\s\-]*sampl", all_text, re.I))
    if m:
        out["touch_sampling"] = f"{m.group(1)} Hz"
 
    for r in d:
        if re.search(r"protect|glass|scratch", r["label"]):
            first = clean(r["value"].split("\n")[0])
            if len(first) > 3 and first.lower() not in {"yes", "no", "none", "na", "n/a"}:
                out["protection"] = first[:80]
                break
 
    return {k: v for k, v in out.items() if v}
 
 
# ============================================================
# PROCESSOR
# ============================================================
 
_CHIP_WORDS = {"elite", "plus", "pro", "ultra", "max", "extreme", "leading", "lite", "energy", "gen"}
 
 
def chip_name(text):
    """Clean chipset name: 'Qualcomm SM8850-AC Snapdragon 8 Elite Gen 5 (3 nm)' -> 'Snapdragon 8 Elite Gen 5'."""
    text = clean(text)
    m = re.search(r"\bApple\s+(A\d{1,2}(?:\s+(?:Pro|Bionic))?)\b", text)
    if m:
        return "Apple " + m.group(1)
 
    m = re.search(r"\b(Snapdragon|Dimensity|Helio|Exynos|Tensor|Kirin|Unisoc)\s+(.*)", text, re.I)
    if not m:
        return ""
    family = m.group(1)
    kept = []
    prev = ""
    for i, word in enumerate(m.group(2).split()[:6]):
        if word.startswith("("):
            break
        token = word.strip(",;")
        low = token.lower()
        if i == 0:
            if not re.fullmatch(r"[a-z]{0,2}\d{1,5}[a-z+]{0,3}", low):
                break
        elif low in _CHIP_WORDS:
            pass
        elif prev == "gen" and re.fullmatch(r"\d+", low):
            pass
        else:
            break
        kept.append(token)
        prev = low
        if word.endswith((",", ";")):
            break
    if not kept:
        return ""
    name = family + " " + " ".join(kept)
    if family.lower() == "tensor" and re.search(r"google\s+tensor", text, re.I):
        name = "Google " + name
    return name
 
 
def _ghz_max(text):
    v = [float(x) for x in re.findall(r"(\d(?:\.\d+)?)\s*GHz", text, re.I)]
    return max(v) if v else None
 
 
_CORE_WORDS = {"single": 1, "dual": 2, "quad": 4, "penta": 5, "hexa": 6, "octa": 8, "nona": 9, "deca": 10}
 
 
def extract_processor(rows):
    p = _rows_for(rows, "platform")
    if not p:
        return {}
    out = {}
 
    chip_rows = [r for r in p if re.fullmatch(
        r"chipset|processor|soc|chipset name|processor name|platform|cpu name", r["label"])]
    node_text = ""
    for r in chip_rows + p:
        name = chip_name(r["value"])
        if name:
            out["chipset"] = name
            node_text = r["value"]
            break
 
    m = re.search(r"(?<![\d.])(\d{1,2})\s*nm\b", node_text, re.I)
    if not m:
        fab = _first_row(p, r"fabrication|process|process node|manufacturing process|technology node")
        m = re.search(r"(?<![\d.])(\d{1,2})\s*nm\b", fab["value"], re.I) if fab else None
    if m:
        out["process_node"] = f"{m.group(1)} nm"
 
    cpu_row = _first_row(p, r"cpu|cpu configuration|cpu cores|processor cores?|number of cores|no\.? of cores|cores")
    cpu_text = " ".join(
        r["value"] for r in p
        if re.fullmatch(r"cpu|cpu configuration|cpu cores|cores|number of cores|no\.? of cores|"
                        r"clock speed|cpu clock|processor speed|frequency|processor", r["label"])
    )
    if cpu_row is None:
        pr = _first_row(p, r"processor")
        if pr and re.search(r"core|ghz", pr["value"], re.I):
            cpu_row = pr
    if cpu_row:
        out["cpu"] = clean(cpu_row["value"].split("\n")[0])[:170]
    m = re.search(r"\b(single|dual|quad|penta|hexa|octa|nona|deca)[\s\-]?core", cpu_text, re.I)
    if m:
        out["cpu_cores"] = m.group(1).capitalize() + "-core"
    else:
        m = re.search(r"\b(\d+)[\s\-]?cores?\b", cpu_text, re.I)
        if m:
            out["cpu_cores"] = f"{m.group(1)}-core"
    ghz = _ghz_max(out.get("cpu", "")) or _ghz_max(cpu_text)
    if ghz:
        out["cpu_clock"] = f"{ghz:g} GHz (max)"
 
    gpu = _first_row(p, r"gpu|graphics|graphics processor|gpu name")
    if gpu:
        out["gpu"] = clean(gpu["value"].split("\n")[0])[:80]
 
    return out
 
 
# ============================================================
# CAMERA
# ============================================================
 
_MP_RE = re.compile(r"(?<![\d./])(\d{1,3}(?:\.\d+)?)\s*(?:MP|megapixels?)\b", re.I)
_LENS_COUNT = {"single": 1, "dual": 2, "triple": 3, "quad": 4, "penta": 5}
_SKIP_LABELS = r".*(?:video|feature|flash|setting|mode|hdr|zoom|stabili|aperture|pixel|focal).*"
 
 
def _role(text):
    t = text.lower()
    if re.search(r"ultra[\s\-]?wide|\buw\b", t):
        return "ultrawide"
    if re.search(r"periscope|\btele(?:photo)?\b", t):
        return "telephoto"
    if re.search(r"\bmacro\b", t):
        return "macro"
    if re.search(r"\bdepth\b|bokeh", t):
        return "depth"
    if re.search(r"monochrome|\bmono\b", t):
        return "mono"
    if re.search(r"\bwide\b|\bprimary\b|\bmain\b|\bstandard\b", t):
        return "main"
    return "unknown"
 
 
def _lens_chunks(rows):
    chunks = []
    for r in rows:
        is_count = r["label"] in _LENS_COUNT
        if not is_count and re.fullmatch(_SKIP_LABELS, r["label"]):
            continue
        prefix = "" if is_count else r["label"]
        for line in r["value"].split("\n"):
            chunks.append(clean(f"{prefix} {line}"))
    return chunks
 
 
def _parse_lenses(chunks):
    lenses = []
    for chunk in chunks:
        hits = list(_MP_RE.finditer(chunk))
        if not hits:
            continue
        fragments = [chunk] if len(hits) == 1 else re.split(r"\s\+\s|;|\|", chunk)
        for fragment in fragments:
            fh = list(_MP_RE.finditer(fragment))
            if len(fh) != 1:
                continue  # cannot tell which number belongs to which lens: skip, never guess
            lenses.append({"mp": float(fh[0].group(1)), "role": _role(fragment), "text": fragment})
    return lenses
 
 
def _mp(value):
    return f"{value:g} MP"
 
 
_VIDEO_RANK = {"8K": 4, "4K": 3, "1440p": 2, "1080p": 1, "720p": 0}
 
 
def parse_video(text):
    """Headline (normal) video modes only; slow-motion only when explicitly labelled."""
    best = {}
    for m in re.finditer(
        r"\b(8K|4K|2160p|1440p|1080p|720p)\s*(?:UHD\s*)?(?:@|at)?\s*((?:\d{2,3}\s*/\s*)*\d{2,3})\s*fps",
        text, re.I,
    ):
        g = m.group(1)
        res = "4K" if g.lower() == "2160p" else (g.upper() if g.lower().endswith("k") else g.lower())
        fps = max(int(x) for x in re.findall(r"\d+", m.group(2)))
        best[res] = max(best.get(res, 0), fps)
    out = {}
    if best:
        ordered = sorted(best, key=lambda r: -_VIDEO_RANK.get(r, -1))
        chosen = [r for r in ordered if _VIDEO_RANK.get(r, 0) >= 3] or ordered[:1]
        out["video"] = "; ".join(f"{r} up to {best[r]} fps" for r in chosen)
    m = (re.search(r"slow[\s\-]?mo(?:tion)?[^.\n;]{0,40}?(\d{3,4})\s*fps", text, re.I)
         or re.search(r"(\d{3,4})\s*fps[^.\n;]{0,15}slow[\s\-]?mo", text, re.I))
    if m:
        out["slow_motion"] = f"up to {m.group(1)} fps"
    return out
 
 
def extract_camera(rows):
    rear_all = _rows_for(rows, "rear")
    front_by_label = [r for r in rear_all if re.search(r"front|selfie", r["label"])]
    rear = [r for r in rear_all if r not in front_by_label]
    front = _rows_for(rows, "front") + front_by_label
    out = {}
 
    lenses = _parse_lenses(_lens_chunks(rear))
    main = next((l for l in lenses if l["role"] == "main"), None)
    if main is None and lenses and lenses[0]["role"] == "unknown":
        main = lenses[0]
    if main and main["mp"] < 5:      # a "main camera" under 5 MP is a mis-read, not a phone
        main = None
 
    if main:
        out["cam_main_mp"] = _mp(main["mp"])
        t = main["text"]
        m = re.search(r"\b(f/\d+(?:\.\d+)?)", t, re.I)
        if m:
            out["cam_main_aperture"] = m.group(1)
        m = re.search(r'(1/\d+(?:\.\d+)?)\s*(?:"|″|inch)', t)
        if m:
            out["cam_main_sensor"] = m.group(1) + '"'
        m = re.search(r"\b(?:Sony\s+)?(IMX\d{3}\w*)|ISOCELL\s+[A-Z0-9]+|LYT[-\s]?\d+\w*", t, re.I)
        if m:
            out["cam_main_sensor_name"] = clean(m.group(0))
        if re.search(r"\bOIS\b|optical image stabili[sz]ation|sensor-shift", t, re.I):
            out["cam_main_ois"] = "Yes"
 
    if "cam_main_ois" not in out:       # 91mobiles lists OIS as its own row for the phone
        ois = _first_row(rear, r"ois|optical image stabili[sz]ation")
        if ois and re.match(r"\s*yes", ois["value"], re.I):
            out["cam_ois"] = "Yes"
 
    for role, key in (("ultrawide", "cam_ultrawide"), ("telephoto", "cam_telephoto")):
        found = [_mp(l["mp"]) for l in lenses if l["role"] == role]
        if found:
            out[key] = " + ".join(found)
 
    count = None
    for r in rear:
        if r["label"] in _LENS_COUNT:
            count = _LENS_COUNT[r["label"]]
            break
    if count is None:
        m = re.search(r"\b(single|dual|triple|quad|penta)\s+(?:rear\s+|back\s+)?camera",
                      " ".join(r["label"] + " " + r["value"] for r in rear), re.I)
        if m:
            count = _LENS_COUNT[m.group(1).lower()]
    ordinal = re.compile(r"(?:^|\s)(?:primary|secondary|tertiary|quaternary)\s*,", re.I)
    structured = bool(lenses) and all(ordinal.search(l["text"]) for l in lenses)   # 91mobiles lens table
    out["lens_complete"] = bool(main and ((count is not None and count == len(lenses)) or structured))
 
    # front camera: ONLY from front rows, never from the rear list
    front_lenses = _parse_lenses(_lens_chunks(front))
    if front_lenses:
        out["cam_front"] = _mp(front_lenses[0]["mp"])
 
    # video (rear)
    video_text = " ".join(r["value"] for r in rear if "video" in r["label"])
    if not video_text:
        video_text = " ".join(r["value"] for r in rear if "fps" in r["value"].lower())
    out.update(parse_video(video_text))
 
    return {k: v for k, v in out.items() if v or k == "lens_complete"}
 
 
# ============================================================
# BATTERY & CHARGING
# ============================================================
 
def classify_watts(text, default="wired"):
    """Assign every 'NNW' to wired / wireless / reverse using the words beside it.
 
    default=None (used for a generic 'Charging' row): a number with no
    wired/wireless/reverse word next to it is only accepted as wired when it is
    the very first value on the first line; otherwise it is ignored, not guessed.
    """
    out = {"wired": [], "wireless": [], "reverse": []}
    matches = list(re.finditer(r"(?<![\d.])(\d{1,3}(?:\.\d+)?)\s*W\b(?!h)", text))
    for i, m in enumerate(matches):
        prev_end = matches[i - 1].end() if i else 0
        next_start = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        after = re.split(r"[,;\n(]", text[m.end():next_start], 1)[0]
        before = re.split(r"[,;\n]", text[prev_end:m.start()])[-1]
        kind = default
        qualified = False
        for window in (after, before):
            w = window.lower()
            if "reverse" in w:
                kind, qualified = "reverse", True
                break
            if re.search(r"wireless|magsafe|\bqi2?(?:\.\d)?\b", w):
                kind, qualified = "wireless", True
                break
            if "wired" in w:
                kind, qualified = "wired", True
                break
        if kind is None:
            if i == 0 and "\n" not in text[:m.start()]:
                kind = "wired"
            else:
                continue
        watts = float(m.group(1))
        if 3 <= watts <= 300:
            out[kind].append(watts)
    return out
 
 
def extract_battery(rows):
    b = _rows_for(rows, "battery")
    if not b:
        return {}
    out = {}
 
    cap_rows = [r for r in b if re.fullmatch(r"capacity|battery capacity|type|battery type|battery", r["label"])] + b
    for r in cap_rows:
        m = re.search(r"(?<![\d.])(\d{4,5})\s*mAh", r["value"], re.I)
        if m and 1000 <= int(m.group(1)) <= 20000:
            out["battery_mah"] = f"{m.group(1)} mAh"
            break
 
    buckets = {"wired": [], "wireless": [], "reverse": []}
    flags = {}
    for r in b:
        label = r["label"]
        if not re.search(r"charg", label):
            continue
        if "reverse" in label:
            default = "reverse"
        elif "wireless" in label:
            default = "wireless"
        elif re.fullmatch(r"(?:battery )?charging(?: speed)?", label):
            default = None            # generic row: do not guess
        else:
            default = "wired"
        for kind, values in classify_watts(r["value"], default).items():
            buckets[kind].extend(values)
        if default in ("reverse", "wireless"):
            m = re.match(r"\s*(yes|no|supported|not supported)\b", r["value"], re.I)
            if m:
                flags[default] = "Yes" if m.group(1).lower() in {"yes", "supported"} else "No"
 
    for kind, key in (("wired", "wired_charging"), ("wireless", "wireless_charging"), ("reverse", "reverse_charging")):
        if buckets[kind]:
            out[key] = f"{max(buckets[kind]):g}W"
        elif kind in flags:
            out[key] = flags[kind]
    return out
 
 
def extract_all(rows):
    spec = {}
    for fn in (extract_display, extract_processor, extract_camera, extract_battery):
        spec.update(fn(rows))
    return spec
 
 
# ============================================================
# SOURCES, MERGE, CONFLICTS
# ============================================================
 
def _debug_dump(domain, url, html, rows):
    if not DEBUG:
        return
    os.makedirs(DEBUG_DIR, exist_ok=True)
    stem = SOURCE_NAMES.get(domain, domain)
    with open(os.path.join(DEBUG_DIR, f"{stem}.html"), "w", encoding="utf-8") as f:
        f.write(html or "")
    with open(os.path.join(DEBUG_DIR, f"{stem}_rows.txt"), "w", encoding="utf-8") as f:
        f.write(url + "\n\n")
        for r in rows:
            f.write(f'[{r["section"]}|{r["pillar"]}] {r["label"]} => {r["value"]!r}\n')
    print(f"[DEBUG] saved {stem}.html and {stem}_rows.txt in {DEBUG_DIR}")
 
 
def load_source(product, domain):
    for page in find_product_pages(product, domain):
        url = page["url"]
        html = fetch_page(url)
        region = page_region(html) if html else ""
        if html and domain == SECONDARY_DOMAIN and region not in ("", "global", "india"):
            better = find_regional_link(html, url, product)
            if better:
                print(f"[SOURCE] GSMArena page is the '{region}' variant; using the global/India page instead")
                better_html = fetch_page(better)
                if better_html:
                    html, url = better_html, better
                    region = page_region(html)
        rows = rows_from_html(html) if html else []
        kind = "full page"
        if len(rows) < 8:
            snippet_rows = rows_from_blob(page.get("snippet", ""))
            if snippet_rows:
                rows = rows + snippet_rows
                kind = "search snippet only" if not html else "page + snippet"
        _debug_dump(domain, url, html, rows)
        if not rows:
            continue
        spec = extract_all(rows)
        if not any(k in spec for k in ("display_type", "chipset", "cam_main_mp", "battery_mah")):
            print(f"[PARSE] {SOURCE_NAMES[domain]}: {len(rows)} rows but no recognisable specs")
            continue
        print(f"[PARSE] {SOURCE_NAMES[domain]}: {len(rows)} rows ({kind})")
        return {"domain": domain, "name": SOURCE_NAMES[domain], "url": url, "kind": kind,
                "spec": spec, "region": region}
    return None
 
 
def variant_mismatch(primary, other):
    """True when two pages clearly describe different variants (different chipset or screen/battery size)."""
    a, b = primary["spec"], other["spec"]
    reasons = []
    if a.get("chipset") and b.get("chipset") and not _same("text", a["chipset"], b["chipset"]):
        reasons.append(f"chipset {b['chipset']}")
    x, y = _num(a.get("display_size")), _num(b.get("display_size"))
    if x and y and abs(x - y) > 0.12:
        reasons.append(f"screen {b['display_size']}")
    x, y = _num(a.get("battery_mah")), _num(b.get("battery_mah"))
    if x and y and abs(x - y) / max(x, y) > 0.10:
        reasons.append(f"battery {b['battery_mah']}")
    return reasons
 
 
LENS_KEYS = ["cam_main_mp", "cam_main_aperture", "cam_main_sensor", "cam_main_sensor_name",
             "cam_main_ois", "cam_ois", "cam_ultrawide", "cam_telephoto"]
ALL_KEYS = [
    "display_type", "display_size", "display_resolution", "refresh_rate", "peak_brightness",
    "typical_brightness", "brightness", "hdr", "touch_sampling", "protection",
    "chipset", "process_node", "cpu", "cpu_cores", "cpu_clock", "gpu",
    "cam_front", "video", "slow_motion",
    "battery_mah", "wired_charging", "wireless_charging", "reverse_charging",
] + LENS_KEYS
 
CHECKS = [
    ("battery_mah", "Battery capacity", "num"),
    ("refresh_rate", "Refresh rate", "num"),
    ("display_size", "Screen size", "num"),
    ("cam_main_mp", "Main camera", "num"),
    ("wired_charging", "Wired charging", "num"),
    ("wireless_charging", "Wireless charging", "num"),
    ("cam_front", "Front camera", "num"),
    ("chipset", "Chipset", "text"),
]
 
 
def _same(kind, a, b):
    if kind == "num":
        x, y = _num(a), _num(b)
        return x is not None and y is not None and abs(x - y) < 0.06
    return re.sub(r"[^a-z0-9]", "", a.lower()) == re.sub(r"[^a-z0-9]", "", b.lower())
 
 
def merge_sources(sources):
    merged, conflicts, fallback = {}, [], set()
    first = sources[0]
 
    lens_src = next((s for s in sources if s["spec"].get("cam_main_mp")), None)
    lens_complete = bool(lens_src and lens_src["spec"].get("lens_complete"))
 
    for key in ALL_KEYS:
        if key in LENS_KEYS:                       # never mix lens roles across sources
            value = lens_src["spec"].get(key, "") if lens_src else ""
            if value:
                merged[key] = value
                if lens_src is not first:
                    fallback.add(lens_src["name"])
            continue
        for s in sources:
            value = s["spec"].get(key, "")
            if value:
                merged[key] = value
                if s is not first:
                    fallback.add(s["name"])
                break
 
    if merged.get("cpu"):
        ghz = _ghz_max(merged["cpu"])
        if ghz:
            merged["cpu_clock"] = f"{ghz:g} GHz (max)"
 
    for key, label, kind in CHECKS:
        values = [(s["name"], s["spec"][key]) for s in sources if s["spec"].get(key)]
        if len(values) >= 2 and not all(_same(kind, values[0][1], v) for _, v in values[1:]):
            conflicts.append((label, values))
 
    return merged, conflicts, fallback, lens_complete
 
 
# ============================================================
# FORMAT
# ============================================================
 
MANDATORY = [
    ("display_type", "Display type"), ("display_size", "Display size"),
    ("display_resolution", "Display resolution"), ("refresh_rate", "Refresh rate"),
    ("chipset", "Chipset"), ("cam_main_mp", "Main camera"),
    ("battery_mah", "Battery capacity"), ("wired_charging", "Wired charging"),
]
 
 
def format_answer(product, merged, conflicts, fallback, lens_complete, sources, ignored=()):
    lines = [f"**{product}**", ""]
 
    def add(label, key, missing_note=False):
        value = merged.get(key, "")
        if value:
            lines.append(f"• {label}: {value}")
        elif missing_note:
            lines.append(f"• {label}: not found on the retrieved pages")
 
    must = {k for k, _ in MANDATORY}
 
    lines.append("**Display**")
    for label, key in (("Type", "display_type"), ("Size", "display_size"),
                       ("Resolution", "display_resolution"), ("Refresh Rate", "refresh_rate"),
                       ("Peak Brightness", "peak_brightness"), ("Typical Brightness", "typical_brightness"),
                       ("Brightness", "brightness"), ("HDR", "hdr"),
                       ("Touch Sampling Rate", "touch_sampling"), ("Protection", "protection")):
        add(label, key, key in must)
 
    lines += ["", "**Processor**"]
    add("Chipset", "chipset", True)
    add("Process Node", "process_node")
    add("CPU", "cpu")
    if not merged.get("cpu"):
        add("CPU Cores", "cpu_cores")
    add("CPU Clock", "cpu_clock")
    add("GPU", "gpu")
 
    lines += ["", "**Camera**"]
    add("Main Camera", "cam_main_mp", True)
    add("Main Aperture", "cam_main_aperture")
    add("Main Sensor", "cam_main_sensor_name")
    add("Main Sensor Size", "cam_main_sensor")
    add("Main OIS", "cam_main_ois")
    if not merged.get("cam_main_ois"):
        add("OIS", "cam_ois")
    for label, key in (("Ultrawide", "cam_ultrawide"), ("Telephoto", "cam_telephoto")):
        if merged.get(key):
            lines.append(f"• {label}: {merged[key]}")
        elif lens_complete:
            lines.append(f"• {label}: Not present")
    add("Front Camera", "cam_front")
    add("Video", "video")
    add("Slow Motion", "slow_motion")
 
    lines += ["", "**Battery & Charging**"]
    add("Capacity", "battery_mah", True)
    add("Wired Charging", "wired_charging", True)
    add("Wireless Charging", "wireless_charging")
    add("Reverse Charging", "reverse_charging")
 
    if conflicts:
        lines += ["", "**Sources disagree**"]
        for label, values in conflicts:
            detail = " vs ".join(f"{n}: {v}" for n, v in values)
            lines.append(f"• {label} — {detail}")
        if any(label == "Battery capacity" for label, _ in conflicts):
            lines.append("  (Battery figures can differ as typical vs rated capacity or by region.)")
        lines.append("  The manufacturer's page is the tie-breaker; the first source listed is shown above.")
 
    if fallback:
        lines += ["", f"Some values were filled from {', '.join(sorted(fallback))} "
                      f"because the primary page did not list them."]
 
    for s in ignored:
        lines += ["", f"Note: the {s['name']} page found describes a different variant of this model "
                      f"({s['ignored']}), so it was not mixed in."]
    for s in sources:
        if s.get("region") not in ("", None, "global", "india"):
            lines += ["", f"Note: the only {s['name']} page found is the '{s['region']}' variant of this phone."]
 
    lines += ["", "**Sources**"]
    for s in sources:
        note = "" if s["kind"] in {"full page", "page + snippet"} else f" ({s['kind']})"
        lines.append(f"• {s['name']}: {s['url']}{note}")
    for s in ignored:
        lines.append(f"• {s['name']}: {s['url']} (different variant - not used)")
 
    return "\n".join(lines)
 
 
def build_spec_answer(product):
    print(f"\n[1/3] Locating exact product pages for: {product}")
    sources = []
    for domain in (PRIMARY_DOMAIN, SECONDARY_DOMAIN):
        source = load_source(product, domain)
        if source:
            sources.append(source)
        else:
            print(f"[SOURCE] no usable {SOURCE_NAMES[domain]} page")
 
    if not sources:
        return ("I could not retrieve an exact, readable product page for "
                f"{product} from 91mobiles or GSMArena. Try again in a moment, or run with "
                "NEXUS_DEBUG=1 to see what the pages returned.")
 
    print("[2/3] Parsing the four pillars from the product page rows...")
    ignored = []
    kept = [sources[0]]
    for other in sources[1:]:
        reasons = variant_mismatch(sources[0], other)
        if reasons:
            other["ignored"] = ", ".join(reasons)
            ignored.append(other)
            print(f"[SOURCE] {other['name']} describes a different variant ({other['ignored']}) - not mixed in")
        else:
            kept.append(other)
    merged, conflicts, fallback, lens_complete = merge_sources(kept)
    for key, label in MANDATORY:
        print(f"[LOCKED] {label}: {merged.get(key) or 'not found'}")
 
    print("[3/3] Building answer.")
    return format_answer(product, merged, conflicts, fallback, lens_complete, kept, ignored)
 
 
if __name__ == "__main__":
    query = " ".join(sys.argv[1:]).strip() or "OnePlus 15"
    print(build_spec_answer(query))
 
