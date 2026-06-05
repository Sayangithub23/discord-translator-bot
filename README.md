# Discord Translator Bot — Reaction Based Multi-Language

A free, persistent Discord translator bot. React with a flag emoji to
translate any message into that language. No auto-translation — clean
chat, quota only used when needed.

---

## How it works

```
Someone sends "Good morning"
        │
        │  No auto-translation — chat stays clean
        │
        ▼
French friend reacts 🇫🇷
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
Bot replies: "🇫🇷 French: Bonjour"
```

### Email rotation (quota management)

```
Email slot 1 active → hits 10k limit
        ↓
Email slot 2 activates → hits 10k limit
        ↓
...
        ↓
All exhausted → anonymous fallback (5k/day)
        ↓
24 hours pass → all slots reset automatically
```

---

## Supported Flag Reactions

| Flag | Language   |
| ---- | ---------- |
| 🇫🇷   | French     |
| 🇸🇦   | Arabic     |
| 🇬🇧   | English    |
| 🇩🇪   | German     |
| 🇪🇸   | Spanish    |
| 🇮🇳   | Hindi      |
| 🇧🇩   | Bengali    |
| 🇯🇵   | Japanese   |
| 🇨🇳   | Chinese    |
| 🇵🇹   | Portuguese |

Adding more languages: just add a new line to `FLAG_TO_LANG` in `bot.py`.

---

## Current Stack

| Component   | Tool              | Cost             |
| ----------- | ----------------- | ---------------- |
| Discord bot | discord.py        | Free             |
| Translation | MyMemory API      | Free, no card    |
| Cache       | JSON file on disk | Free, persistent |

> DeepL and LibreTranslate were removed — DeepL requires a card,
> LibreTranslate public instance is no longer free.
> langdetect removed — source language auto-detected by MyMemory.

---

## Daily Capacity

| Setup     | Words/day |
| --------- | --------- |
| No email  | 5,000     |
| 1 email   | 10,000    |
| 6 emails  | 60,000    |
| 10 emails | 100,000   |

Cache hits don't count toward quota — repeated phrases are free.

---

## Files

```
Discord Bot/
├── bot.py                   Main bot — all logic in one file
├── manager.py               Provider rotation (future use)
├── providers.py             Provider classes (future use)
├── requirements.txt         Python dependencies
├── translation_cache.json   Auto-created on first run, persists forever
├── .env                     Your Discord token — never share this
├── .gitignore               Keeps .env off GitHub
└── README.md
```

---

## Setup

### 1. Install dependencies

```bash
pip install discord.py requests python-dotenv
```

### 2. Create a Discord bot

- Go to https://discord.com/developers/applications
- New Application → Bot → Reset Token → Copy token
- Enable these under Privileged Gateway Intents:
  - ✅ Server Members Intent
  - ✅ Message Content Intent
- Save Changes

### 3. Invite bot to your server

- OAuth2 → URL Generator
- Scope: `bot`
- Permissions: `Send Messages` + `Read Message History` + `Embed Links` + `Add Reactions`
- Open generated URL → invite to server

### 4. Create .env file

```
DISCORD_TOKEN=your_token_here
```

### 5. Configure emails in bot.py

```python
EMAILS = [
    "fake1@example.com",   # MyMemory never verifies emails
    "fake2@example.com",   # fake emails work fine for privacy
    "fake3@example.com",
]
```

### 6. Run

```bash
python bot.py
```

---

## Hosting — Android + Termux (Recommended)

Free forever, no card, 24/7 uptime. Works on any old Android phone.

```bash
# 1. Install Termux from F-Droid (NOT Play Store)
# 2. Inside Termux:
pkg update && pkg upgrade
pkg install python git tmux termux-boot
pip install discord.py requests python-dotenv

# 3. Clone repo
git clone https://github.com/Sayangithub23/discord-translator-bot.git
cd discord-translator-bot

# 4. Create .env
echo "DISCORD_TOKEN=your_token_here" > .env

# 5. Run persistently
tmux new -s bot
python bot.py
# Volume Down + B, then D to detach
```

### Required Android settings

```
Settings → Apps → Termux → Battery → Unrestricted
Settings → Apps → Termux → Background activity → Allow
Settings → Developer Options → Stay awake while charging ✅
```

### Updating the bot

```bash
# On PC — push changes
git add .
git commit -m "your message"
git push

# On phone — pull changes
cd discord-translator-bot
git pull
python bot.py
```

---

## Other Hosting Options

| Option                    | Cost            | 24/7             | Difficulty |
| ------------------------- | --------------- | ---------------- | ---------- |
| **Old Android + Termux**  | ✅ Free forever | ✅ Yes           | Easy       |
| **Oracle Cloud Free VM**  | ✅ Free forever | ✅ Yes           | Medium     |
| **Your PC**               | ✅ Free         | ❌ PC must be on | Very easy  |
| Railway / Render / Fly.io | ⚠️ Limited free | ✅ Yes           | Easy       |

---

## Cache

Translations are saved to `translation_cache.json` automatically.

- Survives bot restarts
- Grows smarter every day
- Cache hits use zero API quota and respond instantly

```json
{
  "fr|good morning": "Bonjour",
  "ar|hello": "مرحبا",
  "es|thank you": "Gracias"
}
```

---

## Limits & Gotchas

- MyMemory daily quota resets at midnight UTC
- Cache resets if bot folder is deleted — keep `translation_cache.json` safe
- On Android — don't swipe away Termux from recent apps
- Bot needs to be in a mutual server to receive DMs
- Reactions only work on messages the bot can see (needs Read Message History)
