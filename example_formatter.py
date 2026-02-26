import re
import html
import asyncio
import logging

logger = logging.getLogger(__name__)

# --- REGEX PATTERNS (Pre-compiled for performance) ---
# Blocks and Structures
RE_BLOCK_CODE = re.compile(r'```(?:[a-zA-Z]+)?\n?(.*?)```', flags=re.DOTALL)
RE_BLOCKQUOTE = re.compile(r'(^|\n)>\s*(.*)')
RE_HEADERS = re.compile(r'(^|\n)#{1,6}\s+(.*)')
RE_LIST_ITEMS = re.compile(r'(^|\n)\s*[-*+]\s+(.*)')

# Inline Formatting with Boundary Protection (Protects commands like /who_am_i)
RE_BOLD_ITALIC = re.compile(r'(^|(?<=\s))(\*\*\*|___)(?!\s)(.*?)(?<!\s)\2($|(?=\s|[.,!?;:]))')
RE_BOLD = re.compile(r'(^|(?<=\s))(\*\*|__)(?!\s)(.*?)(?<!\s)\2($|(?=\s|[.,!?;:]))')
RE_ITALIC_STAR = re.compile(r'(^|(?<=\s))(?<!\*)\*(?!\*)(.*?)(?<!\*)\*($|(?=\s|[.,!?;:]))')
RE_ITALIC_UNDERSCORE = re.compile(r'(^|(?<=\s))(?<!_)_(?!_)(.*?)(?<!_)_($|(?=\s|[.,!?;:]))')
RE_INLINE_CODE = re.compile(r'`([^`]+)`')
RE_LINKS = re.compile(r'\[(.*?)\]\((.*?)\)')
RE_STRIKE = re.compile(r'(^|(?<=\s))~~(?!\s)(.*?)(?<!\s)~~($|(?=\s|[.,!?;:]))')

def markdown_to_telegram_html_sync(text: str) -> str:
    """
    Core formatting engine. Escapes HTML and applies Markdown rules.
    Sync version to be run in a separate thread.
    """
    # 1. Security: Escape original HTML tags
    text = html.escape(text)

    # 2. Block Elements
    text = RE_BLOCK_CODE.sub(r'<pre><code>\1</code></pre>', text)
    text = RE_BLOCKQUOTE.sub(r'\1<blockquote>\2</blockquote>', text)
    text = RE_HEADERS.sub(r'\1<b>\2</b>', text)
    text = RE_LIST_ITEMS.sub(r'\1 • \2', text)

    # 3. Inline Elements
    text = RE_BOLD_ITALIC.sub(r'\1<b><i>\3</i></b>', text)
    text = RE_BOLD.sub(r'\1<b>\3</b>', text)
    text = RE_ITALIC_STAR.sub(r'\1<i>\2</i>', text)
    text = RE_ITALIC_UNDERSCORE.sub(r'\1<i>\2</i>', text)
    text = RE_INLINE_CODE.sub(r'<code>\1</code>', text)
    text = RE_LINKS.sub(r'<a href="\2">\1</a>', text)
    text = RE_STRIKE.sub(r'\1<s>\2</s>', text)

    return text.strip()

async def safe_markdown_to_html(text: str, timeout: float = 2.0) -> str:
    """
    Asynchronous wrapper with strict timeout. 
    Protects the bot against ReDoS or complex pattern hangs.
    """
    if not text:
        return ""

    try:
        # Runs the heavy regex task in a thread to keep the event loop free
        return await asyncio.wait_for(
            asyncio.to_thread(markdown_to_telegram_html_sync, text),
            timeout = timeout
        )
    except asyncio.TimeoutError:
        logger.error(f"PARSER TIMEOUT: Markdown processing exceeded {timeout}s.")
        # Fallback: Return safely escaped text with a warning
        return f"⚠️ <b>Parser Warning:</b> Message too complex for formatting.\n\n{html.escape(text)}"
    except Exception as e:
        logger.error(f"PARSER ERROR: {str(e)}", exc_info=True)
        return html.escape(text)