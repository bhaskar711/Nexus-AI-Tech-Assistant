import re
import json
from datetime import datetime

import ollama

from tools import search_knowledge

from you_search_tool import (
    web_search,
    format_search_results
)


MODEL = "qwen3.5:4b"


# ============================================================
# ROUTER
# ============================================================

def route_question(question):

    question_lower = question.lower()

    web_keywords = [
        "latest",
        "current",
        "today",
        "newest",
        "recent",
        "recently",
        "news",
        "launched",
        "launch",
        "price",
        "pricing",
        "available",
        "availability",
        "upcoming"
    ]

    techspecs_keywords = [
        "specification",
        "specifications",
        "specs",
        "ram",
        "storage",
        "battery",
        "charging",
        "camera",
        "display",
        "processor",
        "chipset",
        "dimensions",
        "weight",
        "refresh rate",
        "resolution",
        "brightness",
        "ois",
        "sensor",
        "selfie",
        "ultrawide",
        "telephoto",
        "ip rating",
        "operating system"
    ]

    if any(
        keyword in question_lower
        for keyword in web_keywords
    ):
        return "web"

    if any(
        keyword in question_lower
        for keyword in techspecs_keywords
    ):
        return "web_specs"

    return "rag"


# ============================================================
# BASIC CLEANING
# ============================================================

def clean_text(text):

    if not isinstance(text, str):
        return ""

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# PRODUCT EXTRACTION
# ============================================================

def normalize_product_name(name):

    name = clean_text(name).lower()

    replacements = [
        (r"\bapple\b\s*", ""),
        (r"\bsamsung\b\s*", ""),
        (r"\bgoogle\b\s*", "")
    ]

    for pattern, replacement in replacements:
        name = re.sub(
            pattern,
            replacement,
            name
        )

    name = re.sub(
        r"\s+",
        " ",
        name
    )

    return name.strip()


def extract_product_query(question):

    question = clean_text(question)

    patterns = [

        # iPhone
        r"\b(?:Apple\s+)?iPhone\s+"
        r"\d{1,2}"
        r"(?:\s*(?:Pro Max|Pro|Plus|Mini|Air|e))?",

        # Samsung Galaxy
        r"\b(?:Samsung\s+)?Galaxy\s+"
        r"(?:(?:Z\s*)?"
        r"(?:Fold|Flip|TriFold)"
        r"\s*\d{1,2}"
        r"|"
        r"[A-Z]\d{1,3}"
        r"|"
        r"Note\s+\d{1,2}"
        r")"
        r"(?:\s*(?:FE|Ultra|Plus|Pro|Edge|Core|Active))?",

        # Pixel
        r"\b(?:Google\s+)?Pixel\s+"
        r"\d{1,2}"
        r"(?:\s*(?:Pro XL|Pro|a|Fold))?",

        # OnePlus
        r"\bOnePlus\s+"
        r"\d{1,2}[A-Za-z]?"
        r"(?:\s*(?:Pro|R|T|CE))?",

        # Xiaomi
        r"\bXiaomi\s+"
        r"\d{1,2}"
        r"(?:\s*(?:Ultra|Pro|T|Lite))?",

        # Redmi
        r"\bRedmi\s+"
        r"(?:Note\s+)?"
        r"\d{1,2}"
        r"(?:\s*(?:Pro Plus|Pro|Plus|5G|4G))?",

        # Realme
        r"\brealme\s+"
        r"(?:GT|"
        r"\d{1,2})"
        r"(?:\s*(?:Pro|Ultra|T|Plus|Master))?",

        # Motorola
        r"\bMotorola\s+"
        r"(?:Edge|Moto)\s+"
        r"[A-Za-z0-9]+"
        r"(?:\s*(?:Pro|Ultra|Fusion|Neo|Plus))?",

        # Nothing
        r"\bNothing\s+Phone\s+"
        r"\d{1,2}"
        r"(?:\s*(?:Pro|Plus|a))?",

        # Samsung shorthand
        r"\bz\s*(?:fold|flip|trifold)\s*\d{1,2}\b"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            question,
            re.IGNORECASE
        )

        if not match:
            continue

        product = clean_text(
            match.group(0)
        )

        product_lower = product.lower()

        shorthand_match = re.fullmatch(
            r"z\s*(fold|flip|trifold)\s*\d{1,2}",
            product_lower
        )

        if shorthand_match:

            series = shorthand_match.group(1)

            number_match = re.search(
                r"\d{1,2}",
                product_lower
            )

            number = (
                number_match.group(0)
                if number_match
                else ""
            )

            return (
                f"Samsung Galaxy Z "
                f"{series.capitalize()} {number}"
            )

        if product_lower.startswith(
            "galaxy "
        ):

            return (
                "Samsung "
                + product
            )

        return product

    return ""


