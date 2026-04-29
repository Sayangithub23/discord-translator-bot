# Discord Translator Bot — EN↔FR

A free, persistent Discord translator bot with caching, email rotation,
and automatic failover. Works in servers and DMs.

---

## Architecture

```
Discord message (server or DM)
        │
        ▼
 langdetect (EN or FR?)
        │
        ▼
 Check translation cache
        │
   ┌────┴────┐
  HIT       MISS
   │           │
return      MyMemory API
instantly   (email rotation)
  ⚡             │
            save to cache
                │
            reply to user
```

### Email rotation (quota management)

```
Email slot 1 active → hits 10k limit
        ↓
Email slot 2 activates → hits 10k limit
        ↓
Email slot 3 activates → ...
        ↓
All exhausted → anonymous fallback (5k/day)
        ↓
24 hours pass → all slots reset automatically
```

---

## Current Stack

| Component          | Tool              | Cost               |
| ------------------ | ----------------- | ------------------ |
| Discord bot        | discord.py        | Free               |
| Translation        | MyMemory API      | Free, no card      |
| Language detection | langdetect        | Free, runs locally |
| Cache              | JSON file on disk | Free, persistent   |

> DeepL and LibreTranslate were removed — DeepL requires a card,
> LibreTranslate public instance is no longer free.

---

## Daily Capacity

| Setup     | Words/day |
| --------- | --------- |
| No email  | 5,000     |
| 1 email   | 10,000    |
| 6 emails  | 60,000    |
| 10 emails | 100,000   |

For a private conversation between 2 people, 5,000 words/day
is more than enough. Cache hits don't count toward quota.

---

## Files

```
Discord Bot/
├── bot.py                   Main bot — all logic in one file
├── manager.py               Provider rotation (future use)
├── providers.py             Provider classes (future use)
├── requirements.txt         Python dependencies
├── translation_cache.json   Auto-created on first run, persists forever
└── README.md
```

---

## Setup

### 1. Install dependencies

```bash
pip install discord.py requests langdetect
```

### 2. Create a Discord bot

- Go to https://discord.com/developers/applications
- New Application → Bot → Reset Token → Copy token
- Enable **Message Content Intent** under Privileged Gateway Intents
- Save Changes

### 3. Invite bot to your server

- OAuth2 → URL Generator
- Scope: `bot`
- Permissions: `Send Messages` + `Read Message History` + `Embed Links`
- Open generated URL → invite to server

### 4. Configure bot.py

```python
DISCORD_TOKEN = "your token here"

EMAILS = [
    "fake1@example.com",   # MyMemory never verifies emails
    "fake2@example.com",   # fake emails work fine for privacy
    "fake3@example.com",
]
```

### 5. Run

```bash
python bot.py
```

---

## Hosting Options

| Option                    | Cost            | 24/7             | Difficulty |
| ------------------------- | --------------- | ---------------- | ---------- |
| **Old Android + Termux**  | ✅ Free forever | ✅ Yes           | Easy       |
| **Oracle Cloud Free VM**  | ✅ Free forever | ✅ Yes           | Medium     |
| **Your PC**               | ✅ Free         | ❌ PC must be on | Very easy  |
| Railway / Render / Fly.io | ⚠️ Limited free | ✅ Yes           | Easy       |

**Recommended**: Old Android phone running Termux — free forever,
no card needed, 24/7 uptime.

### Android (Termux) setup

```bash
# Install Termux from F-Droid (not Play Store)
pkg update
pkg install python tmux termux-boot
pip install discord.py requests langdetect

# Run bot persistently
tmux new -s bot
python bot.py
# Ctrl+B then D to detach
```

Android settings required:

```
Settings → Apps → Termux → Battery → Unrestricted
Settings → Developer Options → Stay awake while charging ✅
```

---

## Cache

Translations are saved to `translation_cache.json` automatically.

- Survives bot restarts
- Grows smarter every day
- Cache hits use zero API quota and respond instantly
- Common phrases (hello, good morning, thank you) cached after first use

```json
{
  "en|fr|hello": "Bonjour",
  "en|fr|good morning": "Bonjour matin",
  "fr|en|salut comment allez-vous": "Hi how are you"
}
```

---

## Limits & Gotchas

- `langdetect` may misfire on very short texts (1 word) — defaults to English
- Misspelled words may not detect correctly — normal limitation
- MyMemory daily quota resets at midnight UTC
- Cache resets if bot folder is deleted — keep `translation_cache.json` safe
- On Android — don't swipe away Termux from recent apps

---

## Adding More Languages (future)

Currently supports EN↔FR only. To add more languages:

1. Update `detect_language()` to include new language codes
2. Add routing logic in `on_message()` for new language pairs
3. MyMemory supports 50+ languages — no extra setup needed
