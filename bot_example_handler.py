import logging
import html
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from src.core.services import chat_service
from src.core.formatters import safe_markdown_to_html

logger = logging.getLogger(__name__)


async def verify_authorization(update: Update) -> bool:
    """
    Centralized authorization check.
    Returns True if authorized, False otherwise (and handles the rejection message).
    """
    user = update.effective_user
    if not chat_service.is_authorized(user.id):
        await chat_service.register_unauthorized_attempt(user)
        raw_md = (
            "⛔ **Acesso Negado.**\n"
            "Olá! Eu sou o MedSecondBrain, um assistente privado.\n"
            "Seu ID não está autorizado.\n\n"
            "Para solicitar acesso:\n"
            "1️⃣ Use o comando /who_am_i para ver seus dados.\n"
            "2️⃣ Envie essas informações para [Dr. André Quadros](https://instagram.com/dr.andreq)."
        )
        formatted_html = await safe_markdown_to_html(raw_md)
        await update.message.reply_html(formatted_html)
        return False
    return True

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /start command.
    """
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot.")
    
    if not await verify_authorization(update):
        return

    response = await chat_service.get_or_create_user(user)
    await update.message.reply_text(response)

async def who_am_i_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Returns the user's details for whitelist configuration.
    """
    user = update.effective_user
    msg = (
        f"👤 **Identificação de Usuário**\n\n"
        f"🆔 **ID**: `{user.id}`\n"
        f"👤 **Username**: @{user.username or 'N/A'}\n"
        f"📛 **Nome**: {user.full_name}\n\n"
        "📋 **Instruções**:\n"
        "Copie as informações acima e envie para o administrador em:\n"
        "👉 [instagram.com/dr.andreq](https://instagram.com/dr.andreq)"
    )
    await update.message.reply_markdown(msg, disable_web_page_preview=True)

async def chat_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle text messages.
    """
    user = update.effective_user
    text = update.message.text
    
    if not await verify_authorization(update):
        return

    # Show typing indicator
    try:
        await context.bot.send_chat_action(chat_id = update.effective_chat.id, action = ChatAction.TYPING)
    except Exception as e:
        logger.warning(f"Could not send typing action: {e}")

    response = await chat_service.process_user_message(user, text)
    try:
        formatted_html = await safe_markdown_to_html(response)
        await update.message.reply_html( formatted_html )
    except Exception as e:
        logger.error(f"Markdown formatting failed: {e}. Falling back to plain text.")
        await update.message.reply_text(response, parse_mode = None)

async def voice_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle voice messages.
    """
    user = update.effective_user
    voice = update.message.voice

    if not await verify_authorization(update):
        return

    if voice.duration > 120:
        await update.message.reply_text("⚠️ Audio muito longo. Por favor, mantenha abaixo de 2 minutos.")
        return

    # Show upload/typing indicator
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.RECORD_VOICE)
    except Exception as e:
        logger.warning(f"Could not send action: {e}")

    # Download file
    try:
        file_obj = await voice.get_file()
        voice_bytes = await file_obj.download_as_bytearray()
        
        # Determine mime type (Telegram voices are usually OGG Opus)
        mime_type = voice.mime_type or "audio/ogg"
        
        response = await chat_service.process_audio_message(
            user, 
            audio_bytes = bytes(voice_bytes), 
            mime_type = mime_type
        )
        
        try:
            formatted_html = await safe_markdown_to_html(response)
            await update.message.reply_html( formatted_html )
        except Exception as e:
            logger.error(f"Markdown formatting failed: {e}. Falling back to plain text.")
            await update.message.reply_text(response, parse_mode = None)
        
    except Exception as e:
        logger.error(f"Error processing voice: {e}", exc_info = True)
        await update.message.reply_text("❌ Erro ao processar mensagem de voz.")

async def test_format_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Test command to verify Telegram Markdown rendering.
    Usage: /test_format <text>
    """
    if not context.args:
        await update.message.reply_text("Usage: /test_format <text>")
        return

    text = " ".join(context.args)
    
    msg = (
        f"*TITLE: {text.upper()}*\n\n"
        f"*Bold*: *{text}*\n"
        f"_Italic_: _{text}_\n"
        f"`Code`: `{text}`\n\n"
        f"*List of Characters*:\n"
    )
    
    for char in text[:5]:
        msg += f"- {char}\n"
        
    try:
        # Use our custom parser to format!
        formatted_html = await safe_markdown_to_html(msg)
        await update.message.reply_html(formatted_html)
    except Exception as e:
        logger.error(f"Test format failed: {e}")
        await update.message.reply_text(f"❌ Formatting failed: {e}\n\nRaw text:\n{msg}")