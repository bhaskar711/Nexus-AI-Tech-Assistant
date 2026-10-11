import re
import json
from datetime import datetime


MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12
}


TRUSTED_INDIA_DOMAINS = [
    "gadgets360.com",
    "91mobiles.com",
    "digit.in",
    "smartprix.com",
    "mysmartprice.com",
    "hindustantimes.com",
    "business-standard.com",
    "businesstoday.in",
    "financialexpress.com",
    "moneycontrol.com",
    "indiatoday.in",
    "thehindu.com",
    "indianexpress.com"
]


NEGATIVE_WORDS = [
    "upcoming",
    "expected",
    "rumour",
    "rumor",
    "rumoured",
    "rumored",
    "leak",
    "leaked",
    "tipped",
    "could launch",
    "may launch",
    "might launch",
    "expected to launch",
    "reportedly launch",
    "reportedly launching",
    "will launch",
    "set to launch",
    "coming soon",
    "anticipated"
]


LAUNCH_WORDS = [
    "launched",
    "launch",
    "launches",
    "introduced",
    "introduces",
    "debuted",
    "debut",
    "released",
    "release",
    "available from",
    "went on sale",
    "sale started"
]


def make_date(month, day, year):

    try:

        return datetime(
            int(year),
            MONTHS[month.lower()],
            int(day)
        )

    except (ValueError, KeyError):

        return None


def clean_text(text):

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def extract_dates(text):

    dates = []

    month_pattern = (
        r"January|February|March|April|May|June|July|August|"
        r"September|October|November|December"
    )

    patterns = [

        # September 16th 2026
        # September 16, 2026
        (
            rf"\b({month_pattern})\s+"
            r"(\d{1,2})(?:st|nd|rd|th)?"
            r"(?:,\s*|\s+)"
            r"(20\d{2})\b"
        ),

        # 16th September 2026
        # 16 September 2026
        (
            rf"\b(\d{1,2})(?:st|nd|rd|th)?\s+"
            rf"({month_pattern})\s+"
            r"(20\d{2})\b"
        )
    ]

    for pattern_index, pattern in enumerate(patterns):

        matches = re.finditer(
            pattern,
            text,
            re.IGNORECASE
        )

        for match in matches:

            if pattern_index == 0:

                month = match.group(1)
                day = match.group(2)
                year = match.group(3)

            else:

                day = match.group(1)
                month = match.group(2)
                year = match.group(3)

            date_value = make_date(
                month,
                day,
                year
            )

            if date_value:

                dates.append({
                    "date": date_value,
                    "start": match.start(),
                    "end": match.end()
                })

    return dates


def has_negative_context(text):

    text_lower = text.lower()

    for word in NEGATIVE_WORDS:

        if word in text_lower:

            return True

    return False


def has_launch_context(text):

    text_lower = text.lower()

    for word in LAUNCH_WORDS:

        if word in text_lower:

            return True

    return False


def extract_product_names(text):

    patterns = [

        # Samsung Galaxy A08
        # Samsung Galaxy S26 FE
        # Samsung Galaxy Z Fold 8
        # Samsung Galaxy Z Flip 8
        # Samsung Galaxy Z Fold 8 Ultra
        r"\bSamsung\s+Galaxy\s+"
        r"(?:"
        r"[A-Z]\d{1,3}"
        r"|"
        r"Z\s+(?:Fold|Flip|TriFold)\s+\d{1,3}"
        r"|"
        r"S\d{1,3}"
        r"|"
        r"M\d{1,3}"
        r"|"
        r"F\d{1,3}"
        r"|"
        r"Note\s+\d{1,3}"
        r")"
        r"(?:\s+(?:FE|Ultra|Plus|Pro|Edge|Core|Active))?"
        r"(?:\s+\d+GB)?"
        r"(?:\s+(?:5G|4G))?",

        # Galaxy A08
        # Galaxy S26 FE
        r"\bGalaxy\s+"
        r"(?:"
        r"[A-Z]\d{1,3}"
        r"|"
        r"Z\s+(?:Fold|Flip|TriFold)\s+\d{1,3}"
        r"|"
        r"S\d{1,3}"
        r"|"
        r"M\d{1,3}"
        r"|"
        r"F\d{1,3}"
        r"|"
        r"Note\s+\d{1,3}"
        r")"
        r"(?:\s+(?:FE|Ultra|Plus|Pro|Edge|Core|Active))?"
        r"(?:\s+\d+GB)?"
        r"(?:\s+(?:5G|4G))?"
    ]

    found = []

    for pattern in patterns:

        matches = re.finditer(
            pattern,
            text,
            re.IGNORECASE
        )

        for match in matches:

            name = clean_text(
                match.group(0)
            )

            if name.lower().startswith(
                "galaxy "
            ):

                name = "Samsung " + name

            name = normalize_product_name(
                name
            )

            if is_real_product_name(
                name
            ):

                found.append({
                    "name": name,
                    "start": match.start(),
                    "end": match.end()
                })

    return found


