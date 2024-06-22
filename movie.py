import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import google.generativeai as genai
import logging
import json
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
class GeminiChat:
    def __init__(self, gemini_token: str, chat_history: list = None) -> None:
        self.chat_history = chat_history or []
        self.GOOGLE_API_KEY = gemini_token
        genai.configure(api_key=self.GOOGLE_API_KEY)
        logging.info("Initiated new chat model")

    def _handle_exception(self, operation: str, e: Exception) -> None:
        logging.warning(f"Failed to {operation}: {e}")
        raise ValueError(f"Failed to {operation}: {e}")

    def _get_model(self, generative_model: str = "gemini-pro") -> genai.GenerativeModel:
        try:
            logging.info("Trying to get generative model")
            return genai.GenerativeModel(generative_model, safety_settings=safety_settings)
        except Exception as e:
            self._handle_exception("get model", e)

    def start_chat(self) -> None:
        try:
            model = self._get_model()
            self.chat = model.start_chat(history=self.chat_history)
            logging.info("Start new conversation")
        except Exception as e:
            self._handle_exception("start chat", e)

    def send_message(self, message_text: str) -> str:
        try:
            response = self.chat.send_message(message_text, stream=True)
            response.resolve()
            logging.info("Received response from Gemini")
            return "".join([text for text in response.text])
        except Exception as e:
            self._handle_exception("send message", e)
            return "Couldn't reach out to Google Gemini. Try Again..."

    def get_chat_history(self):
        try:
            return self.chat.history
        except Exception as e:
            self._handle_exception("get chat history", e)

    def close(self) -> None:
        logging.info("Closed model instance")
        self.chat = None
        self.chat_history = []

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
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import google.generativeai as genai
import logging
import json
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
class GeminiChat:
    def __init__(self, gemini_token: str, chat_history: list = None) -> None:
        self.chat_history = chat_history or []
        self.GOOGLE_API_KEY = gemini_token
        genai.configure(api_key=self.GOOGLE_API_KEY)
        logging.info("Initiated new chat model")

    def _handle_exception(self, operation: str, e: Exception) -> None:
        logging.warning(f"Failed to {operation}: {e}")
        raise ValueError(f"Failed to {operation}: {e}")

    def _get_model(self, generative_model: str = "gemini-pro") -> genai.GenerativeModel:
        try:
            logging.info("Trying to get generative model")
            return genai.GenerativeModel(generative_model, safety_settings=safety_settings)
        except Exception as e:
            self._handle_exception("get model", e)

    def start_chat(self) -> None:
        try:
            model = self._get_model()
            self.chat = model.start_chat(history=self.chat_history)
            logging.info("Start new conversation")
        except Exception as e:
            self._handle_exception("start chat", e)

    def send_message(self, message_text: str) -> str:
        try:
            response = self.chat.send_message(message_text, stream=True)
            response.resolve()
            logging.info("Received response from Gemini")
            return "".join([text for text in response.text])
        except Exception as e:
            self._handle_exception("send message", e)
            return "Couldn't reach out to Google Gemini. Try Again..."

    def get_chat_history(self):
        try:
            return self.chat.history
        except Exception as e:
            self._handle_exception("get chat history", e)

    def close(self) -> None:
        logging.info("Closed model instance")
        self.chat = None
        self.chat_history = []

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
