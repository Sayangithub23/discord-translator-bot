"""
providers.py — Translation provider implementations
Each provider exposes a single method: translate(text, source_lang, target_lang) -> str
"""

import requests
import time
import logging

logger = logging.getLogger(__name__)


class TranslationError(Exception):
    """Raised when a provider fails to translate."""
    pass


class QuotaExceededError(TranslationError):
    """Raised when a provider's quota is exhausted."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# DeepL Free
# ─────────────────────────────────────────────────────────────────────────────
class DeepLProvider:
    """
    DeepL Free Tier — 500,000 chars/month
    Sign up: https://www.deepl.com/pro#developer
    API key ends in ':fx' for free accounts.
    """
    NAME = "DeepL"
    MONTHLY_QUOTA = 500_000

    LANG_MAP = {"en": "EN", "fr": "FR"}

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api-free.deepl.com/v2/translate"

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        src = self.LANG_MAP.get(source_lang, source_lang.upper())
        tgt = self.LANG_MAP.get(target_lang, target_lang.upper())

        resp = requests.post(
            self.url,
            data={
                "auth_key": self.api_key,
                "text": text,
                "source_lang": src,
                "target_lang": tgt,
            },
            timeout=10,
        )

        if resp.status_code == 456:
            raise QuotaExceededError("DeepL monthly quota exceeded")
        if resp.status_code == 403:
            raise TranslationError("DeepL: invalid API key")
        resp.raise_for_status()

        data = resp.json()
        return data["translations"][0]["text"]


# ─────────────────────────────────────────────────────────────────────────────
# LibreTranslate (public instance)
# ─────────────────────────────────────────────────────────────────────────────
class LibreTranslateProvider:
    """
    LibreTranslate — free public instance at libretranslate.com
    No key required for basic usage (rate limited).
    Self-host for unlimited: https://github.com/LibreTranslate/LibreTranslate
    """
    NAME = "LibreTranslate"
    MONTHLY_QUOTA = float("inf")  # rate-limited, not quota-limited

    def __init__(self, url: str = "https://libretranslate.com", api_key: str = ""):
        self.url = url.rstrip("/")
        self.api_key = api_key

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        payload = {
            "q": text,
            "source": source_lang,
            "target": target_lang,
            "format": "text",
        }
        if self.api_key:
            payload["api_key"] = self.api_key

        resp = requests.post(
            f"{self.url}/translate",
            json=payload,
            timeout=15,
        )

        if resp.status_code == 429:
            raise QuotaExceededError("LibreTranslate rate limit hit")
        if resp.status_code == 403:
            raise TranslationError("LibreTranslate: forbidden — may need an API key")
        resp.raise_for_status()

        data = resp.json()
        if "translatedText" not in data:
            raise TranslationError(f"LibreTranslate unexpected response: {data}")
        return data["translatedText"]


# ─────────────────────────────────────────────────────────────────────────────
# MyMemory (Google-backed, free)
# ─────────────────────────────────────────────────────────────────────────────
class MyMemoryProvider:
    """
    MyMemory — free, 5k chars/day anonymous | 10k chars/day with email
    No sign-up required for anonymous use.
    """
    NAME = "MyMemory"
    MONTHLY_QUOTA = float("inf")  # daily limit, not monthly

    def __init__(self, email: str = ""):
        self.email = email  # optional, doubles the daily quota

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        params = {
            "q": text,
            "langpair": f"{source_lang}|{target_lang}",
        }
        if self.email:
            params["de"] = self.email

        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()

        data = resp.json()
        status = data.get("responseStatus")

        if status == 429 or "LIMIT" in str(data.get("responseDetails", "")).upper():
            raise QuotaExceededError("MyMemory daily quota exceeded")
        if status != 200:
            raise TranslationError(f"MyMemory error {status}: {data.get('responseDetails')}")

        return data["responseData"]["translatedText"]
