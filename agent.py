import os
import re
import json
from datetime import datetime
from urllib.parse import urlparse

import ollama
 
from tools import search_knowledge
from you_search_tool import web_search
import phone_specs
 
 
MODEL = os.environ.get("NEXUS_MODEL", "qwen3.5:4b")
CPU_ONLY = os.environ.get("NEXUS_CPU_ONLY", "") == "1"
 
 
def llm_chat(**kwargs):
    """ollama.chat with a CUDA-crash workaround: on failure, retry once on CPU only."""
    options = dict(kwargs.get("options") or {})
    if CPU_ONLY:
        options["num_gpu"] = 0
    kwargs["options"] = options
    try:
        return ollama.chat(**kwargs)
    except Exception as first_error:
        if options.get("num_gpu") == 0:
            raise
        print("[LLM] failed (", str(first_error)[:80], ") - retrying on CPU only...")
        options["num_gpu"] = 0
        kwargs["options"] = options
        return ollama.chat(**kwargs)
 
 
# ============================================================
# TRUSTED SOURCE PRIORITY (used by product resolution and web answers)
# ============================================================
 
TRUSTED_SOURCE_PRIORITY = {
    "apple.com": 100, "samsung.com": 100, "google.com": 100, "oneplus.com": 100,
    "xiaomi.com": 100, "mi.com": 100, "oppo.com": 100, "vivo.com": 100,
    "realme.com": 100, "motorola.com": 100, "nothing.tech": 100, "iqoo.com": 100,
    "iqoo.in": 100, "honor.com": 100, "asus.com": 100, "sony.com": 100,
    "poco.net": 100, "tecno-mobile.com": 100, "infinixmobility.com": 100,
    "91mobiles.com": 100, "gsmarena.com": 95, "gadgets360.com": 70,
    "androidauthority.com": 70, "phonearena.com": 70, "theverge.com": 70,
    "techradar.com": 70, "digit.in": 65, "smartprix.com": 60,
    "flipkart.com": 60, "amazon.in": 60, "amazon.com": 60,
}
 
LOW_QUALITY_DOMAINS = {
    "youtube.com", "youtu.be", "wikipedia.org", "devicespecifications.com", "kimovil.com",
}
 
 
# ============================================================
# ROUTER KEYWORDS
# ============================================================
 
SPEC_KEYWORDS = [
    "specification", "specifications", "specs", "spec", "ram", "storage", "battery",
    "charging", "camera", "display", "screen", "processor", "chipset", "soc",
    "dimensions", "weight", "refresh rate", "resolution", "ppi", "brightness",
    "ip rating", "oled", "amoled", "ltpo", "5g",
]
 
CURRENT_KEYWORDS = [
    "latest", "current", "today", "newest", "recent", "recently", "news",
    "launched", "launch", "price", "pricing", "available", "availability", "upcoming",
]
 
GENERIC_WORDS = {
    "the", "a", "an", "phone", "smartphone", "mobile", "device", "spec", "specs",
    "specification", "specifications", "full", "features", "feature", "details",
    "review", "price", "pricing", "india", "indian", "launch", "launched", "release",
    "released", "available", "availability", "buy", "purchase", "camera", "display",
    "battery", "processor", "chipset", "ram", "storage", "charging", "screen",
    "latest", "current", "newest", "recent", "today",
}
 
 
# ============================================================
# BASIC HELPERS
# ============================================================
 
