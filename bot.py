import logging
import os
import pyotp
import qrcode
import re
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv

# Настройка логгирования
logging.basicConfig(
    level=logging.WARNING,  # Уровень WARNING (только предупреждения и ошибки)
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Отключаем логи httpx (HTTP-запросы)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Отключаем логи python-telegram-bot (INFO-сообщения)
logging.getLogger("telegram").setLevel(logging.WARNING)

# Загружаем переменные из .env
load_dotenv()

# Проверка наличия переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
if BOT_TOKEN is None:
    raise ValueError("Переменная окружения BOT_TOKEN не найдена в .env.")

ADMIN_IDS = os.getenv('ADMIN_IDS')
if ADMIN_IDS is None:
    raise ValueError("Переменная окружения ADMIN_IDS не найдена в .env.")
ADMIN_IDS = [int(id) for id in ADMIN_IDS.split(',')]

# Полный список стоп-слов (русские, английские и матерные)
STOP_WORDS_RU = [
    "работа", "вакансии", "реклама", "скидка", "выиграй", "приз", "деньги", "заработок", 
    "инвестиции", "партнёрка", "реферальная", "доход", "онлайн", "оффлайн", "бизнес", 
    "проект", "услуги", "срочно", "кэшбэк", "ставки", "казино", "играть", "выигрыш", 
    "джекпот", "рулетка", "покер", "лотерея", "турнир", "приложение", "скачать", 
    "регистрация", "зарегистрируйся", "вход", "логин", "пароль", "аккаунт", "профиль", 
    "пополнить", "вывод", "перевод", "оплата", "карта", "кошелёк", "крипта", "биткоин", 
    "эфир", "токен", "майнинг", "ферма", "обмен", "курс", "валюта", "доллар", "рубль", 
    "евро", "займ", "кредит", "ипотека", "рассрочка", "долг", "финансы", "банк", "счёт", 
    "интернет", "сайт", "платформа", "сервис", "рассылка", "новости", "статья", "блог", 
    "курс", "обучение", "тренинг", "вебинар", "мастер-класс", "коучинг", "наставник", 
    "эксперт", "специалист", "профессия", "карьера", "резюме", "опыт", "заявка", "анкета", 
    "форма", "опрос", "тест", "проверка", "успех", "мотивация", "цель", "мечта", "план", 
    "стратегия", "схема", "секрет", "метод", "техника", "программа", "система", "бот", 
    "скрипт", "код", "разработка", "дизайн", "логотип", "бренд", "компания", "фирма", 
    "стартап", "инновация", "технология", "гаджет", "устройство", "прибор", "ремонт", 
    "инструкция", "руководство", "документы", "договор", "соглашение", "условия", "правила", 
    "политика", "конфиденциальность", "безопасность", "защита", "гарант", "стабильность", 
    "прогноз", "тренд", "анализ", "статистика", "отчёт", "график", "таблица", "диаграмма", 
    "рост", "прибыль", "оборот", "поток", "клиенты", "аудитория", "трафик", "лиды", 
    "конверсия", "маркетинг", "таргет", "контекст", "seo", "продвижение", "раскрутка", 
    "рекламодатель", "бюджет", "вложения", "окупаемость", "рентабельность", "пасссивный", 
    "активный", "удалённо", "офис", "график", "смены", "задачи", "процесс", "этапы", 
    "шаги", "решение", "проблема", "вызов", "конкурс", "соревнование", "активация", 
    "промокод", "код", "ссылка", "переход", "клик", "подключение", "доступ", "пакет", 
    "тариф", "абонемент", "членство", "чат"
]

BAD_WORDS_RU = [
    "блять", "сука", "пиздец", "хуй", "ебать", "ебаный", "пидор", "гандон", "мудак", "долбоёб", 
    "уёбок", "тварь", "сучка", "хуёво", "пизда", "жопа", "нахуй", "ебало", "залупа", "пиздеж", 
    "говно", "срать", "дерьмо", "бля", "шлюха", "потаскуха", "пидорас", "хуесос", "еблан", 
    "дебил", "идиот", "кретин", "урод", "выродок", "придурок", "отморозок", "чмо", "скотина", 
    "козёл", "баран", "тупой", "глупый", "тормоз", "позор", "гнида", "падла", "сволочь", "гад"
]

STOP_WORDS_EN = [
    "work", "job", "buy", "sell", "order", "delivery", "free", "discount", "promo", "advertising", 
    "win", "prize", "money", "earn", "invest", "referral", "partner", "income", "online", "business", 
    "cash", "bonus", "gift", "quick", "easy", "casino", "bet", "play", "jackpot", "lottery", 
    "signup", "register", "login", "payment", "withdraw", "bitcoin", "crypto", "trading", "profit", 
    "course", "training", "webinar", "coach", "expert", "service", "platform", "app", "download", 
    "link", "click"
]

# Общий список стоп-слов
STOP_WORDS = STOP_WORDS_RU + STOP_WORDS_EN + BAD_WORDS_RU

# Регулярное выражение для поиска ссылок
LINK_PATTERN = re.compile(
    r'(?:https?:\/\/|www\.|ftp\.|t\.me\/|@|bit\.ly\/|tinyurl\.com\/|goo\.gl\/|ow\.ly\/|t\.co\/|'
    r'bit\.do\/|buff\.ly\/|adf\.ly\/|shorte\.st\/|cutt\.us\/|u\.to\/|tiny\.cc\/|is\.gd\/|v\.gd\/|'
    r'cli\.gs\/|qr\.ae\/|tr\.im\/|vur\.me\/|bc\.vc\/|twitthis\.com\/|su\.pr\/|snipurl\.com\/|'
    r'ity\.im\/|short\.ie|sh\.com|lnkd\.in|fwd4\.me|prettylinkpro\.com|bl\.ink|dlvr\.it|'
    r'[\w\-]+\.(com|ru|org|net|me|io|co|uk|de|fr|es|it|nl|pl|info|biz|online|xyz|site|blog|shop|store))'
)

# Словарь для хранения секретных ключей администраторов
admin_secrets = {}

# Словарь для хранения состояния подтверждения 2FA
admin_verified = {}

# Генерация секретного ключа для администратора
def generate_secret_key(user_id):
    secret = pyotp.random_base32()  # Генерация случайного секретного ключа
    admin_secrets[user_id] = secret
    return secret

# Создание URI для добавления в Google Authenticator
def generate_google_authenticator_uri(user_id, secret):
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=f"Admin_{user_id}",  # Имя администратора
        issuer_name="AntiSpamBot"  # Название бота
    )

