import logging
import re
import os
import asyncio
from dotenv import load_dotenv
import paramiko
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

import psycopg2
from psycopg2 import sql

load_dotenv()

logging.basicConfig(
    filename='bot.log',
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO
)

EMAIL_INPUT, PHONE_INPUT, CONFIRM_EMAIL_SAVE, CONFIRM_PHONE_SAVE, PASSWORD, APT_PACKAGE, DB_ACTION = range(7)

def ssh_exec(command: str, timeout: int = 8) -> str:
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=os.getenv("RM_HOST"),
            port=int(os.getenv("RM_PORT", 22)),
            username=os.getenv("RM_USER"),
            password=os.getenv("RM_PASSWORD"),
            timeout=timeout
        )
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        client.close()
        result = (output or error or "Нет данных").strip()
        return result if len(result) <= 4000 else result[:3997] + ""
    except Exception as e:
        return f"Ошибка SSH: {str(e)[:150]}"

async def send_monitoring_result(update: Update, command: str, msg: str = "Выполняю запрос"):
    await update.message.reply_text(f"{msg}")
    out = await asyncio.to_thread(ssh_exec, command)
    await update.message.reply_text(out)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f'Привет, {user.full_name}!'
    )
    await update.message.reply_text(
        "Доступные команды:\n"
        "/find_email\n/find_phone_number\n/verify_password\n\n"
        "Команды мониторинга:\n"
        "/get_release\n/get_uname\n/get_uptime\n/get_df\n/get_free\n/get_mpstat\n/get_w\n/get_auths\n/get_critical\n/get_ps\n/get_ss\n/get_apt_list\n/get_services\n\n"
        "Команды взаимодействия с базой данных\n"
        "/get_repl_logs\n/get_emails\n/get_phone_numbers\n"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("HELP! -> /start")

async def find_email_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пришлите текст для поиска email:")
    return EMAIL_INPUT

async def find_phone_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пришлите текст для поиска номеров телефонов:")
    return PHONE_INPUT

async def verify_password_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пришлите пароль для проверки сложности:")
    return PASSWORD

async def handle_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if not emails:
        await update.message.reply_text("Email не найдены")
        return ConversationHandler.END
    result = "\n".join(f"{i+1}. {e}" for i, e in enumerate(emails))
    await update.message.reply_text(f"Найдены email:\n{result}\n\nСохранить в базу данных? (y/n)")
    context.user_data['emails_to_save'] = emails
    return CONFIRM_EMAIL_SAVE

async def confirm_email_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.strip().lower()
    if answer in ['да', 'yes', 'y', 'д']:
        emails = context.user_data.get('emails_to_save', [])
        msg = await asyncio.to_thread(db_insert_emails, emails)
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("Сохранение отменено")
    return ConversationHandler.END

async def handle_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    pattern = r'(?:\+7|8)[\s\-()]*(\d{3})[\s\-()]*(\d{3})[\s\-]?(\d{2})[\s\-]?(\d{2})'
    matches = re.findall(pattern, text)
    if not matches:
        await update.message.reply_text("Номера телефонов не найдены")
        return ConversationHandler.END
    numbers = [f"+7{a}{b}{c}{d}" for a, b, c, d in matches]
    result = "\n".join(f"{i+1}. {n}" for i, n in enumerate(numbers))
    await update.message.reply_text(f"Найдены номера:\n{result}\n\nСохранить в базу данных? (y/n)")
    context.user_data['phones_to_save'] = numbers
    return CONFIRM_PHONE_SAVE

async def confirm_phone_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.strip().lower()
    if answer in ['да', 'yes', 'y', 'д']:
        phones = context.user_data.get('phones_to_save', [])
        msg = await asyncio.to_thread(db_insert_phones, phones)
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("Сохранение отменено")
    return ConversationHandler.END

async def handle_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pwd = update.message.text
    if (len(pwd) >= 8 and
        re.search(r'[A-Z]', pwd) and
        re.search(r'[a-z]', pwd) and
        re.search(r'\d', pwd) and
        re.search(r'[!@#$%^&*()]', pwd)):
        await update.message.reply_text("Пароль сложный")
    else:
        await update.message.reply_text("Пароль простой")
    return ConversationHandler.END

async def get_release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_monitoring_result(update, "cat /etc/os-release | head -n 5", "Информация о релизе")

async def get_uname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_monitoring_result(update, "uname -a", "Данные системы")

async def get_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_monitoring_result(update, "uptime", "Время работы")

async def get_df(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_monitoring_result(update, "df -h", "Файловая система")

async def get_free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_monitoring_result(update, "free -h", "Оперативная память")

async def get_mpstat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_monitoring_result(update, "mpstat", "Производительность")

async def get_w(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_monitoring_result(update, "w", "Список активных пользователей")

async def get_auths(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_monitoring_result(update, "last -n 10", "Последние входы")

async def get_critical(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_monitoring_result(update, "journalctl -p crit -n 5 --no-pager", "Критические события")

async def get_ps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_monitoring_result(update, "ps aux | head -n 20", "Процессы")

async def get_ss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_monitoring_result(update, "ss -tuln", "Используемые порты")

async def get_apt_list_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название пакета или 'all' для списка пакетов:")
    return APT_PACKAGE

async def handle_apt_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pkg = update.message.text.strip()
    await update.message.reply_text("Информация о пакетах")
    if pkg.lower() == "all":
        cmd = "dpkg -l"
    else:
        cmd = f"apt show {pkg} 2>/dev/null || echo 'Пакет не найден'"
    out = await asyncio.to_thread(ssh_exec, cmd)
    await update.message.reply_text(out)
    return ConversationHandler.END

async def get_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_monitoring_result(update, "systemctl list-units --type=service --state=running --no-pager | head -n 20", "Запущенные сервисы")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Неизвестная команда. /start")

async def get_repl_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Логи репликации PostgreSQL")
    cmd = "ls /var/log/postgresql/postgresql-*.log 2>/dev/null | sort | tail -n1"
    log_file = await asyncio.to_thread(ssh_exec, cmd)
    if not log_file.strip() or "No such file" in log_file:
        await update.message.reply_text("Логи PostgreSQL не найдены")
        return
    log_file = log_file.strip()
    grep_cmd = f"grep -i 'replication\\|standby\\|ready' {log_file} | tail -n 20"
    out = await asyncio.to_thread(ssh_exec, grep_cmd)
    if not out.strip():
        out = "Логи репликации не обнаружены"
    await update.message.reply_text(out[:4000])

def db_query(query: str) -> str:
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_DATABASE"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if not rows:
            return "Нет данных"
        result = "\n".join(f"{i+1}. {row[0]}" for i, row in enumerate(rows))
        return result[:4000]
    except Exception as e:
        logging.error(f"DB error: {e}")
        return f"Ошибка БД: {str(e)[:150]}"

async def get_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Еmail из БД")
    query = "SELECT email FROM emails ORDER BY id DESC LIMIT 20;"
    out = await asyncio.to_thread(db_query, query)
    await update.message.reply_text(out)

async def get_phone_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Номера телефонов из БД")
    query = "SELECT phone FROM phone_numbers ORDER BY id DESC LIMIT 20;"
    out = await asyncio.to_thread(db_query, query)
    await update.message.reply_text(out)

def db_insert_emails(emails: list) -> str:
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_DATABASE"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        cur = conn.cursor()
        for email in emails:
            cur.execute("INSERT INTO emails (email) VALUES (%s) ON CONFLICT DO NOTHING;", (email,))
        conn.commit()
        cur.close()
        conn.close()
        return f"Успешно сохранено {len(emails)} email"
    except Exception as e:
        logging.error(f"DB insert error: {e}")
        return f"Ошибка записи email: {str(e)[:150]}"

def db_insert_phones(phones: list) -> str:
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_DATABASE"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        cur = conn.cursor()
        for phone in phones:
            cur.execute("INSERT INTO phone_numbers (phone) VALUES (%s) ON CONFLICT DO NOTHING;", (phone,))
        conn.commit()
        cur.close()
        conn.close()
        return f"Успешно сохранено {len(phones)} номеров"
    except Exception as e:
        logging.error(f"DB insert error: {e}")
        return f"Ошибка записи номеров: {str(e)[:150]}"




def main():
    token = os.getenv("TOKEN")
    if not token:
        raise ValueError("TOKEN не найден в .env")

    required = ["RM_HOST", "RM_PORT", "RM_USER", "RM_PASSWORD"]
    for var in required:
        if not os.getenv(var):
            logging.warning(f"Переменная {var} отсутствует в .env")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    app.add_handler(ConversationHandler(
    entry_points=[CommandHandler("find_email", find_email_start)],
    states={
        EMAIL_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email_input)],
        CONFIRM_EMAIL_SAVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_email_save)]
    },
    fallbacks=[]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("find_phone_number", find_phone_start)],
        states={
            PHONE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone_input)],
            CONFIRM_PHONE_SAVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_phone_save)]
        },
        fallbacks=[]
    ))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("verify_password", verify_password_start)],
        states={PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password_input)]},
        fallbacks=[]
    ))

    app.add_handler(CommandHandler("get_release", get_release))
    app.add_handler(CommandHandler("get_uname", get_uname))
    app.add_handler(CommandHandler("get_uptime", get_uptime))
    app.add_handler(CommandHandler("get_df", get_df))
    app.add_handler(CommandHandler("get_free", get_free))
    app.add_handler(CommandHandler("get_mpstat", get_mpstat))
    app.add_handler(CommandHandler("get_w", get_w))
    app.add_handler(CommandHandler("get_auths", get_auths))
    app.add_handler(CommandHandler("get_critical", get_critical))
    app.add_handler(CommandHandler("get_ps", get_ps))
    app.add_handler(CommandHandler("get_ss", get_ss))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("get_apt_list", get_apt_list_start)],
        states={APT_PACKAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_apt_input)]},
        fallbacks=[]
    ))
    app.add_handler(CommandHandler("get_services", get_services))

    app.add_handler(CommandHandler("get_repl_logs", get_repl_logs))
    app.add_handler(CommandHandler("get_emails", get_emails))
    app.add_handler(CommandHandler("get_phone_numbers", get_phone_numbers))

    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    app.run_polling()

if __name__ == "__main__":
    main()
