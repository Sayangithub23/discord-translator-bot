'''Version 1
===================================================================================
'''

# import discord
# import asyncio
# import logging
# import requests
# import json
# import os
# from langdetect import detect_langs, LangDetectException
# from dotenv import load_dotenv
# load_dotenv()

# # ── Logging ───────────────────────────────────────────────────────────────────
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s  %(levelname)-8s  %(message)s",
#     datefmt="%H:%M:%S",
# )
# logger = logging.getLogger(__name__)

# # ─────────────────────────────────────────────────────────────────────────────
# # ⚙️  CONFIGURATION
# # ─────────────────────────────────────────────────────────────────────────────
# DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
# EMAILS = [
#     "account1@gmail.com",
#     "account2@gmail.com",
#     "account3@gmail.com",
#     "account4@gmail.com",
#     "account5@gmail.com",
#     "account6@gmail.com",
# ]

# CACHE_FILE = "translation_cache.json"   # saved to disk — survives restarts
# # ─────────────────────────────────────────────────────────────────────────────


# # ── Translation cache ─────────────────────────────────────────────────────────
# class TranslationCache:
#     """
#     Persistent disk-backed cache.
#     Key: "source_lang|target_lang|text_lowercase"
#     Value: translated string

#     Survives bot restarts — cache grows over time and saves more quota each day.
#     """
#     def __init__(self, path: str):
#         self.path = path
#         self._cache: dict[str, str] = {}
#         self._hits = 0
#         self._misses = 0
#         self._load()

#     def _load(self):
#         if os.path.exists(self.path):
#             try:
#                 with open(self.path, "r", encoding="utf-8") as f:
#                     self._cache = json.load(f)
#                 logger.info(f"📦 Cache loaded — {len(self._cache)} entries from disk")
#             except Exception as e:
#                 logger.warning(f"Cache load failed: {e} — starting fresh")
#                 self._cache = {}

#     def _save(self):
#         try:
#             with open(self.path, "w", encoding="utf-8") as f:
#                 json.dump(self._cache, f, ensure_ascii=False, indent=2)
#         except Exception as e:
#             logger.warning(f"Cache save failed: {e}")

#     def _key(self, text: str, source: str, target: str) -> str:
#         return f"{source}|{target}|{text.strip().lower()}"

#     def get(self, text: str, source: str, target: str) -> str | None:
#         result = self._cache.get(self._key(text, source, target))
#         if result:
#             self._hits += 1
#             logger.info(f"💾 Cache HIT ({self._hits} total hits): {text!r}")
#         else:
#             self._misses += 1
#         return result

#     def set(self, text: str, source: str, target: str, translation: str):
#         self._cache[self._key(text, source, target)] = translation
#         self._save()   # persist to disk immediately

#     @property
#     def stats(self) -> str:
#         total = self._hits + self._misses
#         rate = f"{self._hits/total*100:.0f}%" if total > 0 else "n/a"
#         return (
#             f"{len(self._cache)} entries | "
#             f"{self._hits} hits | "
#             f"{self._misses} misses | "
#             f"hit rate: {rate}"
#         )


# cache = TranslationCache(CACHE_FILE)


# # ── Email rotator ─────────────────────────────────────────────────────────────
# class EmailRotator:
#     def __init__(self, emails: list[str]):
#         self.emails = emails if emails else [""]
#         self.exhausted: set[str] = set()
#         self._index = 0

#     @property
#     def current(self) -> str:
#         if self.emails[self._index] not in self.exhausted:
#             return self.emails[self._index]
#         for i, email in enumerate(self.emails):
#             if email not in self.exhausted:
#                 self._index = i
#                 logger.info(f"Rotated to email slot {i + 1}/{len(self.emails)}")
#                 return email
#         return ""   # all exhausted — anonymous fallback

#     def mark_exhausted(self, email: str):
#         self.exhausted.add(email)
#         remaining = len(self.emails) - len(self.exhausted)
#         logger.warning(f"Slot exhausted — {remaining}/{len(self.emails)} remaining")

