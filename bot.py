import requests
from PIL import Image
from io import BytesIO
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# API endpoints for Jikan and Trace.moe
TRACE_MOE_API_URL = "https://api.trace.moe/search"
JIKAN_API_URL = "https://api.jikan.moe/v4/anime"

# Replace this with your Telegram Bot API token
TELEGRAM_BOT_TOKEN = '7740301929:AAFy_4vCQ1EeRdbzoFmVr91J4qJPrx5pe_M'

# State to track if the user has requested /name and the bot is expecting an image
user_waiting_for_image = {}

# Start command - Welcomes the user and provides a brief explanation of the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the Anime Character Name Provider Bot!\n"
        "Use the /name command and send me an anime image to know the names of the characters!"
    )

# Help command - Provides instructions on how to use the bot
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "To use this bot:\n"
        "1. Type /name.\n"
        "2. Send an anime image (a screenshot or photo).\n"
        "I'll identify the anime and provide the character names!"
    )

# Command /name to prompt the user for an image
async def name_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_waiting_for_image
    user_id = update.message.from_user.id
    user_waiting_for_image[user_id] = True
    await update.message.reply_text(
        "Send me an anime image, and I'll identify the anime and provide the character names!"
    )

# Function to search for the anime using Trace.moe API
def search_anime_by_image(image_bytes):
    try:
        files = {'image': image_bytes}

        # Send the image to the Trace.moe API
        response = requests.post(TRACE_MOE_API_URL, files=files)
        response.raise_for_status()

        # Parse the response
        trace_data = response.json()
        if trace_data['result']:
            # Get the title of the anime and the MyAnimeList ID (mal_id)
            anime_title = trace_data['result'][0]['anilist']['title']['romaji']
            anime_mal_id = trace_data['result'][0]['anilist']['idMal']
            return anime_title, anime_mal_id
        else:
            return None, None
    except Exception as e:
        print(f"Error searching anime by image: {e}")
        return None, None

# Function to retrieve anime character information using Jikan API
def get_anime_characters(anime_mal_id):
    try:
        # Fetch characters related to the anime using its MyAnimeList ID
        character_url = f"{JIKAN_API_URL}/{anime_mal_id}/characters"
        response = requests.get(character_url)
        response.raise_for_status()

        character_data = response.json()
        if 'data' in character_data:
            characters = character_data['data']
            return characters
        else:
            return None
    except Exception as e:
        print(f"Error fetching character info: {e}")
        return None

# Handles image processing after the /name command
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_waiting_for_image
    user_id = update.message.from_user.id

    # Check if the user has issued the /name command and is now sending an image
    if user_id in user_waiting_for_image and user_waiting_for_image[user_id]:
        # Reset state so the bot doesn't expect another image
        user_waiting_for_image[user_id] = False

        # Get the image from the message
        photo_file = await update.message.photo[-1].get_file()
        image_bytes = BytesIO()
        await photo_file.download(out=image_bytes)
        image_bytes.seek(0)

        # Search for the anime by the image
        anime_title, anime_mal_id = search_anime_by_image(image_bytes)
        
        if anime_title and anime_mal_id:
            characters = get_anime_characters(anime_mal_id)
            if characters:
                response_text = f"Anime detected: {anime_title}\nCharacters:\n"
                for char in characters:
                    response_text += f"Name: {char['character']['name']}, Role: {char['role']}\n"
                await update.message.reply_text(response_text)
            else:
                await update.message.reply_text(f"Anime detected: {anime_title}, but no character information was found.")
        else:
            await update.message.reply_text("I couldn't identify the anime from the image. Please try another image.")
    else:
        # If user hasn't issued the /name command first, instruct them to do so
        await update.message.reply_text("Please use the /name command first before sending an image.")

# Fallback for unknown commands
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sorry, I didn't understand that command. Use /name followed by an anime image!")

def main():
    # Create the Application object
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("name", name_command))

    # Add message handler for images
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))

    # Add message handler for unknown commands
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    # Start the bot
    app.run_polling()

if __name__ == "__main__":
    main()