def clean_text(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return re.sub(r"\s+", " ", value).strip()
 
 
def get_domain(url):
    try:
        return urlparse(str(url or "")).netloc.lower().removeprefix("www.")
    except Exception:
        return ""
 
 
def source_priority(url):
    domain = get_domain(url)
    if domain in LOW_QUALITY_DOMAINS:
        return -1
    return TRUSTED_SOURCE_PRIORITY.get(domain, 0)
 
 
def get_search_results(search_result):
    if not isinstance(search_result, dict):
        return []
    results = search_result.get("results", {})
    if not isinstance(results, dict):
        return []
    return (results.get("web", []) or []) + (results.get("news", []) or [])
 
 
def get_result_text(result):
    return phone_specs.result_text(result)
 
 
# ============================================================
# ROUTER
# ============================================================
 
def is_latest_mobile_question(question):
    text = clean_text(question).lower()
    latest_words = ["latest", "newest", "current", "recent", "today"]
    mobile_words = ["mobile", "phone", "smartphone"]
    return any(w in text for w in latest_words) and any(w in text for w in mobile_words)
 
 
def route_question(question):
    text = clean_text(question).lower()
 
    if is_latest_mobile_question(question):
        return "techspecs"
 
    has_spec_word = any(re.search(rf"\b{re.escape(k)}\b", text) for k in SPEC_KEYWORDS)
    has_current_word = any(re.search(rf"\b{re.escape(k)}\b", text) for k in CURRENT_KEYWORDS)
    product = detect_product(question)
 
    # A named phone + a spec word (or just the bare model name) -> spec pipeline.
    if product and (has_spec_word or not has_current_word):
        return "techspecs"
 
    has_brand = any(re.search(rf"\b{b}\b", text) for b in _ROUTER_BRANDS)
    if has_brand and has_spec_word:
        return "techspecs"
 
    if has_current_word:
        return "web"
 
    return "rag"
 
 
# ============================================================
# DIRECT PRODUCT EXTRACTION (variant-safe canonical names)
# ============================================================
 
_APPLE_RE = re.compile(
    r"\b(?:apple\s+)?iphone\s*(?:(\d{1,2})(?:\s*(pro\s*max|pro|plus|mini|air|e)(?![a-z]))?|(air)(?![a-z]))",
    re.I,
)
_SAMSUNG_FOLD_RE = re.compile(
    r"\b(?:samsung\s+)?galaxy\s+z?\s*(fold|flip)\s*(\d{1,2})(?:\s*(fe))?(?![a-z0-9])", re.I)
_SAMSUNG_LETTER_RE = re.compile(
    r"(?<![a-z0-9])(?:(?:samsung\s+)?galaxy\s+)?([sazmf])\s?(\d{2,3})(?:\s?(fe|ultra|plus|edge)|(\+))?(?![a-z0-9])",
    re.I,
)
_PIXEL_RE = re.compile(
    r"\b(?:google\s+)?pixel\s*(\d{1,2})(?:\s*(pro\s*xl|pro\s*fold|pro|xl|fold|a)(?![a-z]))?", re.I)
_ONEPLUS_RE = re.compile(
    r"\boneplus\s*(\d{1,2})\s?(pro|r|t|s)?(?![a-z0-9])", re.I)
_ONEPLUS_NORD_RE = re.compile(
    r"\boneplus\s+nord(?:\s+(?:ce|n))?\s*\d{0,2}(?:\s+lite)?(?![a-z0-9])", re.I)
_VIVO_RE = re.compile(
    r"\bvivo\s*([tvxyus])\s?(\d{1,3}[a-z]?)(?:\s+(pro\+?|pro|ultra|plus|lite|neo|fe|e|s))?(?![a-z0-9])", re.I)
 
_OTHER_PATTERNS = [
    r"\bASUS\s+(?:ROG\s+Phone|Zenfone)\s+[A-Za-z0-9]+\b",
    r"\bSony\s+Xperia\s+[A-Za-z0-9]+\b",
]
 
 
def _fmt_apple(m):
    if m.group(3):
        return "Apple iPhone Air"
    num = m.group(1)
    suffix = re.sub(r"\s+", "", (m.group(2) or "").lower())
    if suffix == "e":
        return f"Apple iPhone {num}e"
    names = {"promax": "Pro Max", "pro": "Pro", "plus": "Plus", "mini": "Mini", "air": "Air"}
    return f"Apple iPhone {num}" + (f" {names[suffix]}" if suffix else "")
 
 
def _fmt_samsung_letter(m):
    letter = m.group(1).upper()
    suffix = (m.group(3) or ("Plus" if m.group(4) else "")).lower()
    names = {"fe": "FE", "ultra": "Ultra", "plus": "Plus", "edge": "Edge"}
    return f"Samsung Galaxy {letter}{m.group(2)}" + (f" {names[suffix]}" if suffix else "")
 
 
def _fmt_pixel(m):
    suffix = re.sub(r"\s+", " ", (m.group(2) or "").lower()).strip()
    if suffix == "a":
        return f"Google Pixel {m.group(1)}a"
    return f"Google Pixel {m.group(1)}" + (" " + suffix.title() if suffix else "").replace("Xl", "XL")
 
 
def _fmt_oneplus(m):
    suffix = (m.group(2) or "").lower()
    if suffix == "pro":
        return f"OnePlus {m.group(1)} Pro"
    return f"OnePlus {m.group(1)}{suffix.upper()}"
 
 
def _fmt_vivo(m):
    name = f"vivo {m.group(1).upper()}{m.group(2).lower() if m.group(2)[-1].isalpha() else m.group(2)}"
    if m.group(3):
        name += " " + ("Pro+" if m.group(3).lower() == "pro+" else m.group(3).title())
    return name
 
 
def extract_product_query(question):
    q = clean_text(question)
 
    m = _APPLE_RE.search(q)
    if m:
        return _fmt_apple(m)
 
    m = _SAMSUNG_FOLD_RE.search(q)
    if m:
        return f"Samsung Galaxy Z {m.group(1).title()}{m.group(2)}" + (" FE" if m.group(3) else "")
 
    m = _PIXEL_RE.search(q)
    if m:
        return _fmt_pixel(m)
 
    m = _ONEPLUS_NORD_RE.search(q)
    if m:
        return clean_text(m.group(0)).title().replace("Oneplus", "OnePlus")
 
    m = _ONEPLUS_RE.search(q)
    if m:
        return _fmt_oneplus(m)
 
    m = _VIVO_RE.search(q)
    if m:
        return _fmt_vivo(m)
 
    for pattern in _OTHER_PATTERNS:
        m = re.search(pattern, q, re.I)
        if m:
            return clean_text(m.group(0))
 
    generic = _generic_brand_product(q)
    if generic:
        return generic
 
    for m in _SAMSUNG_LETTER_RE.finditer(q):
        letter = m.group(1).lower()
        has_galaxy = "galaxy" in m.group(0).lower()
        if letter == "s" or has_galaxy:
            return _fmt_samsung_letter(m)
 
    return ""
 
 
_BRAND_NAMES = {
    "oppo": "OPPO", "realme": "realme", "redmi": "Redmi", "xiaomi": "Xiaomi", "poco": "POCO",
    "iqoo": "iQOO", "motorola": "Motorola", "moto": "Motorola Moto", "nothing": "Nothing",
    "cmf": "CMF", "honor": "Honor", "infinix": "Infinix", "tecno": "Tecno", "lava": "Lava",
    "itel": "itel",
}
_ROUTER_BRANDS = set(_BRAND_NAMES) | {"sony", "asus", "nokia", "huawei", "samsung", "vivo",
                                      "oneplus", "google", "apple"}
_SUFFIX = r"pro\+?|plus|ultra|max|lite|neo|fe|se|gt|speed|turbo|prime|master|mini|power|fusion|ace|edition"
_GENERIC_RE = re.compile(
    r"\b(" + "|".join(_BRAND_NAMES) + r")\s+"
    r"((?:note|find|reno|edge|phone|narzo|magic|gt|x|neo|hot|spark|camon|pova|g)\s?)?"
    r"([a-z]{0,3}\s?\d{1,3}[a-z]?)"
    r"((?:\s?(?:" + _SUFFIX + r"|5g|4g))*)(?![a-z0-9])",
    re.I,
)
_STOP_SHORT = {"a", "an", "as", "at", "be", "by", "do", "if", "in", "is", "it", "me", "my", "no",
               "of", "on", "or", "so", "to", "up", "us", "vs", "we", "ok", "hi", "pc"}
 
 
def _generic_brand_product(question):
    m = _GENERIC_RE.search(question)
    if not m:
        return ""
    brand = _BRAND_NAMES[m.group(1).lower()]
    prefix = clean_text(m.group(2) or "")
    model = re.sub(r"\s+", "", m.group(3))
    model = model.upper() if model[0].isalpha() else model.lower()
    if len(prefix) == 1:                      # "x" + "7" -> X7, "g" + "96" -> G96
        model, prefix = prefix.upper() + model, ""
    elif prefix:
        prefix = prefix.upper() if len(prefix) <= 2 else prefix.title()
    words = []
    for w in re.findall(_SUFFIX, m.group(4) or "", re.I):
        words.append(w.upper() if w.lower() in {"fe", "se", "gt"} else w.title())
 
    # A short trailing token right after the model (e.g. "reno 15 f") is probably part of the
    # variant name; keep it rather than silently answering for the base model.
    tail = re.match(r"\s+([A-Za-z]{1,2})(?![A-Za-z0-9])", question[m.end():])
    if tail and tail.group(1).lower() not in _STOP_SHORT and not words:
        words.append(tail.group(1).upper())
    return clean_text(" ".join([brand, prefix, model] + words))
 
 
def normalize_compact_model_query(question):
    """iphone15 -> iphone 15, oneplus13r -> oneplus 13 r (fallback only)."""
    text = clean_text(question)
    text = re.sub(r"([A-Za-z]+)(\d+)([A-Za-z]+)", r"\1 \2 \3", text)
    text = re.sub(r"([A-Za-z]+)(\d+)\b", r"\1 \2", text)
    return re.sub(r"\s+", " ", text).strip()
 
 
def detect_product(question):
    return extract_product_query(question) or extract_product_query(normalize_compact_model_query(question))
 
 
def get_model_tokens(question):
    text = normalize_compact_model_query(question).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return [t for t in text.split() if t not in GENERIC_WORDS]
 
 
# ============================================================
# SEARCH-BASED PRODUCT IDENTIFICATION (used for "latest phone" style queries)
# ============================================================
 
def clean_search_product_title(title):
    title = clean_text(title)
    if not title:
        return ""
    candidate = re.split(r"\s+(?:\||-|–|—)\s+|\|", title, maxsplit=1)[0].strip()
    candidate = re.sub(
        r"\b(?:full\s+)?(?:specifications|specification|specs|price|review|features|"
        r"features\s+and\s+specifications)\b.*$", "", candidate, flags=re.I)
    candidate = candidate.strip(" -–—:|,")
    candidate = re.sub(r"^(?:buy|review|price|latest|new|launch|launched)\s+(?:the\s+)?", "",
                       candidate, flags=re.I)
    return candidate.strip()
 
 
def resolve_product_with_search(question):
    normalized_question = normalize_compact_model_query(question)
    model_tokens = get_model_tokens(normalized_question)
 
    if is_latest_mobile_question(question):
        query = (f"latest smartphone launched in India {datetime.now().strftime('%B %Y')} "
                 "official launch specifications GSMArena 91mobiles Gadgets360 "
                 "-upcoming -rumour -rumor -leak")
    else:
        query = (f'identify exact smartphone model "{clean_text(question)}" '
                 "smartphone specifications India official product page "
                 "GSMArena 91mobiles Gadgets360 -upcoming -rumour -rumor -leak")
 
    print("\n[PRODUCT SEARCH]")
    print(query)
 
    try:
        results = get_search_results(web_search(query, count=10))
    except Exception as error:
        print("[PRODUCT SEARCH] ERROR:", error)
        return ""
    if not results:
        print("[PRODUCT SEARCH] No results.")
        return ""
 
    evidence = []
    for index, result in enumerate(results[:10], start=1):
        priority = source_priority(result.get("url", ""))
        if priority < 0:
            continue
        evidence.append(
            f"SOURCE {index}\nPRIORITY: {priority}\n"
            f"TITLE: {clean_text(result.get('title', ''))}\n"
            f"URL: {clean_text(result.get('url', ''))}\n"
            f"DESCRIPTION: {clean_text(result.get('description', ''))}")
    if not evidence:
        return ""
 
    # Deterministic pass for named models (e.g. compact queries).
    if model_tokens and not is_latest_mobile_question(question):
        wanted = re.sub(r"[^a-z0-9]+", "", "".join(model_tokens))
        candidates = []
        for result in results:
            priority = source_priority(result.get("url", ""))
            if priority < 0:
                continue
            title = clean_text(result.get("title", ""))
            compact = re.sub(r"[^a-z0-9]+", "", title.lower())
            if wanted and wanted in compact:
                candidates.append((priority, title))
        if candidates:
            candidates.sort(reverse=True)
            best = clean_search_product_title(candidates[0][1])
            if best:
                print("[PRODUCT SEARCH] Resolved product:", best)
                return best
 
    # The LLM is used ONLY to pick a product NAME from search evidence.
    prompt = f"""
You are Nexus's PRODUCT IDENTIFICATION engine.
 
USER QUERY:
{question}
 
SEARCH EVIDENCE:
{chr(10).join(evidence)}
 
Identify the exact smartphone model the user means.
Return JSON only: {{"product": ""}}
 
Rules:
1. Use ONLY the supplied search evidence.
2. Never invent a model or substitute a similar one.
3. For a "latest" query choose a phone the evidence says is already launched, not a rumour.
4. Return only the product name.
"""
    try:
        response = llm_chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Identify products only from supplied evidence. Return JSON."},
                {"role": "user", "content": prompt},
            ],
            format="json", think=False, stream=False, options={"temperature": 0},
        )
        content = response.get("message", {}).get("content", "")
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = {}
        product = clean_text(data.get("product", ""))
        if product:
            print("[PRODUCT SEARCH] Resolved product:", product)
        return product
    except Exception as error:
        print("[PRODUCT SEARCH] Resolution failed (is Ollama running?):", error)
        return ""
 
 
