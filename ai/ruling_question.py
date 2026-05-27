from google import genai
import os
import re
import requests


class RulingQuestion:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_KEY"))

    def extract_card_names(self, message):
        return re.findall(r"\[([^\]]+)\]", message)

    def get_card_data(self, card_name):
        response = requests.get(
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

    def build_card_context(self, card_names):
        if not card_names:
            return "No card names were provided in brackets."

        card_context = ""

        for card_name in card_names:
            card_data = self.get_card_data(card_name)

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

    def rullings_question(self, message):
        card_names = self.extract_card_names(message)
        card_context = self.build_card_context(card_names)

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"""
            You are a Magic: The Gathering rules assistant focused ONLY on rulings, card interactions, and rules clarification.
            
            Rules:
            - Use the provided Scryfall card data as the source of truth.
            - Do not invent card text.
            - If a card was not found, say that clearly.
            - If no cards were provided in brackets, ask the user to use bracket format like [Sol Ring].
            - Keep responses brief and practical.
            
            Card data:
            {card_context}
            
            User message:
            {message}
            """
                    )

        return response.text