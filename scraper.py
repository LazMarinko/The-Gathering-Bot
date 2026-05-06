import os
import json
import requests
from pathlib import Path

POSTED_FILE = "posted_cards.json"
DOWNLOAD_DIR = Path("downloaded_cards")

DOWNLOAD_DIR.mkdir(exist_ok=True)

SCRYFALL_URL = "https://api.scryfall.com/cards/search"

PARAMS = {
    "q": "game:paper",
    "unique": "prints",
    "order": "released",
    "dir": "desc"
}


def load_posted_cards():
    if not os.path.exists(POSTED_FILE):
        return set()

    with open(POSTED_FILE, "r", encoding="utf-8") as file:
        return set(json.load(file))


def save_posted_cards(posted_cards):
    with open(POSTED_FILE, "w", encoding="utf-8") as file:
        json.dump(sorted(list(posted_cards)), file, indent=4)


def get_card_image(card):
    if "image_uris" in card:
        return card["image_uris"].get("normal")

    if "card_faces" in card:
        for face in card["card_faces"]:
            if "image_uris" in face:
                return face["image_uris"].get("normal")

    return None


def download_image(card_id, image_url):
    file_path = DOWNLOAD_DIR / f"{card_id}.jpg"

    if file_path.exists():
        return file_path

    response = requests.get(image_url, timeout=20)
    response.raise_for_status()

    with open(file_path, "wb") as file:
        file.write(response.content)

    return file_path


def check_for_new_spoilers():
    posted_cards = load_posted_cards()

    response = requests.get(SCRYFALL_URL, params=PARAMS, timeout=20)
    response.raise_for_status()

    data = response.json()
    new_images = []

    for card in data["data"]:
        card_id = card["id"]
        card_name = card["name"]

        if card_id in posted_cards:
            continue

        image_url = get_card_image(card)

        if not image_url:
            continue

        try:
            image_path = download_image(card_id, image_url)
            new_images.append((card_id, card_name, image_path))
        except Exception as error:
            print(f"Failed to download {card.get('name')}: {error}")

    return new_images


def mark_as_posted(card_id):
    posted_cards = load_posted_cards()
    posted_cards.add(card_id)
    save_posted_cards(posted_cards)