def resolve_product(question):
    direct = detect_product(question)
    if direct:
        print("[PRODUCT SEARCH] Direct model match:", direct)
        return direct
 
    resolved = resolve_product_with_search(question)
    if resolved:
        # normalise the name found in a page title through the same variant-safe rules
        return detect_product(resolved) or resolved
    return ""
 
 
# ============================================================
# SMARTPHONE SPECIFICATION PIPELINE (page-first, no LLM)
# ============================================================
 
def answer_techspecs(question):
    print("\n[PRODUCT IDENTIFICATION]")
    product = resolve_product(question)
 
    if not product:
        return "Nexus: I could not identify the exact smartphone from your question."
 
    print("\n[PRODUCT QUERY]", product)
 
    try:
        return "Nexus:\n" + phone_specs.build_spec_answer(product)
    except Exception as error:
        return f"Nexus: The specification pipeline failed: {error}"
 
 
# ============================================================
# GENERIC WEB ANSWER
# ============================================================
 
def answer_web(question):
    print("\n[1/3] Searching You.com...")
 
    try:
        search_result = web_search(
            f"{question} India current latest -upcoming -rumour -rumor -leak", count=10)
    except Exception as error:
        return f"Nexus: Web search failed: {error}"
 
    results = get_search_results(search_result)
    if not results:
        return "Nexus: I could not retrieve reliable web evidence right now."
 
    evidence = []
    for result in results[:8]:
        evidence.append(
            f"TITLE: {clean_text(result.get('title', ''))}\n"
            f"URL: {clean_text(result.get('url', ''))}\n"
            f"DESCRIPTION: {clean_text(result.get('description', ''))}")
 
    prompt = f"""
You are Nexus.
 
Answer the user's question using ONLY the retrieved web evidence.
 
QUESTION:
{question}
 
EVIDENCE:
{chr(10).join(evidence)}
 
Rules:
1. Never use model memory.
2. Never guess.
3. Never invent.
4. Never substitute another product.
5. If sources disagree, say so.
6. Answer directly.
"""
    try:
        response = llm_chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Answer only from supplied evidence. Never guess."},
                {"role": "user", "content": prompt},
            ],
            think=False, stream=False, options={"temperature": 0},
        )
        answer = clean_text(response.get("message", {}).get("content", ""))
        return "Nexus:\n" + answer
    except Exception as error:
        return f"Nexus: The local model failed: {error}"
 
 
