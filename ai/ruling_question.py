from google import genai
import os
import re

from web_scraper.card_finder import CardFinder


class RulingQuestion:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        self.card_finder = CardFinder()

    def extract_card_names(self, message):
        return re.findall(r"\[([^\]]+)\]", message)

    def build_card_context(self, card_names):
        if not card_names:
            return None

        card_context = ""

        for card_name in card_names:
            card_data = self.card_finder.get_card_data(card_name)

            if card_data is None:
                card_context += f"\nCard not found: {card_name}\n"
                continue

            card_context += f"""
            Card name:
            {card_data["name"]}

            Type:
            {card_data["type_line"]}

            Oracle text:
            {card_data["oracle_text"]}
            """

        return card_context

    def rulings_question(self, message):
        card_names = self.extract_card_names(message)
        card_context = self.build_card_context(card_names)

        if card_context is not None:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"""
                        You are a Magic: The Gathering rules assistant.

                        Your job is to answer rules questions using the provided Scryfall card data.

                        Rules:
                        - Treat the provided card data as the source of truth.
                        - Never invent card text, mana costs, abilities, or rulings.
                        - If the card data is incomplete, say so.
                        - Explain interactions according to the official Magic: The Gathering rules.
                        - If multiple cards are provided, explain how they interact.
                        - If the answer depends on additional game information, ask for that information.
                        - Keep answers concise, accurate, and practical.
                        - Do not discuss topics unrelated to Magic: The Gathering rules.

                        Card data:
                        {card_context}

                        User question:
                        {message}
                        """
            )
        else:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"""
                        You are a Magic: The Gathering rules assistant.

                        The user did not provide any card data.

                        Rules:
                        - Do not guess card text.
                        - Do not invent what a card does.
                        - If the question references specific cards, ask the user to provide them using square brackets.
                        - Example: [Sol Ring], [Counterspell], [Atraxa, Praetors' Voice]
                        - If the question is a general Magic rules question that does not require card text, answer it normally.
                        - Keep responses concise and practical.

                        User question:
                        {message}
                        """
            )

        return response.text