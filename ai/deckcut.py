from google import genai
import os


class DeckCut():
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_KEY"))

    def deckcut(self, message):
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
            - Prefer cutting weak nonland cards before lands.
            - Do not output explanations.

            Selection logic:
            - Prioritize the listed commander/tags.
            - Cut low-synergy cards.
            - Cut redundant or inefficient cards.
            - Preserve ramp, draw, removal, core synergy, and mana consistency.

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