# ============================================================
# BRAND
# ============================================================

def extract_brand(question):

    question_lower = clean_text(
        question
    ).lower()

    brands = [
        "apple",
        "samsung",
        "google",
        "oneplus",
        "xiaomi",
        "redmi",
        "realme",
        "motorola",
        "nothing",
        "oppo",
        "vivo",
        "iqoo",
        "honor",
        "asus",
        "sony",
        "poco"
    ]

    for brand in brands:

        if re.search(
            rf"\b{re.escape(brand)}\b",
            question_lower
        ):
            return brand

    if "iphone" in question_lower:
        return "apple"

    if "pixel" in question_lower:
        return "google"

    return ""


# ============================================================
# EXACT PRODUCT MATCHING
# ============================================================

def get_domain(url):

    match = re.search(
        r"https?://(?:www\.)?([^/]+)",
        str(url or ""),
        re.IGNORECASE
    )

    if not match:
        return ""

    return (
        match.group(1)
        .lower()
        .removeprefix("www.")
    )


def exact_product_in_result(
    result,
    product_query
):

    requested = normalize_product_name(
        product_query
    )

    if not requested:
        return False

    requested_pattern = re.escape(
        requested
    )

    title = clean_text(
        result.get("title", "")
    ).lower()

    url = clean_text(
        result.get("url", "")
    ).lower()

    if re.search(
        rf"(?<![a-z0-9])"
        rf"{requested_pattern}"
        rf"(?![a-z0-9])",
        title
    ):
        return True

    url_text = re.sub(
        r"[-_/]+",
        " ",
        url
    )

    if re.search(
        rf"(?<![a-z0-9])"
        rf"{requested_pattern}"
        rf"(?![a-z0-9])",
        url_text
    ):
        return True

    return False


# ============================================================
# TRUSTED SOURCES
# ============================================================

TRUSTED_SOURCE_PRIORITY = {

    "apple.com": 100,
    "samsung.com": 100,
    "google.com": 100,
    "oneplus.com": 100,
    "xiaomi.com": 100,
    "mi.com": 100,
    "oppo.com": 100,
    "vivo.com": 100,
    "realme.com": 100,
    "motorola.com": 100,
    "nothing.tech": 100,

    "gsmarena.com": 90,
    "91mobiles.com": 85,
    "gadgets360.com": 80,

    "phonearena.com": 70,
    "androidauthority.com": 70,
    "theverge.com": 70,
    "techradar.com": 70,

    "digit.in": 65,
    "smartprix.com": 60,

    "flipkart.com": 60,
    "amazon.in": 60,
    "amazon.com": 60
}


LOW_QUALITY_DOMAINS = {
    "youtube.com",
    "youtu.be",
    "wikipedia.org",
    "devicespecifications.com",
    "cuit.columbia.edu"
}


def source_priority(url):

    domain = get_domain(url)

    if domain in LOW_QUALITY_DOMAINS:
        return -1

    if domain in TRUSTED_SOURCE_PRIORITY:
        return TRUSTED_SOURCE_PRIORITY[domain]

    return 0


# ============================================================
# RESULT TEXT
# ============================================================

def get_result_text(result):

    parts = []

    title = result.get(
        "title",
        ""
    )

    description = result.get(
        "description",
        ""
    )

    snippets = result.get(
        "snippets",
        []
    )

    if title:
        parts.append(title)

    if description:
        parts.append(description)

    if isinstance(
        snippets,
        list
    ):

        for snippet in snippets:

            if isinstance(
                snippet,
                str
            ):
                parts.append(
                    snippet
                )

    return clean_text(
        " ".join(parts)
    )


