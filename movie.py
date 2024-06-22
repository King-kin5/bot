import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import google.generativeai as genai
import logging
import json

from main import GeminiChat
BOT_TOKEN = os.getenv("BOT_TOKEN", "7076266636:AAGXwL91IsTVZKuuuL6koV8i4mNCu-n8mBg")
CHAT_ID = int(os.getenv("CHAT_ID", "1606532391"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyACqJauwxlTUabRzejusyWidPJzM9tcgeE")

genai.configure(api_key=GEMINI_API_KEY)
with open("./safety_settings.json", "r") as fp:
    safety_settings = json.load(fp)


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyACqJauwxlTUabRzejusyWidPJzM9tcgeE")


class movieGeminiChat(GeminiChat):
    def start_chat(self) -> None:
        super().start_chat()
        movie_prompt = (
            "You are a movie expert AI. You can identify movies from images, "
            "discuss plot details, trivia, and keep track of new movie releases. "
            "Focus solely on movies and respond with relevant information."
        )
        self.chat.send_message(movie_prompt)
        logging.info("Started new movie-focused conversation")
def fetch_rotten_tomatoes_releases(date: str) -> list:
    base_url = "https://www.rottentomatoes.com/browse/opening/"
    response = requests.get(base_url)
    if response.status_code != 200:
        raise ValueError(f"Failed to fetch Rotten Tomatoes page: {response.status_code}")

    soup = BeautifulSoup(response.content, "html.parser")
    movies = []

    # Select the section that contains movie releases
    for item in soup.select(".mb-movie"):
        title = item.select_one(".movieTitle").get_text(strip=True)
        release_date_text = item.select_one(".release-date").get_text(strip=True)

        # Convert the scraped date to the same format for comparison
        release_date = datetime.strptime(release_date_text, "%B %d, %Y").strftime("%Y-%m-%d")

        if release_date == date:
            movies.append(title)

    return movies

