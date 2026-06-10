import os
import json
import requests
from pathlib import Path


class SpoilerScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "The-Gathering-Bot/1.0",
            "Accept": "application/json;q=0.9,*/*;q=0.8"
        })

        self.posted_file = "posted_cards.json"
        self.download_dir = Path("downloaded_cards")
        self.download_dir.mkdir(exist_ok=True)

        self.scryfall_url = "https://api.scryfall.com/cards/search"
        self.params = {
            "q": "game:paper",
            "unique": "prints",
            "order": "released",
            "dir": "desc"
        }

    def load_posted_cards(self):
        if not os.path.exists(self.posted_file):
            return set()

        with open(self.posted_file, "r", encoding="utf-8") as file:
            return set(json.load(file))

    def save_posted_cards(self, posted_cards):
        with open(self.posted_file, "w", encoding="utf-8") as file:
            json.dump(sorted(list(posted_cards)), file, indent=4)

    def get_card_image(self, card):
        if "image_uris" in card:
            return card["image_uris"].get("normal")

        if "card_faces" in card:
            for face in card["card_faces"]:
                if "image_uris" in face:
                    return face["image_uris"].get("normal")

        return None

    def download_image(self, card_id, image_url):
        file_path = self.download_dir / f"{card_id}.jpg"

        if file_path.exists():
            return file_path

        response = self.session.get(image_url, timeout=20)
        response.raise_for_status()

        with open(file_path, "wb") as file:
            file.write(response.content)

        return file_path

    def check_for_new_spoilers(self):
        posted_cards = self.load_posted_cards()

        response = self.session.get(self.scryfall_url, params=self.params, timeout=20)

        if response.status_code != 200:
            print(response.url)
            print(response.status_code)
            print(response.text)
            return []

        data = response.json()
        new_cards = []

        for card in data["data"]:
            card_id = card["id"]
            card_name = card["name"]

            if card_id in posted_cards:
                continue

            image_url = self.get_card_image(card)

            if not image_url:
                continue

            image_path = self.download_image(card_id, image_url)
            new_cards.append((card_id, card_name, image_path))

        return new_cards

    def mark_as_posted(self, card_id):
        posted_cards = self.load_posted_cards()
        posted_cards.add(card_id)
        self.save_posted_cards(posted_cards)