def get_search_results(
    search_result
):

    if not isinstance(
        search_result,
        dict
    ):
        return []

    results = search_result.get(
        "results",
        {}
    )

    web_results = (
        results.get(
            "web",
            []
        )
        or []
    )

    news_results = (
        results.get(
            "news",
            []
        )
        or []
    )

    return (
        web_results
        + news_results
    )


def web_search_failed(
    search_result
):

    return len(
        get_search_results(
            search_result
        )
    ) == 0


# ============================================================
# FILTER WEB RESULTS
# ============================================================

def filter_web_results(
    search_result,
    product_query=""
):

    results = get_search_results(
        search_result
    )

    candidates = []

    for result in results:

        url = result.get(
            "url",
            ""
        )

        priority = source_priority(
            url
        )

        if priority < 0:
            continue

        if (
            product_query
            and not exact_product_in_result(
                result,
                product_query
            )
        ):
            continue

        result_copy = dict(
            result
        )

        result_copy[
            "_nexus_source_priority"
        ] = priority

        candidates.append(
            result_copy
        )

    # If trusted sources exist, use them.
    trusted = [
        result
        for result in candidates
        if result.get(
            "_nexus_source_priority",
            0
        ) >= 60
    ]

    if trusted:
        candidates = trusted

    # Sort by trusted source priority.
    candidates.sort(
        key=lambda result:
        result.get(
            "_nexus_source_priority",
            0
        ),
        reverse=True
    )

    unique = []

    seen = set()

    for result in candidates:

        key = (
            get_domain(
                result.get(
                    "url",
                    ""
                )
            ),
            clean_text(
                result.get(
                    "title",
                    ""
                )
            ).lower()
        )

        if key in seen:
            continue

        seen.add(key)

        unique.append(
            result
        )

    return {
        "results": {
            "web": unique,
            "news": []
        }
    }


# ============================================================
# COMPACT EVIDENCE
# ============================================================

def build_compact_evidence(
    filtered_results,
    maximum=8
):

    web_results = (
        filtered_results
        .get(
            "results",
            {}
        )
        .get(
            "web",
            []
        )
    )

    compact = []

    for result in web_results[:maximum]:

        title = clean_text(
            result.get(
                "title",
                ""
            )
        )

        url = clean_text(
            result.get(
                "url",
                ""
            )
        )

        description = clean_text(
            result.get(
                "description",
                ""
            )
        )

        snippets = result.get(
            "snippets",
            []
        )

        snippet_text = " ".join(
            clean_text(item)
            for item in snippets
            if isinstance(
                item,
                str
            )
        )

        compact.append(
            f"SOURCE {len(compact) + 1}\n"
            f"TITLE: {title}\n"
            f"URL: {url}\n"
            f"DESCRIPTION: {description}\n"
            f"SNIPPETS: {snippet_text}"
        )

    return (
        "\n\n".join(
            compact
        )
    )


# ============================================================
# UNAVAILABLE EVIDENCE
# ============================================================

def unavailable_evidence(
    product_query,
    reason
):

    return (
        "NEXUS_EVIDENCE_UNAVAILABLE\n"
        f"Product: {product_query}\n"
        f"Reason: {reason}"
    )


# ============================================================
# REQUESTED FIELDS
# ============================================================

def requested_product_fields(
    question
):

    q = question.lower()

    fields = []

    if any(
        word in q
        for word in [
            "camera",
            "specification",
            "specifications",
            "specs"
        ]
    ):
        fields.append("camera")

    if any(
        word in q
        for word in [
            "display",
            "screen",
            "refresh",
            "resolution",
            "brightness"
        ]
    ):
        fields.append("display")

    if any(
        word in q
        for word in [
            "processor",
            "chipset",
            "soc",
            "performance"
        ]
    ):
        fields.append("processor")

    if any(
        word in q
        for word in [
            "battery",
            "charging"
        ]
    ):
        fields.append("battery")

    if any(
        word in q
        for word in [
            "ram",
            "storage",
            "memory"
        ]
    ):
        fields.append("memory")

    if any(
        word in q
        for word in [
            "dimensions",
            "weight"
        ]
    ):
        fields.append("dimensions")

    if any(
        word in q
        for word in [
            "software",
            "android",
            "ios",
            "operating system"
        ]
    ):
        fields.append("software")

    # Generic specification request.
    if any(
        word in q
        for word in [
            "specification",
            "specifications",
            "specs"
        ]
    ):

        default_fields = [
            "camera",
            "display",
            "processor",
            "battery",
            "memory",
            "dimensions",
            "software"
        ]

        for field in default_fields:

            if field not in fields:
                fields.append(
                    field
                )

    return fields


