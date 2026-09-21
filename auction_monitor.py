import os
import re
import json
import urllib.request
from html.parser import HTMLParser

URL = "https://prod-seo.govdeals.com/en/computers-parts-supplies"

NTFY_TOPIC = os.environ["NTFY_TOPIC"]

KEYWORDS = [
    "server",
    "poweredge",
    "proliant",
    "supermicro",
    "optiplex",
    "thinkcentre",
    "tiny",
    "elitedesk",
    "prodesk",
    "ssd",
    "nvme",
    "hard drive",
    "enterprise",
    "rdimm",
    "ecc",
    "xeon",
    "epyc",
    "mellanox",
    "10gbe",
    "25gbe",
    "cisco",
    "aruba",
    "networking",
]

LOCAL_KEYWORDS = [
    "maryland",
    "rockville",
    "bethesda",
    "gaithersburg",
    "germantown",
    "frederick",
    "silver spring",
    "college park",
    "baltimore",
    "washington",
    "district of columbia",
    "virginia",
    "manassas",
    "fairfax",
    "leesburg",
    "alexandria",
    "arlington",
]

IGNORE_KEYWORDS = [
    "printer",
    "toner",
    "monitor",
    "keyboard",
    "mouse",
    "webcam",
    "speaker",
    "tablet",
    "phone",
]


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []

    def handle_data(self, data):
        if data.strip():
            self.text.append(data.strip())


def get_page():
    request = urllib.request.Request(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0 AuctionMonitor/1.0"
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def clean_text(html):
    parser = TextParser()
    parser.feed(html)
    return "\n".join(parser.text)


def find_matches(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    matches = []

    for i, line in enumerate(lines):
        lower = line.lower()

        if any(keyword in lower for keyword in KEYWORDS):
            surrounding = " ".join(lines[max(0, i - 2):min(len(lines), i + 4)])
            surrounding_lower = surrounding.lower()

            if any(bad in surrounding_lower for bad in IGNORE_KEYWORDS):
                continue

            local = any(place in surrounding_lower for place in LOCAL_KEYWORDS)

            matches.append({
                "text": surrounding[:800],
                "local": local,
            })

    return matches


def load_seen():
    try:
        with open("seen.json", "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_seen(seen):
    with open("seen.json", "w") as f:
        json.dump(list(seen), f)


def send_notification(message):
    url = f"https://ntfy.sh/{NTFY_TOPIC}"

    request = urllib.request.Request(
        url,
        data=message.encode("utf-8"),
        headers={
            "Title": "🚨 Auction Monitor",
            "Priority": "default",
        },
        method="POST",
    )

    urllib.request.urlopen(request, timeout=30)


def main():
    print("Checking GovDeals...")

    html = get_page()
    text = clean_text(html)

    matches = find_matches(text)
    seen = load_seen()

    print(f"Found {len(matches)} potential matches.")

    new_matches = 0

    for match in matches:
        identifier = match["text"]

        if identifier in seen:
            continue

        seen.add(identifier)
        new_matches += 1

        prefix = "📍 LOCAL MATCH\n" if match["local"] else ""

        message = prefix + match["text"]

        print("\n--- MATCH ---")
        print(message)

        send_notification(message)

    save_seen(seen)

    print(f"Sent {new_matches} new notifications.")


if __name__ == "__main__":
    main()