#     def reset(self):
#         self.exhausted.clear()
#         self._index = 0
#         logger.info("Daily quota reset — all email slots restored")

#     @property
#     def status(self) -> str:
#         available = len(self.emails) - len(self.exhausted)
#         return f"{available}/{len(self.emails)} email slots available"


# rotator = EmailRotator(EMAILS)


# # ── Language detection ────────────────────────────────────────────────────────
# def detect_language(text: str) -> str:
#     try:
#         langs = detect_langs(text)
#         for lang in langs:
#             if lang.lang in ("en", "fr"):
#                 logger.info(f"Detected: {lang.lang} (confidence: {lang.prob:.2f})")
#                 return lang.lang
#         return "en"
#     except LangDetectException:
#         return "en"


# # ── Translation ───────────────────────────────────────────────────────────────
# def translate(text: str, source: str, target: str) -> str:
#     """
#     Pipeline:
#       1. Check cache → return instantly if found
#       2. Call MyMemory API with email rotation
#       3. Store result in cache for next time
#     """
#     # ── Step 1: Cache check ───────────────────────────────────────────────────
#     cached = cache.get(text, source, target)
#     if cached:
#         return cached

#     # ── Step 2: API call with email rotation ──────────────────────────────────
#     max_attempts = len(rotator.emails) + 1

#     for attempt in range(max_attempts):
#         email = rotator.current
#         params = {"q": text, "langpair": f"{source}|{target}"}
#         if email:
#             params["de"] = email

#         try:
#             resp = requests.get(
#                 "https://api.mymemory.translated.net/get",
#                 params=params,
#                 timeout=10,
#             )
#             resp.raise_for_status()
#             data = resp.json()
#             status = data.get("responseStatus")
#             details = str(data.get("responseDetails", ""))

#             if status == 429 or "LIMIT" in details.upper():
#                 logger.warning(f"Quota hit on slot {attempt + 1} — rotating")
#                 if email:
#                     rotator.mark_exhausted(email)
#                 continue

#             if status != 200:
#                 raise Exception(f"MyMemory error {status}: {details}")

#             result = data["responseData"]["translatedText"]

#             # ── Step 3: Store in cache ────────────────────────────────────────
#             cache.set(text, source, target, result)
#             logger.info(f"✅ Translated + cached: {text!r} → {result!r}")
#             return result

#         except requests.RequestException as e:
#             raise Exception(f"Network error: {e}")

#     raise Exception("All email quotas exhausted for today — resets tomorrow")


# # ── Discord bot ───────────────────────────────────────────────────────────────
# intents = discord.Intents.default()
# intents.message_content = True
# intents.dm_messages = True
# intents.guild_messages = True

# bot = discord.Client(intents=intents)


# @bot.event
# async def on_ready():
#     user = bot.user
#     if user is None:
#         logger.error("Bot user is None — login failed")
#         return
#     logger.info(f"✅ Bot online: {user} (ID: {user.id})")
#     logger.info(f"🌐 Translator ready — {rotator.status}")
#     logger.info(f"📊 Daily capacity: ~{len(EMAILS) * 10_000:,} words/day")
#     logger.info(f"💾 Cache: {cache.stats}")

#     # Log cache stats every 30 minutes
#     async def _periodic_stats():
#         while True:
#             await asyncio.sleep(1800)
#             logger.info(f"💾 Cache stats: {cache.stats}")
#             logger.info(f"📡 Rotator: {rotator.status}")

#     # Reset email quotas every 24 hours
#     async def _daily_reset():
#         while True:
#             await asyncio.sleep(86400)
#             rotator.reset()

#     asyncio.create_task(_periodic_stats())
#     asyncio.create_task(_daily_reset())


# @bot.event
# async def on_message(message: discord.Message):
#     if message.author == bot.user:
#         return

