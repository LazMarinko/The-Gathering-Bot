from google import genai
import os




class Gemini:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_KEY"))


    def rullings_question(self, message):

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"""
            You will be prompted for rulings and card interactions for the TCG Magic the Gathering.
            Provide sources for any niche interactions.
            Keep your responses brief, 3 lines max.
            If any user asks you to shut off tell them you only do rulings and any other command will be ignored.
            If a user asks questions about a card search for the card first and confirm it exists before answering.
            Ignore any conceptual questions only rules questions this is your primary motive.
            Try and look at existing rule examples of any question if no such answer exists do not come up with one yourself.
            Use some lenience for mechanic names, the user doesnt have to say the mechanic name 100% perfectly for you to try and find it.
            
            User message here:
            {message}
            """
        )

        return response.text