# ============================================================
# TARGETED WEB SEARCH
# ============================================================

def build_targeted_query(
    product_query,
    field
):

    field_queries = {

        "camera": (
            f"{product_query} camera specifications "
            f"main camera ultrawide telephoto selfie "
            f"sensor aperture OIS video India "
            f"official GSMArena 91mobiles Gadgets360 "
            f"-upcoming -rumour -rumor -leak"
        ),

        "display": (
            f"{product_query} display specifications "
            f"AMOLED OLED LTPO LTPS resolution refresh rate "
            f"brightness India official GSMArena 91mobiles "
            f"Gadgets360 -upcoming -rumour -rumor -leak"
        ),

        "processor": (
            f"{product_query} processor chipset SoC GPU "
            f"specifications India official GSMArena 91mobiles "
            f"Gadgets360 -upcoming -rumour -rumor -leak"
        ),

        "battery": (
            f"{product_query} battery capacity charging speed "
            f"wired wireless charging India official GSMArena "
            f"91mobiles Gadgets360 -upcoming -rumour -rumor -leak"
        ),

        "memory": (
            f"{product_query} RAM storage variants specifications "
            f"India official GSMArena 91mobiles Gadgets360 "
            f"-upcoming -rumour -rumor -leak"
        ),

        "dimensions": (
            f"{product_query} dimensions weight IP rating "
            f"specifications India official GSMArena 91mobiles "
            f"Gadgets360 -upcoming -rumour -rumor -leak"
        ),

        "software": (
            f"{product_query} operating system Android iOS "
            f"software version India official GSMArena 91mobiles "
            f"Gadgets360 -upcoming -rumour -rumor -leak"
        )
    }

    return field_queries.get(
        field,
        (
            f"{product_query} {field} specifications "
            f"India official GSMArena 91mobiles Gadgets360 "
            f"-upcoming -rumour -rumor -leak"
        )
    )


def search_missing_product_field(
    product_query,
    field
):

    query = build_targeted_query(
        product_query,
        field
    )

    print(
        f"\n[TARGETED SEARCH] Missing field: {field}"
    )

    print(
        "[TARGETED QUERY]",
        query
    )

    result = web_search(
        query,
        count=10
    )

    if web_search_failed(
        result
    ):
        return ""

    filtered = filter_web_results(
        result,
        product_query
    )

    web_results = (
        filtered
        .get(
            "results",
            {}
        )
        .get(
            "web",
            []
        )
    )

    print(
        "[TARGETED FILTER] Exact-product results:",
        len(web_results)
    )

    if not web_results:
        return ""

    return build_compact_evidence(
        filtered,
        maximum=6
    )


# ============================================================
# QWEN JSON EXTRACTION
# ============================================================

def extract_json_from_response(
    response_text
):

    if not response_text:
        return {}

    response_text = response_text.strip()

    # Remove markdown code fences.
    response_text = re.sub(
        r"```json",
        "",
        response_text,
        flags=re.IGNORECASE
    )

    response_text = re.sub(
        r"```",
        "",
        response_text
    )

    response_text = response_text.strip()

    # Direct JSON.
    try:
        data = json.loads(
            response_text
        )

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    # Find first JSON object.
    match = re.search(
        r"\{.*\}",
        response_text,
        re.DOTALL
    )

    if not match:
        return {}

    try:

        data = json.loads(
            match.group(0)
        )

        if isinstance(data, dict):
            return data

    except Exception:
        return {}

    return {}


