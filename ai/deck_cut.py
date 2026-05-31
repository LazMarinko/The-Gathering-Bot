import os
import re

from google import genai

from web_scraper.card_finder import CardFinder


class DeckCut:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        self.card_finder = CardFinder()

    def _extract_card_names(self, deck_text):
        basic_lands = {
            "Plains",
            "Island",
            "Swamp",
            "Mountain",
            "Forest",
            "Wastes"
        }

        card_names = []

        for line in deck_text.splitlines():
            match = re.match(r"^\d+\s+(.+?)\s+\(", line.strip())

            if not match:
                continue

            card_name = match.group(1)

            if card_name in basic_lands:
                continue

            card_names.append(card_name)

        return card_names

    def _build_card_context(self, deck_text):
        card_names = self._extract_card_names(deck_text)

        cards_data = self.card_finder.get_cards_data(card_names)

        return "\n\n".join(
            f"Name: {card['name']}\n"
            f"Type: {card['type_line']}\n"
            f"Text: {card['oracle_text']}"
            for card in cards_data
        )

    def deckcut(self, message):
        card_context = self._build_card_context(message)

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"""
            You are an expert Magic: The Gathering Commander deck cutting assistant.

            You will receive one input containing:
            - Commander + Tags
            - Decklist
            - Cards to cut

            Hard rules:
            - The commander is NOT part of the decklist.
            - The final decklist must contain exactly 99 cards.
            - Cut exactly the number shown in "Cards to cut".
            - Do not calculate a different cut number.
            - Count duplicate quantities correctly, especially basic lands.
            - NEVER invent, rename, add, or replace cards.
            - ONLY remove cards that appear in the provided decklist.
            - Preserve exact card names and set codes as written.
            - Do not cut the commander.
            - NEVER cut lands.
            - Prioritize cutting nonland cards with duplicate or redundant effects.
            - Prefer cutting cards that are weaker, slower, too narrow, off-theme, or less synergistic with the commander.
            - If multiple cards do the same job, keep the stronger or more synergistic option and cut the weaker duplicate effect.
            - Do not output explanations.

            Selection logic:
            - Prioritize the listed commander/tags.
            - Cut low-synergy cards.
            - Cut redundant or inefficient cards.
            - Preserve ramp, draw, removal, core synergy, and mana consistency.

            Relevant card data:
            {card_context}

            Output exactly in this format:

            Cards Cut: <number from Cards to cut>

            Cuts:
            - <exact card line from decklist>
            - <exact card line from decklist>

            Updated Decklist:
            <full decklist after cuts, preserving original line formatting>

            Final Deck Count: 99

            Input:
            {message}
            """
        )

        return response.text