def normalize_product_name(name):

    name = clean_text(
        name
    )

    name = re.sub(
        r"\s+",
        " ",
        name
    )

    name = re.sub(
        r"\bSamsung\s+Samsung\b",
        "Samsung",
        name,
        flags=re.IGNORECASE
    )

    return name


def is_real_product_name(name):

    name_lower = name.lower()

    if not name_lower.startswith(
        "samsung galaxy"
    ):

        return False

    invalid_names = [
        "samsung galaxy series",
        "samsung galaxy phones",
        "samsung galaxy mobiles",
        "samsung galaxy models",
        "samsung galaxy owners",
        "samsung galaxy feature",
        "samsung galaxy weekly",
        "samsung galaxy lineup"
    ]

    if name_lower in invalid_names:

        return False

    return True


def source_is_india_related(result):

    url = result.get(
        "url",
        ""
    ).lower()

    title = result.get(
        "title",
        ""
    ).lower()

    description = result.get(
        "description",
        ""
    ).lower()

    snippets = result.get(
        "snippets",
        []
    )

    snippet_text = " ".join(
        snippets
    ).lower()

    combined = (
        url
        + " "
        + title
        + " "
        + description
        + " "
        + snippet_text
    )

    if ".in/" in url:

        return True

    india_words = [
        "india",
        "indian",
        "in india"
    ]

    for word in india_words:

        if word in combined:

            return True

    return False


def get_evidence_text(result):

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

    parts = [
        title,
        description
    ]

    parts.extend(
        snippets
    )

    return clean_text(
        " ".join(parts)
    )


def extract_launch_evidence_for_product(
    text,
    product_start,
    product_end
):

    dates = extract_dates(
        text
    )

    candidates = []

    for date_info in dates:

        date_start = date_info["start"]
        date_end = date_info["end"]

        distance = min(
            abs(date_start - product_end),
            abs(product_start - date_end)
        )

        # Product and date should be reasonably close.
        if distance > 500:

            continue

        context_start = max(
            0,
            min(
                product_start,
                date_start
            ) - 180
        )

        context_end = min(
            len(text),
            max(
                product_end,
                date_end
            ) + 180
        )

        context = text[
            context_start:context_end
        ]

        context_lower = context.lower()

        if not has_launch_context(
            context
        ):

            continue

        if has_negative_context(
            context
        ):

            continue

        candidates.append({
            "date": date_info["date"],
            "context": context
        })

    if not candidates:

        return None

    # If multiple valid launch dates exist,
    # use the latest verified launch date.
    candidates.sort(
        key=lambda item: item["date"],
        reverse=True
    )

    return candidates[0]


