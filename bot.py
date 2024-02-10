import json
import logging
import os
import time
from datetime import datetime

import feedparser
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

fh = logging.FileHandler('bot.log')
fh.setLevel(logging.INFO)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO,
    handlers=[fh, logging.StreamHandler()]
)

FEED_URL = 'https://www.aa.com.tr/tr/rss/default?cat=guncel'
group_chat_ids = set()
last_send_time = datetime.now()
if os.path.exists('state.json'):
    with open('state.json', 'r') as file:
        state = json.load(file)
        group_chat_ids = set(state['group_chat_ids'])
        last_send_time =  datetime.strptime(state['last_send_time'], '%Y-%m-%d %H:%M:%S')
else:
    with open('state.json', 'w') as file:
        state = {'group_chat_ids': list(group_chat_ids), 'last_send_time': last_send_time.strftime('%Y-%m-%d %H:%M:%S')}
        json.dump(state, file)

logging.info("Bot started...")
logging.info(f"Feed URL: {FEED_URL}")
logging.info(f"Group chat IDs: {group_chat_ids}")
logging.info(f"Last send time: {last_send_time}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Ben Haberci. Güncel haberleri almak için grubunuza ekleyin ve /haberver komutunu kullanın.')

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group_chat_ids.add(update.message.chat.id)
    await update.message.reply_text(f'Grubunuz başarıyla kaydedildi.')
    await send_news(context)
    logging.info(f"update.message.chat.id: {update.message.chat.id} added to group_chat_ids.")
    logging.info(f"{update.message.chat.title}")
    # save state to file
    with open('state.json', 'w') as file:
        state = {'group_chat_ids': list(group_chat_ids), 'last_send_time': last_send_time.strftime('%Y-%m-%d %H:%M:%S')}
        json.dump(state, file)
        logging.info(f"State saved to file: {state}")


async def send_news(context: ContextTypes.DEFAULT_TYPE) -> None:
    global last_send_time
    feed = feedparser.parse(FEED_URL)
    if len(feed.entries) == 0:
        logging.info(f"Feed is empty: {FEED_URL}")
        return
    for entry in feed.entries:
        published_time = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z').replace(tzinfo=None)
        if published_time > last_send_time:
            last_send_time = published_time
            for chat_id in group_chat_ids:
                await context.bot.send_message(chat_id=chat_id, text=entry['summary'] + "\n\n" + entry['link'])
        else:
            break

    logging.info(f"Last send time: {last_send_time}")
    # save state to file
    with open('state.json', 'w') as file:
        state = {'group_chat_ids': list(group_chat_ids), 'last_send_time': last_send_time.strftime('%Y-%m-%d %H:%M:%S')}
        json.dump(state, file)
        logging.info(f"State saved to file: {state}")

if __name__ == '__main__':
    app = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("haberver", register))
    app.job_queue.run_repeating(send_news, interval=60, first=0)

    app.run_polling(allowed_updates=Update.ALL_TYPES)
