import os
import logging
import asyncio
import json
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import google.generativeai as genai
from movie import movieGeminiChat

load_dotenv()

# Your API tokens
BOT_TOKEN = os.getenv("BOT_TOKEN", "7076266636:AAGXwL91IsTVZKuuuL6koV8i4mNCu-n8mBg")
CHAT_ID = int(os.getenv("CHAT_ID", "1606532391"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyACqJauwxlTUabRzejusyWidPJzM9tcgeE")

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI()

# Initialize the Telegram bot
application = ApplicationBuilder().token(BOT_TOKEN).build()

# Load Gemini safety settings
with open("safety_settings.json", "r") as fp:
    safety_settings = json.load(fp)

class GeminiChat:
    def __init__(self, gemini_token: str, chat_history: list = None) -> None:
        self.chat_history = chat_history or []
        genai.configure(api_key=gemini_token)
        self.model = self._get_model()

    def _handle_exception(self, operation: str, e: Exception) -> None:
        logger.warning(f"Failed to {operation}: {e}")
        raise ValueError(f"Failed to {operation}: {e}")

    def _get_model(self, generative_model: str = "gemini-pro") -> genai.GenerativeModel:
        try:
            return genai.GenerativeModel(generative_model, safety_settings=safety_settings)
        except Exception as e:
            self._handle_exception("get model", e)

    def start_chat(self) -> None:
        try:
            self.chat = self.model.start_chat(history=self.chat_history)
        except Exception as e:
            self._handle_exception("start chat", e)

    def send_message(self, message_text: str) -> str:
        try:
            response = self.chat.send_message(message_text, stream=True)
            response.resolve()
            return "".join([text for text in response.text])
        except Exception as e:
            self._handle_exception("send message", e)
            return "Couldn't reach out to Google Gemini. Try Again..."

# Initialize GeminiChat instance
gemini_chat = GeminiChat( "AIzaSyACqJauwxlTUabRzejusyWidPJzM9tcgeE")

# Track latest news titles
latest_news_titles = set()

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
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook'
    data = {'url': 'https://bot-b7bm.onrender.com/webhook'}
    response = requests.post(url, json=data)
    if response.status_code == 200:
        logger.info('Webhook set up successfully!')
    else:
        logger.error(f'Error setting up webhook: {response.text}')

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
        movie_gemini_chat = movieGeminiChat(GEMINI_API_KEY)
        movie_gemini_chat.start_chat()
        response = movie_gemini_chat.send_message(message_text)
    else:
        gemini_chat.start_chat()
        response = gemini_chat.send_message(message_text)

    await update.message.reply_text(response)

def fetch_latest_news(section_url, max_articles=10):
    """Fetch the latest news articles from the given section URL."""
    response = requests.get(section_url)
    if response.status_code != 200:
        logger.error(f"Failed to fetch the website content: {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    articles = soup.select('article')

    news_list = []

    for article in articles[:max_articles]:
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
            'summary': summary
        })

    return news_list

async def notify_latest_news(update: Update, section_url: str) -> None:
    """Notify about the latest news from a given section URL."""
    global latest_news_titles
    news_list = fetch_latest_news(section_url)
    if not news_list:
        await update.callback_query.edit_message_text("No latest news found.")
        return

    new_articles = 0
    messages = []
    for news in news_list:
        if news['title'] not in latest_news_titles:
            message = f"📰 {news['title']}\n{news['summary']}\n[Read more]({news['link']})"
            messages.append(message)
            latest_news_titles.add(news['title'])
            new_articles += 1

    if new_articles == 0:
        await update.callback_query.edit_message_text("No new articles since the last check.")
    else:
        for message in messages:
            await update.callback_query.message.reply_text(message, parse_mode="Markdown")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Sorry, I didn't understand that command.")

# FastAPI route for webhook
@app.post("/webhook")
async def webhook(request: Request):
    try:
        update = Update.de_json(await request.json(), application.bot)
        await application.update_queue.put(update)
        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"Failed to process update: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# Registering handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