def extract_products(data):

    results = data.get(
        "results",
        {}
    )

    web_results = results.get(
        "web",
        []
    )

    news_results = results.get(
        "news",
        []
    )

    all_results = (
        web_results
        + news_results
    )

    products = []

    for result in all_results:

        evidence = get_evidence_text(
            result
        )

        if not evidence:

            continue

        product_matches = extract_product_names(
            evidence
        )

        if not product_matches:

            continue

        india_related = source_is_india_related(
            result
        )

        for product_match in product_matches:

            launch_evidence = (
                extract_launch_evidence_for_product(
                    evidence,
                    product_match["start"],
                    product_match["end"]
                )
            )

            if launch_evidence is None:

                continue

            products.append({

                "name": product_match["name"],

                "launch_date": (
                    launch_evidence["date"]
                ),

                "india_related": india_related,

                "source_title": result.get(
                    "title",
                    ""
                ),

                "url": result.get(
                    "url",
                    ""
                ),

                "evidence": evidence,

                "launch_context": (
                    launch_evidence["context"]
                )

            })

    return products


def merge_products(products):

    merged = {}

    for product in products:

        key = product["name"].lower()

        if key not in merged:

            merged[key] = {

                "name": product["name"],

                "launch_date": product["launch_date"],

                "india_related": product["india_related"],

                "sources": []

            }

        existing = merged[key]

        if (
            product["india_related"]
            and not existing["india_related"]
        ):

            existing["india_related"] = True

        if (
            product["launch_date"]
            and (
                existing["launch_date"] is None
                or product["launch_date"]
                > existing["launch_date"]
            )
        ):

            existing["launch_date"] = (
                product["launch_date"]
            )

        source_exists = any(
            source["url"] == product["url"]
            for source in existing["sources"]
        )

        if not source_exists:

            existing["sources"].append({

                "title": product["source_title"],

                "url": product["url"],

                "india_related": product["india_related"],

                "evidence": product["evidence"],

                "launch_context": product[
                    "launch_context"
                ]

            })

    return list(
        merged.values()
    )


def find_latest(products):

    valid_products = [

        product

        for product in products

        if (
            product["launch_date"] is not None
            and product["india_related"]
        )

    ]

    if not valid_products:

        return None

    valid_products.sort(
        key=lambda product:
        product["launch_date"],
        reverse=True
    )

    return valid_products[0]


def print_product(product):

    print()

    print(
        "Product:",
        product["name"]
    )

    print(
        "Launch date:",
        product["launch_date"].strftime(
            "%Y-%m-%d"
        )
    )

    print(
        "India-related evidence:",
        product["india_related"]
    )

    print(
        "Supporting sources:",
        len(product["sources"])
    )

    for source in product["sources"]:

        print()

        print(
            "-",
            source["title"]
        )

        print(
            "  URL:",
            source["url"]
        )

        print(
            "  India-related:",
            source["india_related"]
        )

        print(
            "  Launch evidence:",
            source["launch_context"]
        )


if __name__ == "__main__":

    with open(
        "web_result.json",
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(
            file
        )

    products = extract_products(
        data
    )

    merged_products = merge_products(
        products
    )

    print()

    print(
        "VERIFIED LAUNCH CANDIDATES"
    )

    print(
        "=" * 60
    )

    if not merged_products:

        print(
            "No verified launch candidates found."
        )

    else:

        merged_products.sort(
            key=lambda product:
            product["launch_date"]
            if product["launch_date"]
            else datetime.min,
            reverse=True
        )

        for product in merged_products:

            print_product(
                product
            )

    latest = find_latest(
        merged_products
    )

    print()

    print(
        "=" * 60
    )

    print(
        "VERIFIED LATEST PRODUCT"
    )

    print(
        "=" * 60
    )

    if latest:

        print()

        print(
            "Product:",
            latest["name"]
        )

        print(
            "India launch date:",
            latest["launch_date"].strftime(
                "%Y-%m-%d"
            )
        )

        print(
            "Supporting sources:",
            len(latest["sources"])
        )

        for source in latest["sources"]:

            print()

            print(
                "SOURCE:",
                source["title"]
            )

            print(
                "URL:",
                source["url"]
            )

            print(
                "EVIDENCE:",
                source["launch_context"]
            )

    else:

        print(
            "No India launch information could be verified."
        )