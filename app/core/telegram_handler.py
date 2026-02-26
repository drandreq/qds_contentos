import os
import logging
import asyncio
from datetime import datetime
from typing import List
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from fastapi import Request
from core.authenticator import authenticator
from google.genai import types

logger = logging.getLogger(__name__)

class TelegramHandler:
    def __init__(self):
        self.application: Application = None
        self.authorized_users: List[int] = []
        self._is_polling = False
        self._voice_queue = asyncio.Queue()
        self._queue_worker_task = None
        
    def initialize(self):
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token or token == "your_telegram_bot_token_here":
            logger.warning("TELEGRAM_BOT_TOKEN not set or invalid. Telegram Bot disabled.")
            return

        # Load authorized users
        auth_users_str = os.getenv("TELEGRAM_AUTHORIZED_USER_IDS", "")
        self.authorized_users = [
            int(uid.strip()) for uid in auth_users_str.split(",") if uid.strip().isdigit()
        ]
        
        logger.info(f"Telegram Bot initialized. Authorized User IDs: {self.authorized_users}")

        # Build application
        self.application = Application.builder().token(token).build()

        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("who_am_i", self.who_am_i_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message_handler))
        self.application.add_handler(MessageHandler(filters.VOICE, self.voice_message_handler))

    async def verify_authorization(self, update: Update) -> bool:
        """
        Centralized authorization check.
        Returns True if authorized, False otherwise (and handles the rejection message).
        """
        user = update.effective_user
        if not user or user.id not in self.authorized_users:
            logger.warning(f"Unauthorized Telegram access attempt from User ID: {user.id}")
            msg = (
                "⛔ *Acesso Negado.*\n"
                "Olá! Eu sou o assistente do ContentOS.\n"
                "Seu ID não está autorizado.\n\n"
                "Para solicitar acesso:\n"
                "1️⃣ Use o comando /who\\_am\\_i para ver seus dados.\n"
                "2️⃣ Envie essas informações para o administrador."
            )
            await update.message.reply_markdown(msg)
            return False
        return True

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.verify_authorization(update):
            return
            
        user = update.effective_user
        await update.message.reply_text(f"Olá, {user.first_name}! Eu sou o ContentOS bot. Envie-me textos ou áudios para transformá-los em Markdown seeds.")

    async def who_am_i_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        msg = (
            f"👤 *Identificação de Usuário*\n\n"
            f"🆔 *ID*: `{user.id}`\n"
            f"👤 *Username*: @{user.username or 'N/A'}\n"
            f"📛 *Nome*: {user.full_name}\n\n"
            "📋 *Instruções*:\n"
            "Copie as informações acima e envie para o administrador."
        )
        await update.message.reply_markdown(msg)

    async def text_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.verify_authorization(update):
            return
            
        text = update.message.text
        # Sprint 5 basic response: Acknowledge receipt
        await update.message.reply_text(f"Recebi seu texto com {len(text.split())} palavras. (Integração de semente na próxima sprint).")

    async def voice_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Sprint 6: Handle incoming voice messages, save locally, and queue for processing.
        """
        if not await self.verify_authorization(update):
            return
            
        user = update.effective_user
        voice = update.message.voice
        
        # Enforce 10 minute limit (600 seconds)
        if voice.duration > 600:
            await update.message.reply_text("⚠️ Áudio muito longo. Por favor, mantenha abaixo de 10 minutos.")
            return

        # Let the user know we received it and are processing
        await update.message.reply_text("⏳ Processando seu áudio...")
        
        try:
            # 1. Ensure cache directory exists
            cache_dir = os.path.join(os.getcwd(), "vault", ".cache", "voice_uploads")
            os.makedirs(cache_dir, exist_ok=True)
            
            # 2. Get file from Telegram
            file_obj = await voice.get_file()
            
            # 3. Create a unique filename with timestamp and user ID
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"voice_{user.id}_{timestamp_str}.ogg"
            filepath = os.path.join(cache_dir, filename)
            
            # 4. Download file to disk
            await file_obj.download_to_drive(custom_path=filepath)
            logger.info(f"Downloaded voice note to {filepath}")
            
            # 5. Enqueue the file for background processing
            await self._voice_queue.put({
                "filepath": filepath,
                "mime_type": voice.mime_type or "audio/ogg",
                "chat_id": update.effective_chat.id,
                "bot": context.bot
            })
            
        except Exception as e:
            logger.error(f"Error handling voice message: {e}")
            await update.message.reply_text("❌ Ocorreu um erro ao receber o áudio.")

    async def _process_voice_queue(self):
        """
        Background worker that processes voice files from the queue using Gemini.
        Unloads the main event loop to keep FastAPI responsive.
        """
        logger.info("Voice processing background worker started.")
        while True:
            try:
                task = await self._voice_queue.get()
                filepath = task["filepath"]
                mime_type = task["mime_type"]
                chat_id = task["chat_id"]
                bot = task["bot"]
                
                # Check authenticator layer
                if authenticator.client is None:
                    await bot.send_message(chat_id=chat_id, text="⚠️ Erro: Cliente do Google GenAI não inicializado.")
                    self._voice_queue.task_done()
                    continue

                # Show typing action to simulate active transcription
                await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                
                logger.info(f"Transcribing {filepath} using Gemini...")
                
                # Read bytes from disk
                with open(filepath, 'rb') as f:
                    audio_bytes = f.read()

                # Call Gemini for transcription
                prompt = "Transcreva este áudio com precisão absoluta, em Português. Formate o texto usando parágrafos e sem fazer resumos, apenas a transcrição fiel."
                
                response = authenticator.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                        prompt
                    ]
                )
                
                transcription = response.text
                
                # Send the result back
                reply_text = f"🎙️ **Transcrição:**\n\n{transcription}"
                await bot.send_message(chat_id=chat_id, text=reply_text, parse_mode='Markdown')
                logger.info(f"Successfully transcribed {filepath}.")
                
            except asyncio.CancelledError:
                logger.info("Voice processing worker cancelled.")
                break
            except Exception as e:
                logger.error(f"Error processing voice queue task: {e}")
                if "bot" in locals() and "chat_id" in locals():
                    await bot.send_message(chat_id=chat_id, text="❌ Ocorreu um erro na transcrição do áudio com a Gemini API.")
            finally:
                self._voice_queue.task_done()

    async def start_ptb(self):
        if not self.application:
            return
            
        await self.application.initialize()
        
        # Start the background processor
        self._queue_worker_task = asyncio.create_task(self._process_voice_queue())
        
        webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
        
        if webhook_url:
            logger.info(f"Setting Telegram webhook to: {webhook_url}")
            await self.application.bot.set_webhook(url=webhook_url)
            await self.application.start()
        else:
            logger.info("No TELEGRAM_WEBHOOK_URL found. Falling back to local long-polling...")
            self._is_polling = True
            await self.application.bot.delete_webhook()
            # Start polling in a non-blocking background task
            asyncio.create_task(self.application.updater.start_polling())
            await self.application.start()

    async def stop_ptb(self):
        if self._queue_worker_task:
            self._queue_worker_task.cancel()
            
        if self.application:
            if self._is_polling and self.application.updater:
                await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

    async def process_update(self, request: Request):
        if not self.application:
            return {"status": "disabled"}
            
        body = await request.json()
        update = Update.de_json(body, self.application.bot)
        await self.application.process_update(update)
        return {"status": "ok"}

# Singleton instance
telegram_bot = TelegramHandler()