# Проверка кода Google Authenticator
def verify_google_authenticator_code(user_id, code):
    if user_id not in admin_secrets:
        return False
    secret = admin_secrets[user_id]
    totp = pyotp.TOTP(secret)
    return totp.verify(code)

# Проверка, что пользователь является администратором
def is_admin(user_id):
    return user_id in ADMIN_IDS

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        if not is_admin(user_id):
            await update.message.reply_text("🚫 Этот бот доступен только администраторам.")
            return

        # Если секретный ключ отсутствует, запускаем /setup_2fa
        if user_id not in admin_secrets:
            await setup_2fa(update, context)
        else:
            await update.message.reply_text(
                "🤖 Я бот-антиспам! Помогаю держать нашу дружную команду в чистоте! 🧹\n\n"
                "📖 Ознакомьтесь с правилами: /ruls",
                parse_mode='Markdown'
            )
    except Exception as e:
        logging.error(f"Ошибка в функции start: {e}")
        await update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже.")

# Обработчик команды /setup_2fa (для настройки Google Authenticator)
async def setup_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        if not is_admin(user_id):
            await update.message.reply_text("🚫 Эта команда доступна только администраторам!")
            return

        # Генерация секретного ключа
        secret = generate_secret_key(user_id)

        # Создание URI для Google Authenticator
        uri = generate_google_authenticator_uri(user_id, secret)

        # Отправка инструкций администратору
        await update.message.reply_text(
            "🔐 Настройте двухфакторную аутентификацию (2FA) с помощью Google Authenticator:\n\n"
            f"1. Откройте Google Authenticator.\n"
            f"2. Нажмите '+' и выберите 'Сканировать QR-код'.\n"
            f"3. Отсканируйте QR-код ниже или введите ключ вручную:\n\n"
            f"Ключ: `{secret}`\n\n"
            f"4. Введите код из Google Authenticator для подтверждения.",
            parse_mode='Markdown'
        )

        # Генерация и отправка QR-кода
        img = qrcode.make(uri)
        bio = BytesIO()
        img.save(bio, format="PNG")
        bio.seek(0)
        await context.bot.send_photo(chat_id=user_id, photo=bio, caption="QR-код для Google Authenticator")
    except Exception as e:
        logging.error(f"Ошибка в функции setup_2fa: {e}")
        await update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже.")

