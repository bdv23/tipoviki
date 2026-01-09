import logging
import re
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

BOT_TOKEN = "8584353184:AAG2A8lVGJSi8bys-JFYJRNJKmb6I1ASYQI"
# RM_HOST = rm_host - будет содержать удаленный хост, который будем мониторить
# RM_PORT = rm_port - будет содержать порт удаленного хоста, к которому будем подключаться
# RM_USER = rm_user - будет содержать пользователя удаленного хоста
# RM_PASSWORD = rm_password - будет содержать пароль пользователя удаленного хоста
# DB_USER = db_user - будет содержать пользователя базы данных удаленного хоста
# DB_PASSWORD = db_password - будет содержать пароль пользователя базы данных удаленного хоста
# DB_HOST = db_host - будет содержать хост(имя контейнера), в котором будет работать база данных
# DB_PORT = db_port - будет содержать порт, на котором работает база данных
# DB_DATABASE = db_database - будет содержать имя базы данных
# DB_REPL_USER = db_repl_user - будет содержать пользователя реплицируемой базы данных
# DB_REPL_PASSWORD = db_repl_password - будет содержать пароль пользователя реплицируемой базы данных
# DB_REPL_HOST = db_repl_host - будет содержать хост(имя контейнера), в котором будет работать реплицируемая база данных
# DB_REPL_PORT = db_repl_port - будет содержать порт, на котором работает реплицируемая база данных


logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

PHONE_INPUT = 0

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f'Привет, {user.full_name}!'
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("HELP!")

async def cmd_find_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Вставь текст, в котором нужно найти номера:")
    return PHONE_INPUT

async def process_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    pattern = r"(?:\+7|8)[\s\-()]*(\d{3})[\s\-()]*(\d{3})[\s\-]?(\d{2})[\s\-]?(\d{2})"
    matches = re.findall(pattern, text)

    if not matches:
        await update.message.reply_text("Номера не обнаружены.")
        return ConversationHandler.END

    numbers = [f"8 ({a}) {b}-{c}-{d}" for a, b, c, d in matches]
    response = "\n".join(f"{i}. {n}" for i, n in enumerate(numbers, 1))
    await update.message.reply_text(response)
    return ConversationHandler.END

async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Не понял. Используй /findphone или /help.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    phone_conv = ConversationHandler(
        entry_points=[CommandHandler("findphone", cmd_find_phone)],
        states={PHONE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_phone_input)]},
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(phone_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown))

    app.run_polling()

if __name__ == "__main__":
    main()
