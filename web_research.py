import os
import json
import requests
from dotenv import load_dotenv


load_dotenv()


API_KEY = os.getenv("YDC_API_KEY")

BASE_URL = "https://ydc-index.io/v1/search"


def search_web(query, count=10):

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "query": query,
        "count": count
    }

    response = requests.post(
        BASE_URL,
        headers=headers,
        json=data
    )

    response.raise_for_status()

    return response.json()


def get_results(data):

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

    combined = []

    for result in web_results:

        combined.append({
            "type": "web",
            "title": result.get(
                "title",
                ""
            ),
            "url": result.get(
                "url",
                ""
            ),
            "date": result.get(
                "page_age",
                ""
            ),
            "description": result.get(
                "description",
                ""
            ),
            "snippets": result.get(
                "snippets",
                []
            )
        })

    for result in news_results:

        combined.append({
            "type": "news",
            "title": result.get(
                "title",
                ""
            ),
            "url": result.get(
                "url",
                ""
            ),
            "date": result.get(
                "page_age",
                ""
            ),
            "description": result.get(
                "description",
                ""
            ),
            "snippets": result.get(
                "snippets",
                []
            )
        })

    return combined


def print_results(title, results):

    print()
    print("=" * 70)
    print(title)
    print("=" * 70)

    for index, result in enumerate(
        results,
        start=1
    ):

        print()
        print(
            f"SOURCE {index}"
        )

        print(
            "TITLE:",
            result["title"]
        )

        print(
            "URL:",
            result["url"]
        )

        print(
            "DATE:",
            result["date"]
        )

        print(
            "DESCRIPTION:",
            result["description"]
        )

        snippets = result["snippets"]

        if snippets:

            print(
                "EVIDENCE:"
            )

            for snippet in snippets[:3]:

                print(
                    "-",
                    snippet
                )


def research_latest_samsung():

    queries = [

        (
            "Samsung smartphones "
            "launched in India "
            "2026 September August July "
            "official launch"
        ),

        (
            "Samsung Galaxy smartphone "
            "India launch 2026 "
            "September August July "
            "Galaxy S Galaxy A Galaxy M Galaxy Z"
        ),

        (
            "Samsung latest Galaxy phones "
            "India 2026 launched "
            "September 2026"
        ),

        (
            "site:samsung.com/in/newsroom "
            "Galaxy smartphone India "
            "2026 launch"
        )

    ]

    all_results = []

    for index, query in enumerate(
        queries,
        start=1
    ):

        print()
        print(
            f"SEARCH {index}"
        )

        print(
            "QUERY:",
            query
        )

        data = search_web(
            query,
            count=10
        )

        results = get_results(
            data
        )

        print_results(
            f"RESULTS FOR SEARCH {index}",
            results
        )

        all_results.extend(
            results
        )

    combined_data = {
        "results": {
            "web": [],
            "news": []
        }
    }

    for result in all_results:

        if result["type"] == "web":

            combined_data["results"]["web"].append(
                result
            )

        else:

            combined_data["results"]["news"].append(
                result
            )

    with open(
        "web_result.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            combined_data,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 70)

    print(
        "RESEARCH COMPLETED"
    )

    print(
        "=" * 70
    )

    print(
        "Total search results collected:",
        len(all_results)
    )

    print(
        "Saved as: web_result.json"
    )


if __name__ == "__main__":

    research_latest_samsung()