def qwen_extract_missing_field(
    product_query,
    field,
    evidence
):

    if not evidence:
        return {}

    if field == "camera":

        schema = """
{
  "rear_configuration": "",
  "main_camera": "",
  "main_sensor": "",
  "main_aperture": "",
  "main_ois": "",
  "ultrawide": "",
  "ultrawide_sensor": "",
  "ultrawide_aperture": "",
  "telephoto": "",
  "telephoto_sensor": "",
  "telephoto_aperture": "",
  "telephoto_ois": "",
  "front_camera": "",
  "front_aperture": "",
  "rear_video": "",
  "front_video": ""
}
"""

    elif field == "display":

        schema = """
{
  "display_type": "",
  "display_size": "",
  "resolution": "",
  "refresh_rate": "",
  "touch_sampling_rate": "",
  "brightness": "",
  "protection": ""
}
"""

    elif field == "processor":

        schema = """
{
  "chipset": "",
  "process_node": "",
  "cpu": "",
  "gpu": ""
}
"""

    elif field == "battery":

        schema = """
{
  "battery_capacity": "",
  "wired_charging": "",
  "wireless_charging": ""
}
"""

    elif field == "memory":

        schema = """
{
  "ram": "",
  "storage": ""
}
"""

    elif field == "dimensions":

        schema = """
{
  "dimensions": "",
  "weight": "",
  "ip_rating": ""
}
"""

    elif field == "software":

        schema = """
{
  "operating_system": "",
  "software_version": ""
}
"""

    else:

        schema = """
{
  "value": ""
}
"""

    prompt = f"""
You are extracting one missing specification for Nexus.

PRODUCT:
{product_query}

FIELD:
{field}

EVIDENCE:
{evidence}

Return ONLY valid JSON.

SCHEMA:
{schema}

STRICT RULES:

1. Use ONLY facts explicitly present in the supplied evidence.

2. The evidence must refer to the exact requested product.

3. Never use your own training knowledge.

4. Never guess.

5. Never combine facts from another model.

6. Never convert an approximate value into an exact value.

7. If a value is not explicitly supported, leave that JSON value as "".

8. Do not write "Not available".

9. Do not write "unknown".

10. Do not write N/A.

11. Do not add extra JSON keys.

12. Preserve numbers and units exactly as supported by the evidence.

13. For camera specifications, keep main, ultrawide, telephoto and front-camera information separate.

14. If only some camera information is available, return only those supported values and leave the rest empty.
"""

    try:

        response = ollama.chat(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict factual "
                        "information extraction system. "
                        "Return valid JSON only."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            think=False,
            stream=False,
            options={
                "temperature": 0
            }
        )

        content = (
            response
            .get("message", {})
            .get("content", "")
        )

        data = extract_json_from_response(
            content
        )

        return data

    except Exception as error:

        print(
            "[QWEN EXTRACTION ERROR]",
            error
        )

        return {}


# ============================================================
# CLEAN EXTRACTED DATA
# ============================================================

def clean_extracted_data(
    data
):

    if not isinstance(
        data,
        dict
    ):
        return {}

    cleaned = {}

    for key, value in data.items():

        if not isinstance(
            value,
            str
        ):
            continue

        value = clean_text(
            value
        )

        if not value:
            continue

        forbidden = [
            "not available",
            "unavailable",
            "unknown",
            "n/a",
            "not specified",
            "not mentioned"
        ]

        if value.lower() in forbidden:
            continue

        cleaned[key] = value

    return cleaned


# ============================================================
# DETERMINE WHETHER FIELD WAS FOUND
# ============================================================

def field_has_data(
    data,
    field
):

    if not isinstance(
        data,
        dict
    ):
        return False

    for value in data.values():

        if isinstance(
            value,
            str
        ) and clean_text(value):

            return True

    return False


# ============================================================
# WEB SPECIFICATION EVIDENCE
# ============================================================

