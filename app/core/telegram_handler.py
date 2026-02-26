import os
import logging
import asyncio
from typing import List
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from fastapi import Request

logger = logging.getLogger(__name__)

class TelegramHandler:
    def __init__(self):
        self.application: Application = None
        self.authorized_users: List[int] = []
        self._is_polling = False
        
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
        await update.message.reply_text(f"Olá, {user.first_name}! Eu sou o ContentOS bot. Envie-me textos para transformá-los em Markdown seeds.")

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

    async def start_ptb(self):
        if not self.application:
            return
            
        await self.application.initialize()
        
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