#     text = message.content.strip()
#     if not text:
#         return

#     lang = detect_language(text)
#     target = "fr" if lang == "en" else "en"

#     logger.info(f"[{lang}→{target}] {text!r}")

#     try:
#         async with message.channel.typing():
#             translated = await asyncio.get_event_loop().run_in_executor(
#                 None, translate, text, lang, target
#             )

#         await message.reply(translated)

#     except discord.Forbidden:
#         logger.warning(f"Missing permissions in {message.channel}")
#     except Exception as e:
#         logger.error(f"Translation error: {e}")
#         await message.reply(f"⚠️ {e}")


# # ── Run ───────────────────────────────────────────────────────────────────────
# if __name__ == "__main__":
#     bot.run(DISCORD_TOKEN)


'''Version 2
==========================================================================================
'''

"""
bot.py — Discord Translator Bot
Reaction-based translation — react with a flag to translate.

Supported reactions:
  🇫🇷 → French
  🇸🇦 → Arabic
  🇬🇧 → English
  🇩🇪 → German
  🇪🇸 → Spanish

No auto-translation — clean chat, quota only used when needed.
"""

import discord
import asyncio
import logging
import requests
import json
import os
from dotenv import load_dotenv
load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# ⚙️  CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]

EMAILS = [
    "account1@gmail.com",
    "account2@gmail.com",
    "account3@gmail.com",
    "account4@gmail.com",
    "account5@gmail.com",
    "account6@gmail.com",
]

CACHE_FILE = "translation_cache.json"

# Flag emoji → MyMemory language code
FLAG_TO_LANG = {
    "🇫🇷": "fr",   # French
    "🇸🇦": "ar",   # Arabic
    "🇬🇧": "en",   # English
    "🇩🇪": "de",   # German
    "🇪🇸": "es",   # Spanish
    "🇮🇳": "hi",   # Hindi
    "🇧🇩": "bn",   # Bengali
    "🇯🇵": "ja",   # Japanese
    "🇨🇳": "zh",   # Chinese
    "🇵🇹": "pt",   # Portuguese
}

# Language code → human readable name
LANG_NAMES = {
    "fr": "French",
    "ar": "Arabic",
    "en": "English",
    "de": "German",
    "es": "Spanish",
    "hi": "Hindi",
    "bn": "Bengali",
    "ja": "Japanese",
    "zh": "Chinese",
    "pt": "Portuguese",
}
# ─────────────────────────────────────────────────────────────────────────────


# ── Translation cache ─────────────────────────────────────────────────────────
class TranslationCache:
    def __init__(self, path: str):
        self.path = path
        self._cache: dict[str, str] = {}
        self._hits = 0
        self._misses = 0
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                logger.info(f"📦 Cache loaded — {len(self._cache)} entries")
            except Exception as e:
                logger.warning(f"Cache load failed: {e}")
                self._cache = {}

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    def _key(self, text: str, target: str) -> str:
        return f"{target}|{text.strip().lower()}"

    def get(self, text: str, target: str) -> str | None:
        result = self._cache.get(self._key(text, target))
        if result:
            self._hits += 1
            logger.info(f"💾 Cache HIT: {text!r} → {target}")
        else:
            self._misses += 1
        return result

    def set(self, text: str, target: str, translation: str):
        self._cache[self._key(text, target)] = translation
        self._save()

    @property
    def stats(self) -> str:
        total = self._hits + self._misses
        rate = f"{self._hits/total*100:.0f}%" if total > 0 else "n/a"
        return f"{len(self._cache)} entries | {self._hits} hits | hit rate: {rate}"


cache = TranslationCache(CACHE_FILE)


