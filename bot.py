import asyncio
import html
import json
import logging
import os
import traceback
from datetime import datetime

import feedparser
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.ext import filters
import requests

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
        last_send_time = datetime.strptime(state['last_send_time'], '%Y-%m-%d %H:%M:%S')
else:
    with open('state.json', 'w') as file:
        state = {'group_chat_ids': list(group_chat_ids), 'last_send_time': last_send_time.strftime('%Y-%m-%d %H:%M:%S')}
        json.dump(state, file)

logging.info("Bot started...")
logging.info(f"Feed URL: {FEED_URL}")
logging.info(f"Group chat IDs: {group_chat_ids}")
logging.info(f"Last send time: {last_send_time}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Ben Haberci. Güncel haberleri almak için /haberver komutunu kullanın.')


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat.id in group_chat_ids:
        await update.message.reply_text("Chat zaten kayıtlı.")
        return
    group_chat_ids.add(update.message.chat.id)
    await update.message.reply_text(f'Başarıyla kaydedildi. Yeni haberler geldikçe otomatik olarak gönderilecektir.')
    # await send_news(context)
    logging.info(f"update.message.chat.id: {update.message.chat.id} added to group_chat_ids.")
    logging.info(f"{update.message.chat.title}")
    logging.info(update.message.chat.invite_link)
    # save state to file
    with open('state.json', 'w') as file:
        state = {'group_chat_ids': list(group_chat_ids), 'last_send_time': last_send_time.strftime('%Y-%m-%d %H:%M:%S')}
        json.dump(state, file)
        logging.info(f"State saved to file: {state}")


async def unregister(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group_chat_ids.remove(update.message.chat.id)
    # await update.message.reply_text(f'Haberci ile burada tÄ±kÄ±lÄ±p kaldÄ±nÄ±z.')
    logging.info(f"update.message.chat.id: {update.message.chat.id} removed from group_chat_ids.")
    logging.info(f"{update.message.chat.title}")
    # save state to file
    with open('state.json', 'w') as file:
        state = {'group_chat_ids': list(group_chat_ids), 'last_send_time': last_send_time.strftime('%Y-%m-%d %H:%M:%S')}
        json.dump(state, file)
        logging.info(f"State saved to file: {state}")
    await update.message.reply_text(f'Chat başarıyla silindi. Haberler artık gönderilmeyecek.')


async def send_news(context: ContextTypes.DEFAULT_TYPE) -> None:
    global last_send_time
    feed = feedparser.parse(FEED_URL)
    if len(feed.entries) == 0:
        logging.info(f"Feed is empty: {FEED_URL}")
        return
    logging.info("Preparing to send news...")
    message_str = "📰 Geçtiğimiz saatte gündem:\n\n"
    msg_count = 0
    most_recent_time = last_send_time
    for entry in feed.entries:
        published_time = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z').replace(tzinfo=None)
        last_send_time = last_send_time.replace(tzinfo=None)
        if published_time > last_send_time:
            message_str += f"🔗 <a href='{entry.link}'>{entry.title}</a>\n\n"
            msg_count += 1
            if published_time > most_recent_time:
                most_recent_time = published_time
    last_send_time = most_recent_time
    message_str += "Haber kaynağı: <a href='https://www.aa.com.tr/tr'>Anadolu Ajansı</a>"

    if msg_count == 0:
        logging.info("No new news found.")
        return
    else:
        logging.info(f"New news count: {msg_count}")

    logging.info("Sending news...")

    for chat_id in group_chat_ids:
        try:
            msg = await context.bot.send_message(chat_id=chat_id, text=message_str, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            await context.bot.pin_chat_message(chat_id=chat_id, message_id=msg.message_id, disable_notification=False)
        except Exception as e:
            logging.error(f"Error while sending message to chat_id: {chat_id}, error: {e}")
            continue

    logging.info(f"Last send time: {last_send_time}")
    # save state to file
    with open('state.json', 'w') as file:
        state = {'group_chat_ids': list(group_chat_ids), 'last_send_time': last_send_time.strftime('%Y-%m-%d %H:%M:%S')}
        json.dump(state, file)
        logging.info(f"State saved to file: {state}")

async def feedback_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_info = ""
    try:
        user_info = f"User: {update.message.from_user.username}, {update.message.from_user.first_name}, {update.message.from_user.last_name}, Chat ID: {update.message.chat.id}"
    except Exception as e:
        user_info = "User info not found."
    await context.bot.send_message(
        chat_id=os.environ['DEV_CHAT_ID'], text="Feedback received: " + update.message.text + "\n\n" + user_info
    )

# async def error_raise(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
#     await context.bot.wrong_method_name()

async def send_notification(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.info("Notification command received.")
    logging.info(f"update.message.chat.id: {update.message.chat.id}")
    if update.message.chat.id == int(os.environ['DEV_CHAT_ID']):
        txt = update.message.text.replace("/bildirim", "")
        for chat_id in group_chat_ids:
            try:
                await context.bot.send_message(chat_id=chat_id, text=txt)
                await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"Notification failed for chat ID: {chat_id}")
                continue

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error("Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    # Finally, send the message
    await context.bot.send_message(
        chat_id=os.environ['DEV_CHAT_ID'], text=message, parse_mode=ParseMode.HTML
    )

if __name__ == '__main__':
    resp = requests.get(f"https://api.telegram.org/bot{os.environ['NEWS_BOT_TOKEN']}/getUpdates?offset=-1")
    if resp.status_code == 200:
        logging.info("Bot messages reset.")
    else:
        logging.error("Bot messages reset failed.")

    app = ApplicationBuilder().token(os.environ["NEWS_BOT_TOKEN"]).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("haberver", register))
    app.add_handler(CommandHandler("haberverme", unregister))
    app.add_handler(CommandHandler("feedback", feedback_handler))
    app.add_handler(CommandHandler("bildirim", send_notification))
    # app.add_handler(CommandHandler("error", error_raise))

    app.add_error_handler(error_handler)
    app.job_queue.run_repeating(send_news, interval=3600)

    app.run_polling(allowed_updates=Update.ALL_TYPES)
