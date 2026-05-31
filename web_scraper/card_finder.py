import requests


class CardFinder:
    def __init__(self):
        self.session = requests.Session()

    def get_card_data(self, card_name):
        try:
            response = self.session.get(
                "https://api.scryfall.com/cards/named",
                params={"fuzzy": card_name},
                timeout=10
            )

            if response.status_code != 200:
                return None

            card = response.json()

            return {
                "name": card.get("name"),
                "type_line": card.get("type_line", ""),
                "oracle_text": card.get("oracle_text", "")
            }

        except requests.RequestException:
            return None

    def get_cards_data(self, card_names):
        cards = []

        for card_name in card_names:
            card_data = self.get_card_data(card_name)

            if card_data is not None:
                cards.append(card_data)

        return cards