# Обработчик текстовых сообщений (для ввода кода Google Authenticator)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        if not is_admin(user_id):
            await update.message.reply_text("🚫 Этот бот доступен только администраторам.")
            return

        text = update.message.text

        # Проверяем, ожидается ли код 2FA от этого пользователя
        if user_id in admin_secrets and user_id not in admin_verified:
            if verify_google_authenticator_code(user_id, text):
                admin_verified[user_id] = True  # Пользователь подтвердил 2FA
                await update.message.reply_text("✅ Код подтверждён! Теперь вы можете выполнять команды.")
            else:
                await update.message.reply_text("❌ Неверный код. Попробуйте ещё раз.")
            return

        # Если 2FA подтверждена, выполняем команды
        if user_id in admin_verified and admin_verified[user_id]:
            # Проверка на стоп-слова, мат и ссылки
            detected_stop_word = next((word for word in STOP_WORDS if word in text.lower()), None)
            has_link = LINK_PATTERN.search(text)

            if detected_stop_word or has_link:
                # Удаляем сообщение
                await update.message.delete()

                # Формируем сообщение о нарушении
                if detected_stop_word:
                    if detected_stop_word in BAD_WORDS_RU:
                        violation_reason = f"🚫 Обнаружено оскорбление или мат: *{detected_stop_word}*!"
                    else:
                        violation_reason = f"🚫 Обнаружено стоп-слово: *{detected_stop_word}*!"
                else:
                    detected_link = has_link.group(0)
                    violation_reason = f"🚫 Ссылка: *{detected_link}*!"

                # Отправляем предупреждение пользователю
                violation_warning = (
                    f"🛡️ *ВНИМАНИЕ! Обнаружено нарушение!* 🛡️\n\n"
                    f"{violation_reason}\n"
                    "❌ Ваше сообщение удалено.\n"
                    "🙅‍♂️ Пожалуйста, больше не нарушайте правила!\n"
                    "🧱 Повторные нарушения приведут к блокировке!\n\n"
                    "📖 Ознакомьтесь с правилами: /ruls"
                )
                keyboard = [[InlineKeyboardButton("Сообщить об ошибке ⚠️", callback_data=f"report_{update.message.from_user.id}_{text[:50]}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=violation_warning,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )

                # Уведомляем администратора
                user = update.message.from_user
                admin_text = (
                    f"⚠️ *Обнаружено нарушение!* ⚠️\n\n"
                    f"👤 Пользователь: {user.first_name} (ID: {user.id})\n"
                    f"📝 Сообщение: `{text}`\n"
                    f"🔗 Нарушение: {violation_reason}\n"
                    f"⏰ Время: {update.message.date}\n\n"
                    f"ℹ️ Нажмите 'Заблокировать', чтобы навсегда исключить пользователя из чата.\n"
                    f"📖 Ознакомьтесь с правилами: /ruls"
                )
                keyboard = [[InlineKeyboardButton("Заблокировать 🚫", callback_data=f"ban_{user.id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                for admin_id in ADMIN_IDS:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=admin_text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
    except Exception as e:
        logging.error(f"Ошибка в функции handle_text: {e}")
        await update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже.")

# Обработчик нажатия кнопки "Заблокировать"
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        # Проверяем, является ли пользователь администратором
        if query.from_user.id not in ADMIN_IDS:
            await query.edit_message_text("🚫 У вас нет прав для выполнения этой операции!")
            return

        # Получаем ID пользователя, которого нужно заблокировать
        user_id = int(query.data.split('_')[1])
        chat_id = query.message.chat_id

        # Выполняем вечный бан пользователя в чате
        await context.bot.ban_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            revoke_messages=True  # Удаляет все сообщения пользователя в чате
        )
        await query.edit_message_text(
            text=f"✅ Пользователь (ID: {user_id}) заблокирован навсегда! 🚫\n\n"
                 f"📖 Ознакомьтесь с правилами: /ruls",
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Ошибка в функции ban_user: {e}")
        await query.edit_message_text("Произошла ошибка. Пожалуйста, попробуйте позже.")

# Обработчик нажатия кнопки "Сообщить об ошибке"
async def report_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        data = query.data.split('_')
        user_id = int(data[1])
        reported_text = '_'.join(data[2:])  # Собираем остаток текста сообщения

        # Уведомляем администратора об ошибке
        report_text = (
            f"⚠️ *Сообщение об ошибке определения спама* ⚠️\n\n"
            f"👤 Пользователь: {query.from_user.first_name} (ID: {user_id})\n"
            f"📝 Сообщение: `{reported_text}`\n"
            f"⏰ Время: {query.message.date}\n\n"
            "ℹ️ Пожалуйста, проверьте и внесите корректировки в список стоп-слов, если необходимо."
        )
        
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(
                chat_id=admin_id,
                text=report_text,
                parse_mode='Markdown'
            )
        
        # Подтверждаем пользователю, что ошибка отправлена
        await query.edit_message_text(
            text=f"✅ Ваше сообщение об ошибке отправлено администратору для проверки!\n\n📖 Ознакомьтесь с правилами: /ruls",
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Ошибка в функции report_error: {e}")
        await query.edit_message_text("Произошла ошибка. Пожалуйста, попробуйте позже.")

# Обработчик команды /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        if not is_admin(user_id):
            await update.message.reply_text("🚫 Эта команда доступна только администраторам!")
            return

        help_text = (
            "🛠 *Команды настройки бота (для админов)* 🛠\n\n"
            "🔹 */start* - Запустить бота и получить приветствие 🤖\n"
            "🔹 */setup_2fa* - Настроить двухфакторную аутентификацию (2FA) 🔐\n"
            "🔹 */help* - Показать список команд настройки (вы здесь) ℹ️\n\n"
            "ℹ️ Для выполнения административных команд требуется двухфакторная аутентификация (2FA)."
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Ошибка в функции help_command: {e}")
        await update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже.")

# Основная функция
def main():
    try:
        application = Application.builder().token(BOT_TOKEN).build()

        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("setup_2fa", setup_2fa))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        application.add_handler(CallbackQueryHandler(ban_user, pattern=r"ban_\d+"))
        application.add_handler(CallbackQueryHandler(report_error, pattern=r"report_\d+_.+"))

        # Запускаем бота
        print("🤖 Бот запущен! 🌟")
        application.run_polling()
    except Exception as e:
        logging.error(f"Ошибка в функции main: {e}")

if __name__ == '__main__':
    main()