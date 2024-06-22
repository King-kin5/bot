import logging
import asyncio
import os
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import json
import google.generativeai as genai
from movie import movieGeminiChat
import http.server
import socketserver

PORT = 8080

# Load environment variables
load_dotenv()

# Your API tokens
BOT_TOKEN = os.getenv("BOT_TOKEN", "7076266636:AAGXwL91IsTVZKuuuL6koV8i4mNCu-n8mBg")
CHAT_ID = int(os.getenv("CHAT_ID", "1606532391"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyACqJauwxlTUabRzejusyWidPJzM9tcgeE")

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Gemini API
genai.configure(api_key=GEMINI_API_KEY)
with open("./safety_settings.json", "r") as fp:
    safety_settings = json.load(fp)

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

    def get_chat_title(self) -> str:
        try:
            return self.send_message("Write a one-line short title up to 10 words for this conversation in plain text.")
        except Exception as e:
            self._handle_exception("get chat title", e)

    def close(self) -> None:
        logging.info("Closed model instance")
        self.chat = None

# Initialize GeminiChat instance
gemini_chat = GeminiChat(GEMINI_API_KEY)

# Global set to keep track of latest news titles to avoid duplicates
latest_news_titles = set()

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the conversation with /start command and ask the user for input."""
    keyboard = [
        [
            InlineKeyboardButton("Movie News", callback_data="MOVIE_NEWS"),
            InlineKeyboardButton("TV News", callback_data="TV_NEWS"),
        ],
        [
            InlineKeyboardButton("Chat with AI", callback_data="CHAT_AI"),
            InlineKeyboardButton("Movie Gemini", callback_data="MOVIE_GEMINI"),
        ],
        [InlineKeyboardButton("Start Over", callback_data="START_OVER")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        text="Hi. It's Bot Mode. You can ask me anything and talk to me about what you want.",
        reply_markup=reply_markup,
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button clicks from the inline keyboard."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "MOVIE_NEWS":
        await notify_latest_news(update, "https://discussingfilm.net/category/film/")
    elif data == "TV_NEWS":
        await notify_latest_news(update, "https://discussingfilm.net/category/tv/")
    elif data == "CHAT_AI":
        await query.edit_message_text(text="Send me a message and I'll respond!")
    elif data == "MOVIE_GEMINI":
        await query.edit_message_text(text="You have chosen Movie mode. Send me a message about movies!")
        context.user_data['chat_mode'] = 'MOVIE_GEMINI'
    elif data == "START_OVER":
        await start(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Use the buttons to navigate through options.")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message_text = update.message.text
    chat_mode = context.user_data.get('chat_mode', 'NORMAL_AI')
    if chat_mode == 'MOVIE_GEMINI':
        # Create an instance of the movieGeminiChat class
        movie_gemini_chat = movieGeminiChat(GEMINI_API_KEY)
        # Call the start_chat method to initialize the chat attribute
        movie_gemini_chat.start_chat()
        # Call the send_message method on the instance, providing the message_text as an  argument
        response = movie_gemini_chat.send_message(message_text)
    else:
        gemini_chat.start_chat()  # Initialize the chat
        response = gemini_chat.send_message(message_text)

        await update.message.reply_text(" typing...", parse_mode="Markdown")
    await update.message.reply_text(response)
# Function to fetch the latest news from a specific section
def fetch_latest_news(section_url, max_articles=10):
    """Fetch the latest news articles from the given section URL."""
    response = requests.get(section_url)
    if response.status_code!= 200:
        logger.error(f"Failed to fetch the website content: {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    articles = soup.select('article')

    news_list = []

    for article in articles[:max_articles]:  # Limit to max_articles
        title_tag = article.select_one('h2 a')
        if title_tag is None:
            continue

        title = title_tag.get_text(strip=True)
        link = title_tag['href']
        summary_tag = article.select_one('p')
        summary = summary_tag.get_text(strip=True) if summary_tag else 'No summary available.'

        news_list.append({
            'title': title,
            'link': link,
            'ummary': summary
        })

    logger.info(f"Fetched {len(news_list)} articles from {section_url}")
    return news_list

# Function to notify about the latest news
async def notify_latest_news(update: Update, section_url: str) -> None:
    """Notify about the latest news from a given section URL."""
    global latest_news_titles
    news_list = fetch_latest_news(section_url)
    if not news_list:
        await update.callback_query.edit_message_text("No latest news found.")
        return

    new_articles = 0
    messages = []  # Store all messages to be sent
    for news in news_list:
        if news['title'] not in latest_news_titles:
            message = f"📰 {news['title']}\n{news['summary']}\n[Read more]({news['link']})"
            messages.append(message)
            latest_news_titles.add(news['title'])
            new_articles += 1

    if new_articles == 0:
        await update.callback_query.edit_message_text("No new articles since the last check.")
    else:
        # Send messages
        for message in messages:
            await update.callback_query.message.reply_text(message, parse_mode="Markdown")


# Handle unknown commands
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Sorry, I didn't understand that command.")

def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    logger.info('Starting bot...')
    application.run_polling()

def set_webhook():
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook'
    data = {'url': f'https://bot-73ru.onrender.com/webhook'}
    response = requests.post(url, json=data)
    if response.status_code == 200:
        print('Webhook set up successfully!')
    else:
        print('Error setting up webhook:', response.text)

if __name__ == '__main__':
    try:
        asyncio.run(asyncio.wait_for(main(), timeout=60))
    except asyncio.TimeoutError:
        logger.error("The bot operation timed out....")
        set_webhook()

    Handler = http.server.SimpleHTTPRequestHandler

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print("serving at port", PORT)
        httpd.serve_forever()