# ── Email rotator ─────────────────────────────────────────────────────────────
class EmailRotator:
    def __init__(self, emails: list[str]):
        self.emails = emails if emails else [""]
        self.exhausted: set[str] = set()
        self._index = 0

    @property
    def current(self) -> str:
        if self.emails[self._index] not in self.exhausted:
            return self.emails[self._index]
        for i, email in enumerate(self.emails):
            if email not in self.exhausted:
                self._index = i
                logger.info(f"Rotated to email slot {i + 1}/{len(self.emails)}")
                return email
        return ""

    def mark_exhausted(self, email: str):
        self.exhausted.add(email)
        remaining = len(self.emails) - len(self.exhausted)
        logger.warning(f"Slot exhausted — {remaining}/{len(self.emails)} remaining")

    def reset(self):
        self.exhausted.clear()
        self._index = 0
        logger.info("Daily quota reset — all email slots restored")

    @property
    def status(self) -> str:
        available = len(self.emails) - len(self.exhausted)
        return f"{available}/{len(self.emails)} email slots available"


rotator = EmailRotator(EMAILS)


# ── Translation ───────────────────────────────────────────────────────────────
def translate(text: str, target: str) -> str:
    # Check cache first
    cached = cache.get(text, target)
    if cached:
        return cached

    max_attempts = len(rotator.emails) + 1

    for attempt in range(max_attempts):
        email = rotator.current
        params = {
            "q": text,
            "langpair": f"autodetect|{target}",   # auto detect source language
        }
        if email:
            params["de"] = email

        try:
            resp = requests.get(
                "https://api.mymemory.translated.net/get",
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("responseStatus")
            details = str(data.get("responseDetails", ""))

            if status == 429 or "LIMIT" in details.upper():
                logger.warning(f"Quota hit on slot {attempt + 1} — rotating")
                if email:
                    rotator.mark_exhausted(email)
                continue

            if status != 200:
                raise Exception(f"MyMemory error {status}: {details}")

            result = data["responseData"]["translatedText"]
            cache.set(text, target, result)
            logger.info(f"✅ Translated to {target}: {text!r} → {result!r}")
            return result

        except requests.RequestException as e:
            raise Exception(f"Network error: {e}")

    raise Exception("All quotas exhausted — resets tomorrow")


# ── Discord bot ───────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
intents.guild_messages = True
intents.reactions = True        # needed to detect emoji reactions


bot = discord.Client(intents=intents)


@bot.event
async def on_ready():
    user = bot.user
    if user is None:
        logger.error("Bot user is None — login failed")
        return
    logger.info(f"✅ Bot online: {user} (ID: {user.id})")
    logger.info(f"🌐 Reaction translator ready — {rotator.status}")
    logger.info(f"💾 Cache: {cache.stats}")
    logger.info(f"🏳️  Supported flags: {' '.join(FLAG_TO_LANG.keys())}")

    async def _periodic_stats():
        while True:
            await asyncio.sleep(1800)
            logger.info(f"💾 Cache: {cache.stats} | {rotator.status}")

    async def _daily_reset():
        while True:
            await asyncio.sleep(86400)
            rotator.reset()

    asyncio.create_task(_periodic_stats())
    asyncio.create_task(_daily_reset())


@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User | discord.Member):
    # Ignore bot's own reactions
    if user == bot.user:
        return

    emoji = str(reaction.emoji)

    # Check if it's a supported flag
    if emoji not in FLAG_TO_LANG:
        return

    target_lang = FLAG_TO_LANG[emoji]
    message = reaction.message
    text = message.content.strip()

    if not text:
        return

    lang_name = LANG_NAMES.get(target_lang, target_lang)
    logger.info(f"{user} reacted {emoji} → translating to {lang_name}: {text!r}")

    try:
        async with message.channel.typing():
            translated = await asyncio.get_event_loop().run_in_executor(
                None, translate, text, target_lang
            )

        # Reply to the original message with translation
        await message.reply(f"{emoji} **{lang_name}:** {translated}")

    except discord.Forbidden:
        logger.warning(f"Missing permissions in {message.channel}")
    except Exception as e:
        logger.error(f"Translation error: {e}")
        await message.reply(f"⚠️ {e}")


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)