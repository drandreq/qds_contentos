import logging
import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from src.bot import handlers
from src.core.config import settings


# Setup Logging
logging.basicConfig(
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level = getattr(logging, settings.LOG_LEVEL.upper())
)

async def post_init(application):
    """
    Post initialization hook.
    """
    # Set bot commands menu
    await application.bot.set_my_commands([
        ("start", "Start the bot"),
        ("who_am_i", "Get my ID for whitelist"),
        ("test_format", "Test Markdown formatting"),
    ])

def main():
    """
    Entry point for the bot.
    """
    application = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Register Handlers
    application.add_handler(CommandHandler("start", handlers.start_command))
    application.add_handler(CommandHandler("who_am_i", handlers.who_am_i_command))
    application.add_handler(CommandHandler("test_format", handlers.test_format_command))

    # Voice Handler must come before generic text if using filters properly,
    # but here filters.VOICE is specific.
    application.add_handler(MessageHandler(filters.VOICE, handlers.voice_message_handler))

    # Text Handler (exclude commands)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handlers.chat_message_handler))

    # Run
    # Note: run_polling() is blocking and handles the event loop.
    # In docker, we usually want this.
    application.run_polling()

if __name__ == '__main__':
    main()