def get_specification_evidence(
    question
):

    product_query = extract_product_query(
        question
    )

    print(
        "[PRODUCT QUERY]",
        product_query
    )

    if not product_query:

        return (
            "",
            {},
            {}
        )

    # --------------------------------------------------------
    # FIRST SEARCH
    # --------------------------------------------------------

    search_query = (
        f"{product_query} specifications "
        f"{question} India "
        f"official specifications "
        f"GSMArena 91mobiles Gadgets360 "
        f"-upcoming -rumour -rumor -leak"
    )

    print(
        "\n[1/3] Searching You.com..."
    )

    print(
        "[SEARCH QUERY]",
        search_query
    )

    search_result = web_search(
        search_query,
        count=10
    )

    if web_search_failed(
        search_result
    ):

        print(
            "[WEB] No results returned."
        )

        return (
            unavailable_evidence(
                product_query,
                "You.com returned no web results"
            ),
            {},
            {}
        )

    filtered = filter_web_results(
        search_result,
        product_query
    )

    web_results = (
        filtered
        .get(
            "results",
            {}
        )
        .get(
            "web",
            []
        )
    )

    print(
        "[WEB FILTER] Exact-product results:",
        len(web_results)
    )

    if not web_results:

        return (
            unavailable_evidence(
                product_query,
                "No trusted exact-product result was found"
            ),
            {},
            {}
        )

    initial_evidence = build_compact_evidence(
        filtered,
        maximum=8
    )

    # --------------------------------------------------------
    # DETERMINE FIELDS THAT NEED VERIFICATION
    # --------------------------------------------------------

    fields = requested_product_fields(
        question
    )

    print(
        "[FIELDS] Requested fields:",
        ", ".join(fields)
        if fields
        else "general"
    )

    # --------------------------------------------------------
    # FIRST QWEN EXTRACTION
    #
    # We use Qwen to determine which requested areas are
    # actually supported by the first web search.
    # --------------------------------------------------------

    extracted_fields = {}

    for field in fields:

        print(
            f"\n[FIELD CHECK] Checking {field}..."
        )

        data = qwen_extract_missing_field(
            product_query,
            field,
            initial_evidence
        )

        data = clean_extracted_data(
            data
        )

        if field_has_data(
            data,
            field
        ):

            extracted_fields[field] = data

            print(
                f"[FIELD CHECK] {field}: data found"
            )

        else:

            print(
                f"[FIELD CHECK] {field}: data missing"
            )

    # --------------------------------------------------------
    # TARGETED SEARCH
    #
    # Only search fields that Qwen could not extract.
    # This prevents unnecessary You.com calls.
    # --------------------------------------------------------

    targeted_fields = {}

    for field in fields:

        if field in extracted_fields:
            continue

        targeted_evidence = (
            search_missing_product_field(
                product_query,
                field
            )
        )

        if not targeted_evidence:
            continue

        data = qwen_extract_missing_field(
            product_query,
            field,
            targeted_evidence
        )

        data = clean_extracted_data(
            data
        )

        if field_has_data(
            data,
            field
        ):

            targeted_fields[field] = data

            print(
                f"[TARGETED RESULT] {field}: data found"
            )

        else:

            print(
                f"[TARGETED RESULT] {field}: no exact data found"
            )

    # --------------------------------------------------------
    # COMBINE EXTRACTIONS
    # --------------------------------------------------------

    final_extracted = {}

    for field, data in extracted_fields.items():

        final_extracted[field] = data

    for field, data in targeted_fields.items():

        if field not in final_extracted:
            final_extracted[field] = data

        else:

            for key, value in data.items():

                if key not in final_extracted[field]:
                    final_extracted[field][key] = value

    return (
        initial_evidence,
        final_extracted,
        {
            "product": product_query,
            "fields": fields
        }
    )


# ============================================================
# GENERAL WEB SEARCH
# ============================================================

def get_general_web_evidence(
    question
):

    print(
        "\n[1/3] Calling You.com web search..."
    )

    current_date = datetime.now().strftime(
        "%B %Y"
    )

    product_query = extract_product_query(
        question
    )

    search_query = (
        f"{question} "
        f"India "
        f"official "
        f"{current_date} "
        f"-upcoming "
        f"-rumour "
        f"-rumor "
        f"-leak"
    )

    print(
        "[SEARCH QUERY]",
        search_query
    )

    result = web_search(
        search_query,
        count=10
    )

    if web_search_failed(
        result
    ):

        return unavailable_evidence(
            product_query,
            "You.com returned no web results"
        )

    filtered = filter_web_results(
        result,
        product_query
    )

    web_results = (
        filtered
        .get(
            "results",
            {}
        )
        .get(
            "web",
            []
        )
    )

    if not web_results:

        return unavailable_evidence(
            product_query,
            "No trusted exact-product web result was found"
        )

    return build_compact_evidence(
        filtered,
        maximum=8
    )