# ============================================================
# RAG
# ============================================================
 
def answer_rag(question):
    print("\n[1/3] Searching Nexus knowledge base...")
 
    try:
        results = search_knowledge(question, top_k=3)
    except Exception as error:
        return f"Nexus: RAG search failed: {error}"
 
    if not results:
        return "Nexus: No relevant knowledge was found."
 
    context = []
    for result in results:
        context.append(
            f"Topic: {result.get('topic', '')}\n"
            f"Similarity: {result.get('similarity', '')}\n"
            f"Content:\n{result.get('content', '')}")
 
    prompt = f"""
You are Nexus.
 
Answer using ONLY the supplied knowledge.
 
QUESTION:
{question}
 
KNOWLEDGE:
{chr(10).join(context)}
 
Rules:
1. Never invent facts.
2. Never use model memory.
3. Explain simply.
4. Answer directly.
"""
    try:
        response = llm_chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Answer only from supplied knowledge. Never invent."},
                {"role": "user", "content": prompt},
            ],
            think=False, stream=False, options={"temperature": 0},
        )
        answer = clean_text(response.get("message", {}).get("content", ""))
        return "Nexus:\n" + answer
    except Exception as error:
        return f"Nexus: The local model failed: {error}"
 
 
# ============================================================
# MAIN
# ============================================================
 
def main():
    question = input("You: ").strip()
 
    if not question:
        print("Nexus: Please enter a question.")
        return
 
    print("\n[ROUTER] Analysing question...")
    route = route_question(question)
    print(f"[ROUTER] Selected tool: {route}")
 
    if route == "techspecs":
        print(answer_techspecs(question))
        return
 
    if route == "web":
        print(answer_web(question))
        return
 
    print(answer_rag(question))
 
 
if __name__ == "__main__":
    main()