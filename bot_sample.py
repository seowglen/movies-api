# bot.py
# pip install python-telegram-bot httpx
import os
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_URL = "http://127.0.0.1:8000"
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]


async def movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Try: /movie fantastic four tomorrow after 7pm for 2 people")
        return

    async with httpx.AsyncClient() as client:
        parsed = (await client.post(API_URL + "/parse", json={"query": query})).json()
        result = (await client.post(API_URL + "/search", json=parsed)).json()

    screenings = result["screenings"]
    if not screenings:
        await update.message.reply_text("No matching screenings found.")
        return

    best = screenings[0]
    seats = ", ".join(best["recommended_seats"]) or "No suitable group found"
    price = "$%.2f" % best["price"] if best["price"] is not None else "Price unavailable"

    await update.message.reply_text(
        "{movie}\n"
        "{cinema} — {datetime}\n"
        "{experience} | {price}\n"
        "Recommended: {seats}\n"
        "{url}".format(
            movie=best["movie"],
            cinema=best["cinema"],
            datetime=best["datetime"],
            experience=best["experience"],
            price=price,
            seats=seats,
            url=best["booking_url"],
        )
    )


app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("movie", movie))
app.run_polling()