# ============================================================
# RAG EVIDENCE
# ============================================================

def get_rag_evidence(
    question
):

    print(
        "\n[1/3] Searching Nexus knowledge base..."
    )

    results = search_knowledge(
        question,
        top_k=3
    )

    print(
        "[1/3] RAG search completed."
    )

    if not results:
        return "No relevant knowledge was found."

    context = []

    for result in results:

        context.append(
            f"Topic: {result['topic']}\n"
            f"Similarity: {result['similarity']}\n"
            f"Content:\n{result['content']}"
        )

    return "\n\n".join(
        context
    )


# ============================================================
# FORMAT CAMERA
# ============================================================

def build_camera_section(
    camera
):

    if not isinstance(
        camera,
        dict
    ):
        return ""

    lines = []

    mapping = [

        (
            "rear_configuration",
            "Configuration"
        ),

        (
            "main_camera",
            "Main camera"
        ),

        (
            "main_sensor",
            "Main sensor"
        ),

        (
            "main_aperture",
            "Main aperture"
        ),

        (
            "main_ois",
            "Main OIS"
        ),

        (
            "ultrawide",
            "Ultrawide"
        ),

        (
            "ultrawide_sensor",
            "Ultrawide sensor"
        ),

        (
            "ultrawide_aperture",
            "Ultrawide aperture"
        ),

        (
            "telephoto",
            "Telephoto"
        ),

        (
            "telephoto_sensor",
            "Telephoto sensor"
        ),

        (
            "telephoto_aperture",
            "Telephoto aperture"
        ),

        (
            "telephoto_ois",
            "Telephoto OIS"
        ),

        (
            "front_camera",
            "Front camera"
        ),

        (
            "front_aperture",
            "Front aperture"
        ),

        (
            "rear_video",
            "Rear video"
        ),

        (
            "front_video",
            "Front video"
        )
    ]

    for key, label in mapping:

        value = camera.get(
            key,
            ""
        )

        if not value:
            continue

        lines.append(
            f"• {label}: {value}"
        )

    if not lines:
        return ""

    return (
        "CAMERAS\n"
        + "\n".join(lines)
    )


# ============================================================
# BUILD EXTRACTED EVIDENCE FOR FINAL ANSWER
# ============================================================

def build_structured_evidence(
    extracted_fields
):

    sections = []

    if not isinstance(
        extracted_fields,
        dict
    ):
        return ""

    field_titles = {
        "camera": "CAMERA FACTS",
        "display": "DISPLAY FACTS",
        "processor": "PROCESSOR FACTS",
        "battery": "BATTERY FACTS",
        "memory": "MEMORY FACTS",
        "dimensions": "PHYSICAL FACTS",
        "software": "SOFTWARE FACTS"
    }

    for field, data in extracted_fields.items():

        if not data:
            continue

        title = field_titles.get(
            field,
            field.upper()
        )

        values = []

        for key, value in data.items():

            if not value:
                continue

            values.append(
                f"{key}: {value}"
            )

        if not values:
            continue

        sections.append(
            title
            + "\n"
            + "\n".join(values)
        )

    return "\n\n".join(
        sections
    )


# ============================================================
# FINAL ANSWER
# ============================================================

