import os
import logging
import asyncio
from datetime import datetime
from typing import List
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
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
        self.application.add_handler(CommandHandler("test_format", self.test_format_command))
        self.application.add_handler(CallbackQueryHandler(self.dimensional_triage_callback))
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
            # 1. Ensure cache directory exists in the vault root
            cache_dir = "/vault/.cache/voice_uploads"
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
                prompt = (
                    "Atue como um especialista em comunicação e oratória. "
                    "Sua tarefa principal é transcrever este áudio com precisão absoluta em Português (sem inventar palavras ou fazer resumos). "
                    "No entanto, preste muita atenção à cadência da fala, ao tom, a eventuais gaguejos ou repetições, às pausas reflexivas/respiratórias e às mudanças de tema. "
                    "Use essas pistas não-verbais da minha voz para adicionar a pontuação correta (vírgulas, pontos e vírgulas, reticências, etc.) "
                    "e, o mais importante, para QUEBRAR O TEXTO em parágrafos muito bem estruturados sempre que houver uma clara mudança de ritmo ou de ideia. "
                    "O objetivo é gerar uma transcrição fiel que reflita o ritmo real e as falhas/sucessos da minha expressão verbal, me ajudando a analisar e melhorar meu fluxo de pensamento e comunicação."
                )
                
                response = authenticator.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                        prompt
                    ]
                )
                
                transcription = response.text
                
                # Save the base JSON transcription metadata for triage
                import time
                from core.models import TranscriptionMetadata
                from core.atomic_filesystem import atomic_fs

                os.makedirs("/vault/03_voice", exist_ok=True)
                json_filename = f"voice_{chat_id}_{int(time.time())}.json"
                
                meta = TranscriptionMetadata(
                    user_id=chat_id,
                    raw_text=transcription
                )
                
                atomic_fs.write_file(f"03_voice/{json_filename}", meta.model_dump_json(indent=2))

                # Construct 7D inline keyboard markdown
                keyboard = [
                    [InlineKeyboardButton("🧠 LOGOS", callback_data=f"dim:logos:{json_filename}"),
                     InlineKeyboardButton("🛠️ TECHNE", callback_data=f"dim:techne:{json_filename}")],
                    [InlineKeyboardButton("⚖️ ETHOS", callback_data=f"dim:ethos:{json_filename}"),
                     InlineKeyboardButton("🧬 BIOS", callback_data=f"dim:bios:{json_filename}")],
                    [InlineKeyboardButton("📈 STRATEGOS", callback_data=f"dim:strategos:{json_filename}"),
                     InlineKeyboardButton("🏛️ POLIS", callback_data=f"dim:polis:{json_filename}")],
                    [InlineKeyboardButton("❤️ PATHOS", callback_data=f"dim:pathos:{json_filename}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Send the result back
                reply_text = f"🎙️ **Transcrição:**\n\n{transcription}\n\n*Classifique este áudio para o Vault:*"
                await bot.send_message(
                    chat_id=chat_id, 
                    text=reply_text, 
                    reply_markup=reply_markup, 
                    parse_mode='Markdown'
                )
                logger.info(f"Successfully transcribed and mapped {filepath} to {json_filename}.")
                
            except asyncio.CancelledError:
                logger.info("Voice processing worker cancelled.")
                break
            except Exception as e:
                logger.error(f"Error processing voice queue task: {e}")
                if "bot" in locals() and "chat_id" in locals():
                    await bot.send_message(chat_id=chat_id, text="❌ Ocorreu um erro na transcrição do áudio com a Gemini API.")
            finally:
                # Optional Cleanup: Remove local file after successful processing
                keep_audio = os.getenv("TELEGRAM_KEEP_AUDIO", "false").lower() == "true"
                if not keep_audio:
                    try:
                        if os.path.exists(filepath):
                            os.remove(filepath)
                            logger.info(f"Deleted temporary audio file: {filepath}")
                    except Exception as e:
                        logger.warning(f"Failed to delete temporary audio {filepath}: {e}")

                self._voice_queue.task_done()

    async def dimensional_triage_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Sprint 10: Catch the inline keyboard presses for Voice triage classification.
        Saves the dominant 1.0 weight into the corresponding HeptatomoTensor JSON artifact.
        """
        query = update.callback_query
        await query.answer() # Acknowledge the callback internally
        
        data = query.data
        if not data.startswith("dim:"):
            return
            
        _, dimension, filename = data.split(":", 2)
        
        # Load JSON from vault
        try:
            import json
            from core.atomic_filesystem import atomic_fs
            from core.models import HeptatomoTensor
            
            content = atomic_fs.read_file(f"03_voice/{filename}")
            meta_dict = json.loads(content)
                
            # Assign binary triage weight
            tensor = HeptatomoTensor()
            setattr(tensor, dimension, 1.0)
            
            meta_dict["dimensional_tensor"] = tensor.model_dump()
            
            # Save atomically
            atomic_fs.write_file(f"03_voice/{filename}", json.dumps(meta_dict, indent=2))
            
            # Edit the message to visually lock in the classification
            original_text = query.message.text
            await query.edit_message_text(
                text=f"{original_text}\n\n✅ **Classificado no Tensor como:** {dimension.upper()}"
            )
        except Exception as e:
            logger.error(f"Dimensional Triage Error: {e}")
            await query.edit_message_text(text="❌ Erro: Arquivo de transcrição não encontrado ou falha na leitura no Vault.")

    async def test_format_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Test command to verify Telegram Markdown rendering.
        Usage: /test_format <text>
        """
        if not await self.verify_authorization(update):
            return

        if not context.args:
            await update.message.reply_text("Uso: /test_format <texto>")
            return

        text = " ".join(context.args)
        
        # Using standard Markdown parser for Telegram (Markdown)
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
            await update.message.reply_markdown(msg)
        except Exception as e:
            logger.error(f"Test format failed: {e}")
            await update.message.reply_text(f"❌ Formatting failed: {e}\n\nRaw text:\n{msg}")

    async def start_ptb(self):
        if not self.application:
            return
            
        await self.application.initialize()
        
        # Register Bot Commands to appear in the Telegram UI Menu
        try:
            await self.application.bot.set_my_commands([
                ("start", "Inicia o bot do ContentOS"),
                ("who_am_i", "Retorna seu ID de usuário para liberação"),
                ("test_format", "Testa a formatação markdown nativa")
            ])
            logger.info("Successfully registered bot commands in Telegram.")
        except Exception as e:
            logger.warning(f"Failed to set bot commands: {e}")
        
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
