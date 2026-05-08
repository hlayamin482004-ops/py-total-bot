import asyncio
import os
import re

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from dotenv import load_dotenv

from parser import parse_message

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN မရှိပါ (Railway Variables ထဲထည့်ပါ)")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# =====================
# 🔥 MARKET LIST & PERCENTAGE
# =====================
MARKETS = {
    "du": ["du", "dubai", "ဒူ", "ဒူဘိုင်း"],
    "me": ["me", "mega", "မီ", "မီဂါ"],
    "max": ["maxi", "max", "မက်ဆီ", "မက်စီ", "စီစီ"],
    "glo": ["glo", "global", "ဂလို"],
    "ld": ["ld", "london", "landon", "လန်ဒန်", "လန်လန်"],
    "lao": ["lao", "laos", "loadon", "laodon", "လာအို", "လာလာ"],
    "mm": ["mm", "MM"],
}

# မင်းအစောပိုင်းပြောထားတဲ့ % အတိုင်း
PERCENT = {
    "du": 7,
    "me": 7,
    "max": 7,
    "glo": 3,
    "ld": 7,
    "lao": 7,
    "mm": 10,
}

SEPS_CLASS = r"[ \t,\-*/=.:]"


def _contains_token(text: str, token: str) -> bool:
    t = text.lower()
    k = token.lower()

    # ASCII token with boundary for short ones (du/me/mm/ld)
    if re.fullmatch(r"[a-z0-9]+", k):
        if len(k) <= 2:
            return re.search(rf"(?:^|{SEPS_CLASS}){re.escape(k)}(?:$|{SEPS_CLASS})", t) is not None
        return k in t

    # Burmese: simple contains
    return k in t


def detect_markets(text: str):
    """
    - provider keyword မပါတာဆို []
    - mm က digits ပါမှ accept
    - ၂ မျိုး以上 ပါရင် list ၂ ခု以上
    """
    t = text.lower()
    has_digits = re.search(r"\d", t) is not None

    found = []
    for key, aliases in MARKETS.items():
        if key == "mm" and not has_digits:
            continue
        for a in aliases:
            if _contains_token(t, a):
                found.append(key)
                break

    # unique keep order
    seen = set()
    uniq = []
    for x in found:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


async def mention_owner_and_admins(message: Message) -> str:
    admins = await message.chat.get_administrators()
    targets = [a for a in admins if a.status in ("creator", "administrator")]

    parts = []
    for a in targets[:10]:
        u = a.user
        if u.username:
            parts.append(f"@{u.username}")
        else:
            name = " ".join([x for x in [u.first_name, u.last_name] if x])
            parts.append(f'<a href="tg://user?id={u.id}">{name}</a>')

    return " ".join(parts)


@dp.message()
async def handle(message: Message):
    text = message.text or ""

    # ❌ no number → ignore
    if not re.search(r"\d", text):
        return

    markets = detect_markets(text)

    # ✅ Provider keyword မပါတာဆို bot မပြန်
    if len(markets) == 0:
        return

    user_name = message.from_user.first_name or "User"

    # ✅ Provider ၂ မျိုး以上 ပါရင် owner/admin mention + စစ်ခိုင်း
    if len(markets) >= 2:
        mention = await mention_owner_and_admins(message)
        msg = f"{mention}\n⚠️ {user_name} ရဲ့ဒါလေးလာစစ်ပေးပါရှင့်"
        return await message.reply(msg, parse_mode="HTML", disable_web_page_preview=True)

    market = markets[0]
    percent = PERCENT.get(market, 7)

    data = parse_message(text)
    total_amount = int(data["grand_total"])
    if total_amount <= 0:
        return

    cashback = round(total_amount * (percent / 100))
    net = total_amount - cashback

    reply = (
        f"👤 {user_name}\n"
        f"--------------------\n"
        f"စုစုပေါင်း = {total_amount:,} ကျပ်\n"
        f"{percent}% Cashback = {cashback:,} ကျပ်\n"
        f"--------------------\n"
        f"လက်ခံရမည့်ငွေ = {net:,} ကျပ်\n"
        f"ဘဲ လွဲပါရှင့်\n"
        f"--------------------\n"
        f"ကံကောင်းပါစေ"
    )

    await message.reply(reply)


async def main():
    # 24/7 run (Railway)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
                                   