def generate_final_answer(
    question,
    route,
    evidence,
    extracted_fields,
    product_query
):

    structured_evidence = (
        build_structured_evidence(
            extracted_fields
        )
    )

    final_prompt = f"""
You are Nexus, a technology assistant.

USER QUESTION:
{question}

EXACT PRODUCT:
{product_query}

ORIGINAL WEB EVIDENCE:
{evidence}

STRUCTURED FACT EXTRACTION:
{structured_evidence}

Your task is to answer the user's question clearly.

STRICT RULES:

1. Use ONLY the supplied evidence and structured facts.

2. Never use your own memory or training knowledge.

3. Never invent a specification.

4. Never estimate a missing number.

5. Never substitute another product.

6. Never mix the requested product with a Pro, Plus, Ultra, Max, Lite, or another variant.

7. Never mix information from a different generation.

8. If a fact is not supported, SKIP that fact completely.

9. Do NOT write:
   - Not available
   - Unavailable
   - Unknown
   - N/A
   - Not specified

10. Do NOT create an "Unavailable Specifications" section.

11. Do NOT mention missing fields.

12. Do NOT mention the web-search process.

13. Do NOT mention Qwen, You.com, routing, prompts, evidence processing, or internal implementation.

14. Only display a field when a concrete value is supported by the supplied evidence.

15. Preserve numerical values and units from the evidence.

16. If multiple sources provide the same fact, use the supported value.

17. If sources clearly disagree, briefly mention the disagreement rather than guessing.

18. For camera specifications, keep:
   - main camera
   - ultrawide
   - telephoto
   - front camera
   separate.

19. For a generic specification question, organize the answer under useful headings such as:
   - Display
   - Performance
   - Memory
   - Cameras
   - Battery
   - Physical
   - Software

20. Do not force every heading to appear. If a section has no supported facts, skip the section.

21. Keep the answer concise but useful.

22. Explain technical terms simply when appropriate.

23. Start directly with the answer.

"""

    try:

        response = ollama.chat(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Nexus, a factual "
                        "technology assistant. "
                        "Use only supplied evidence. "
                        "Never invent facts."
                    )
                },
                {
                    "role": "user",
                    "content": final_prompt
                }
            ],
            think=False,
            stream=True,
            options={
                "temperature": 0
            }
        )

        print(
            "\nNexus:",
            end=" ",
            flush=True
        )

        answer = ""

        for chunk in response:

            text = (
                chunk
                .get("message", {})
                .get("content", "")
            )

            print(
                text,
                end="",
                flush=True
            )

            answer += text

        print()

        return answer

    except Exception as error:

        print(
            "\n[QWEN ERROR]",
            error
        )

        return ""


# ============================================================
# MAIN
# ============================================================

question = input(
    "You: "
).strip()


if not question:

    print(
        "Nexus: Please enter a question."
    )

    raise SystemExit(0)


print(
    "\n[ROUTER] Analysing question..."
)


route = route_question(
    question
)


print(
    f"[ROUTER] Selected tool: {route}"
)


# ============================================================
# SPECIFICATION ROUTE
# ============================================================

if route == "web_specs":

    print(
        "\n[MODE] Product specification mode"
    )

    (
        evidence,
        extracted_fields,
        metadata
    ) = get_specification_evidence(
        question
    )

    product_query = metadata.get(
        "product",
        extract_product_query(question)
    )

    print(
        "\n[2/3] Evidence processing completed."
    )

    print(
        "[2/3] Original evidence characters:",
        len(evidence)
    )

    print(
        "[2/3] Structured fields found:",
        list(
            extracted_fields.keys()
        )
    )

    if evidence.startswith(
        "NEXUS_EVIDENCE_UNAVAILABLE"
    ):

        print(
            "\nNexus: I couldn't retrieve reliable "
            "web evidence for this product right now."
        )

        raise SystemExit(0)

    print(
        "\n[3/3] Sending final evidence to Qwen3.5:4B..."
    )

    generate_final_answer(
        question,
        route,
        evidence,
        extracted_fields,
        product_query
    )

    raise SystemExit(0)


# ============================================================
# GENERAL WEB ROUTE
# ============================================================

if route == "web":

    evidence = get_general_web_evidence(
        question
    )

    print(
        "\n[2/3] Evidence received."
    )

    print(
        "[2/3] Evidence characters:",
        len(evidence)
    )

    if evidence.startswith(
        "NEXUS_EVIDENCE_UNAVAILABLE"
    ):

        print(
            "\nNexus: I couldn't retrieve reliable "
            "web evidence for this question right now."
        )

        raise SystemExit(0)

    product_query = extract_product_query(
        question
    )

    print(
        "\n[3/3] Sending evidence to Qwen3.5:4B..."
    )

    generate_final_answer(
        question,
        route,
        evidence,
        {},
        product_query
    )

    raise SystemExit(0)


# ============================================================
# RAG ROUTE
# ============================================================

evidence = get_rag_evidence(
    question
)

print(
    "\n[2/3] Evidence received."
)

print(
    "[2/3] Evidence characters:",
    len(evidence)
)

print(
    "\n[3/3] Sending evidence to Qwen3.5:4B..."
)

generate_final_answer(
    question,
    route,
    evidence,
    {},
    ""
)