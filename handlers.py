import re
import json
import os

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import CallbackContext

from config import ADMIN_CHAT_ID
from states import (
    MAIN_MENU,
    IMPORTER_COUNTRY,
    IMPORTER_AMOUNT,
    IMPORTER_CURRENCY,
    IMPORTER_COMMISSION_CHOICE,
    IMPORTER_INN,
    IMPORTER_PURPOSE,
    IMPORTER_PHONE,
    IMPORTER_PREVIEW,

    EXPORTER_COUNTRY,
    EXPORTER_AMOUNT,
    EXPORTER_CURRENCY,
    EXPORTER_PURPOSE,
    EXPORTER_COMMISSION_CHOICE,
    EXPORTER_SENDER_DETAILS,
    EXPORTER_RECEIVER_DETAILS,
    EXPORTER_PHONE,
    EXPORTER_PREVIEW,

    PHYSICAL_CHOICES,
    PHYSICAL_COUNTRY,
    PHYSICAL_AMOUNT,
    PHYSICAL_CURRENCY,
    PHYSICAL_COMMISSION_CHOICE,
    PHYSICAL_PHONE,
    PHYSICAL_PREVIEW,

    AGENT_SUBMENU,
    AGENT_IMPORTER_COUNTRY,
    AGENT_IMPORTER_AMOUNT,
    AGENT_IMPORTER_CURRENCY,
    AGENT_IMPORTER_COMMISSION_CHOICE,
    AGENT_IMPORTER_INN,
    AGENT_IMPORTER_PURPOSE,
    AGENT_IMPORTER_PHONE,
    AGENT_IMPORTER_PREVIEW,

    AGENT_EXPORTER_COUNTRY,
    AGENT_EXPORTER_AMOUNT,
    AGENT_EXPORTER_CURRENCY,
    AGENT_EXPORTER_PURPOSE,
    AGENT_EXPORTER_COMMISSION_CHOICE,
    AGENT_EXPORTER_SENDER_DETAILS,
    AGENT_EXPORTER_RECEIVER_DETAILS,
    AGENT_EXPORTER_PHONE,
    AGENT_EXPORTER_PREVIEW
)

import json
import os

def get_exchange_rate(key: str) -> float:
    """
    Reads the latest exchange rate from the JSON file.
    Returns None if file doesn't exist or key not found.
    """
    try:
        with open("exchange_rates.json", "r") as f:
            data = json.load(f)
            rate = data.get(key)
            return float(rate) if rate is not None else None
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return None

def calculate_commission(amount_usd: float, usd_rate: float) -> (float, str):
    """
    Given the amount in USD and the USD→RUB rate, determine the commission percentage and message.
    For amounts below 5000, returns an error message.
    (For the 5% bracket, if the computed commission in RUB is below 100,000, then the minimum applies.)
    """
    if amount_usd < 5000:
        return None, "The minimum transfer amount is 5000 USD."
    # If amount is less than 50,000 USD, use 5% (with minimum 100,000 RUB)
    if amount_usd < 50000:
        commission_percent = 5.0
        commission_rub = amount_usd * usd_rate * (commission_percent / 100)
        if commission_rub < 100000:
            message = "5% commission (minimum 100,000 RUB)"
        else:
            message = "5% commission"
    elif 50000 <= amount_usd < 100000:
        commission_percent = 3.5
        message = "3.5% commission"
    elif 100000 <= amount_usd < 500000:
        commission_percent = 3.0
        message = "3% commission"
    else:  # amount_usd >= 500000
        commission_percent = 2.5
        message = "2.5% commission"
    return commission_percent, message


#
# -------------------------------------------------------------------
# Validation helpers
# -------------------------------------------------------------------
#

def is_valid_text(text: str) -> bool:
    """
    Checks if text contains only letters/spaces/hyphens (for e.g. countries, names).
    """
    pattern = r'^[A-Za-zА-Яа-я\s-]+$'
    return bool(re.match(pattern, text.strip()))

def is_valid_number(text: str) -> bool:
    """
    Checks if the input is a valid integer or decimal number (e.g. 123 or 123.45).
    """
    pattern = r'^\d+(\.\d+)?$'
    return bool(re.match(pattern, text.strip()))

def is_valid_currency(text: str) -> bool:
    """
    Checks if the input is typically 3-5 letters (e.g. USD, EUR, AED, etc.).
    """
    pattern = r'^[A-Za-z]{3,5}$'
    return bool(re.match(pattern, text.strip()))

def is_valid_phone(text: str) -> bool:
    """
    Checks if the input is a phone number (7-15 digits, optional leading +).
    """
    pattern = r'^\+?\d{7,15}$'
    return bool(re.match(pattern, text.strip()))


#
# -------------------------------------------------------------------
# Minimal translation helper
# -------------------------------------------------------------------
#

def get_user_lang(context: CallbackContext) -> str:
    return context.user_data.get("lang", "ru")

def set_user_lang(context: CallbackContext, lang: str) -> None:
    context.user_data["lang"] = lang

def update_bot_commands(context: CallbackContext) -> None:
    context.bot.set_my_commands([
        BotCommand("start",     "Начать / Start"),
        BotCommand("menu",      "Главное меню / Main menu"),
        BotCommand("cancel",    "Отменить / Cancel"),
        BotCommand("about",     "О боте / About"),
        BotCommand("help",      "Помощь / Help"),
        BotCommand("contact",   "Связаться / Contact us"),
        BotCommand("faq",       "Частые вопросы / FAQ"),
        BotCommand("language",  "Выбрать язык / Choose language")
    ])

def _(key: str, lang: str) -> str:
    """
    Minimal translation dictionary
    """
    texts = {
        ("start_intro", "ru"): (
            "👋 Добро пожаловать!\n\n"
            "🤝 Что может этот бот?\n"
            "   💳 Помощь в оплате товаров и услуг за рубежом\n"
            "   🌍 Помощь в переводе собственных средств за рубеж и из-за рубежа\n"
            "   💱 Возврат экспортной выручки\n\n"
        ),
        ("start_intro", "en"): (
            "👋 Welcome!\n\n"
            "🤝 What can this bot do?\n"
            "   💳 Help with paying for goods and services abroad\n"
            "   🌍 Help transferring your own funds abroad and from abroad\n"
            "   💱 Return of export proceeds\n\n"
        ),
        ("greeting", "ru"): "🌐 Привет! Я ваш персональный помощник для международных платежей.",
        ("greeting", "en"): "🌐 Hello! I'm your personal assistant for international payments.",
        ("main_menu_label", "ru"): (
            "\n🏠 Главное меню:\n\n"
            "1️⃣ Импортер - оплата товаров и услуг\n"
            "2️⃣ Экспортер - возврат выручки\n"
            "3️⃣ Физ лицо - личные переводы\n"
            "4️⃣ Агент - партнерская программа\n\n"
        ),
        ("main_menu_label", "en"): (
            "\n🏠 Main Menu:\n\n"
            "1️⃣ Importer - pay for goods & services\n"
            "2️⃣ Exporter - revenue returns\n"
            "3️⃣ Individual - personal transfers\n"
            "4️⃣ Agent - partnership program\n\n"
        ),
        ("about_text", "ru"): (
            "ℹ️ О нашем сервисе:\n\n"
            "🌐 Международные переводы и платежи:\n"
            "- Помощь импортерам с оплатой товаров и услуг\n"
            "- Поддержка экспортеров с возвратом выручки\n"
            "- Переводы для физических лиц (индивидуальные условия)\n\n"
            "💼 Для бизнеса:\n"
            "- Оптимизация международных платежей\n"
            "- Быстрые и надежные транзакции\n"
            "- Профессиональная поддержка\n\n"
            "👥 Для частных лиц:\n"
            "- Переводы себе за границу\n"
            "- Переводы родственникам\n"
            "- Оплата зарубежных услуг\n\n"
            "📱 Свяжитесь с нами через бот для получения персональных условий!"
        ),
        ("about_text", "en"): (
            "ℹ️ About our service:\n\n"
            "🌐 International Transfers & Payments:\n"
            "- Help importers pay for goods and services\n"
            "- Support exporters with revenue returns\n"
            "- Individual transfers (custom conditions)\n\n"
            "💼 For Business:\n"
            "- International payment optimization\n"
            "- Fast and secure transactions\n"
            "- Professional support\n\n"
            "👥 For Individuals:\n"
            "- Self transfers abroad\n"
            "- Transfers to relatives\n"
            "- Payment for foreign services\n\n"
            "📱 Contact us through the bot for personalized conditions!"
        ),
        ("language_prompt", "ru"): "🌐 Выберите язык:",
        ("language_prompt", "en"): "🌐 Choose your language:",
        ("importer_country", "ru"): "🌍 Введите страну получателя:",
        ("importer_country", "en"): "🌍 Enter recipient country:",
        ("enter_amount", "ru"): "💰 Введите сумму:",
        ("enter_amount", "en"): "💰 Enter amount:",
        ("commission_2", "ru"): "Комиссия: от 2%. Продолжить?",
        ("commission_2", "en"): "Commission: from 2%. Continue?",
        ("exporter_country", "ru"): "🌍 Введите страну отправителя:",
        ("exporter_country", "en"): "🌍 Enter sender's country:",
        ("commission_15", "ru"): "Комиссия: от 1.5%. Продолжить?",
        ("commission_15", "en"): "Commission: from 1.5%. Continue?",
        ("connect_manager", "ru"): "👨‍💼 Комиссия индивидуальна для каждой страны. Связаться с менеджером?",
        ("connect_manager", "en"): "👨‍💼 Commission is individual for each country. Connect with a manager?",
    }

    return texts.get((key, lang), f"[MISSING TEXT {key}_{lang}]")

def yes_no_keyboard(lang: str) -> ReplyKeyboardMarkup:
    if lang == "en":
        return ReplyKeyboardMarkup([["Yes", "No"]], one_time_keyboard=True, resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True, resize_keyboard=True)

def get_main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    if lang == "en":
        buttons = [["Importer", "Exporter"], ["Individual", "Agent"]]
    else:
        buttons = [["Импортер", "Экспортер"], ["Физ лицо", "Агент"]]

    return ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)

#
# -------------------------------------------------------------------
# Reusable functions
# -------------------------------------------------------------------
#

def go_back_to_main_menu(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    update.message.reply_text(
        _("main_menu_label", lang),
        reply_markup=get_main_menu_keyboard(lang)
    )
    return MAIN_MENU

#
# -------------------------------------------------------------------
# /start, /about, /language & MAIN MENU
# -------------------------------------------------------------------
#

def start(update: Update, context: CallbackContext) -> int:
    update_bot_commands(context)
    if "lang" not in context.user_data:
        set_user_lang(context, "ru")  # default

    lang = get_user_lang(context)
    intro_text = _("start_intro", lang)
    greeting   = _("greeting", lang)

    update.message.reply_text(f"{intro_text}{greeting}", reply_markup=ReplyKeyboardRemove())
    update.message.reply_text(_("main_menu_label", lang), reply_markup=get_main_menu_keyboard(lang))
    return MAIN_MENU

def main_menu(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    choice = update.message.text.lower().strip()

    # synonyms RU/EN
    if any(word in choice for word in ["импортер", "importer"]):
        update.message.reply_text(_( "importer_country", lang ), reply_markup=ReplyKeyboardRemove())
        return IMPORTER_COUNTRY

    elif any(word in choice for word in ["экспортер", "exporter"]):
        update.message.reply_text(_("exporter_country", lang), reply_markup=ReplyKeyboardRemove())
        return EXPORTER_COUNTRY

    elif any(word in choice for word in ["физ", "individual"]):
        # Physical submenu
        if lang == "en":
            reply_keyboard = [
                ["Transfer to self", "Transfer to relative"],
                ["Pay for services", "Back to menu"]
            ]
            prompt_text = "What do you want to do?"
        else:
            reply_keyboard = [
                ["Перевод себе за границу", "Перевод родственнику"],
                ["Оплата услуг", "Назад в главное меню"]
            ]
            prompt_text = "Выберите, что вы хотите сделать:"

        update.message.reply_text(
            prompt_text,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return PHYSICAL_CHOICES

    elif any(word in choice for word in ["агент", "agent"]):
        # Show agent submenu
        if lang == "en":
            text = ("Agent Options:\n\n"
                    "1. Make the payment\n"
                    "2. Forex rebate")
            keyboard = [["1", "2"]]
        else:
            text = ("Опции Агента:\n\n"
                    "1. Произвести оплату\n"
                    "2. Вернуть валютную выручку")
            keyboard = [["1", "2"]]

        context.user_data["agent_choice"] = None  # reset
        update.message.reply_text(
            text,
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return AGENT_SUBMENU

    else:
        update.message.reply_text(_( "main_menu_label", lang ), reply_markup=get_main_menu_keyboard(lang))
        return MAIN_MENU

def about_command(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    update.message.reply_text(_("about_text", lang), reply_markup=ReplyKeyboardRemove())
    return MAIN_MENU

def language_command(update: Update, context: CallbackContext) -> None:
    lang = get_user_lang(context)
    kb = [[
        InlineKeyboardButton("🇷🇺 Русский", callback_data="set_lang_ru"),
        InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en")
    ]]
    update.message.reply_text(_("language_prompt", lang),
                              reply_markup=InlineKeyboardMarkup(kb))

def language_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    data = query.data
    if data == "set_lang_en":
        set_user_lang(context, "en")
        confirmation = "Language set to English."
    else:
        set_user_lang(context, "ru")
        confirmation = "Язык переключен на Русский."

    query.edit_message_text(confirmation)
    lang = get_user_lang(context)
    query.message.reply_text(_("main_menu_label", lang), reply_markup=get_main_menu_keyboard(lang))

#
# -------------------------------------------------------------------
# AGENT FLOW
# Submenu => user picks 1 or 2 => Then we do a custom Importer/Exporter flow for Agents
# -------------------------------------------------------------------
#

def agent_submenu(update: Update, context: CallbackContext) -> int:
    """
    Here we see if user picks '1' => Agent Importer flow
                      or '2' => Agent Exporter flow
    """
    lang = get_user_lang(context)
    choice = update.message.text.strip()

    if choice == "1":
        context.user_data["agent_choice"] = "make_payment"  # import-like
        if lang == "en":
            update.message.reply_text("🌍 Enter the recipient country:", reply_markup=ReplyKeyboardRemove())
        else:
            update.message.reply_text("🌍 Введите страну получателя:", reply_markup=ReplyKeyboardRemove())
        return AGENT_IMPORTER_COUNTRY

    elif choice == "2":
        context.user_data["agent_choice"] = "forex_rebate"  # export-like
        if lang == "en":
            update.message.reply_text("🌍 Enter the sender's country:", reply_markup=ReplyKeyboardRemove())
        else:
            update.message.reply_text("🌍 Введите страну отправителя:", reply_markup=ReplyKeyboardRemove())
        return AGENT_EXPORTER_COUNTRY

    else:
        # invalid choice => go back to main menu
        return go_back_to_main_menu(update, context)


# ---------------------
# Agent -> Importer-like
# ---------------------
def agent_importer_country(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    text = update.message.text.strip()
    if not is_valid_text(text):
        if lang == "en":
            update.message.reply_text("Please enter a valid text (no digits). Try again:")
        else:
            update.message.reply_text("Пожалуйста, введите текст без цифр. Попробуйте еще раз:")
        return AGENT_IMPORTER_COUNTRY

    context.user_data["agent_importer_country"] = text
    # Now ask the user to choose a currency:
    if lang == "en":
        update.message.reply_text(
            "Please select the currency:",
            reply_markup=ReplyKeyboardMarkup([["USD", "EUR", "AED", "Others"]],
                                           one_time_keyboard=True, resize_keyboard=True)
        )
    else:
        update.message.reply_text(
            "Пожалуйста, выберите валюту:",
            reply_markup=ReplyKeyboardMarkup([["USD", "EUR", "AED", "Others"]],
                                           one_time_keyboard=True, resize_keyboard=True)
        )
    return AGENT_IMPORTER_CURRENCY

def agent_importer_currency(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    text = update.message.text.strip().upper()
    
    # If this is the first entry (from menu)
    if text == "OTHERS":
        currencies = get_available_currencies()
        context.user_data['available_currencies'] = currencies
        message = format_currency_list(currencies, lang)
        update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
        return AGENT_IMPORTER_CURRENCY
    
    # Handle currency selection by number
    if context.user_data.get('available_currencies'):
        try:
            selection = int(text)
            currencies = context.user_data['available_currencies']
            
            if 1 <= selection <= len(currencies):
                selected_currency = currencies[selection - 1]
                context.user_data['agent_importer_currency'] = selected_currency
                
                # Clear the available_currencies from context
                context.user_data.pop('available_currencies', None)
                
                if lang == "en":
                    update.message.reply_text(
                        f"You selected {selected_currency}. 💰 Enter transfer amount:",
                        reply_markup=ReplyKeyboardRemove()
                    )
                else:
                    update.message.reply_text(
                        f"Вы выбрали {selected_currency}. 💰 Введите сумму перевода:",
                        reply_markup=ReplyKeyboardRemove()
                    )
                return AGENT_IMPORTER_AMOUNT
            else:
                if lang == "en":
                    update.message.reply_text("Invalid number. Please select from the list above:")
                else:
                    update.message.reply_text("Неверный номер. Пожалуйста, выберите из списка выше:")
                return AGENT_IMPORTER_CURRENCY
                
        except ValueError:
            if lang == "en":
                update.message.reply_text("Please enter a valid number from the list:")
            else:
                update.message.reply_text("Пожалуйста, введите корректный номер из списка:")
            return AGENT_IMPORTER_CURRENCY
    
    # For standard currencies (USD, EUR, AED)
    if text not in ["USD", "EUR", "AED"]:
        if lang == "en":
            update.message.reply_text("Invalid option. Please choose one of: USD, EUR, AED, Others")
        else:
            update.message.reply_text("Неверный выбор. Пожалуйста, выберите из: USD, EUR, AED, Others")
        return AGENT_IMPORTER_CURRENCY

    context.user_data['agent_importer_currency'] = text
    
    if lang == "en":
        update.message.reply_text(
            "💰 Enter transfer amount:",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        update.message.reply_text(
            "💰 Введите сумму перевода:",
            reply_markup=ReplyKeyboardRemove()
        )
    return AGENT_IMPORTER_AMOUNT

def agent_importer_amount(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    text = update.message.text.strip()
    if not is_valid_number(text):
        if lang == "en":
            update.message.reply_text("Please enter a numeric value only. Try again:")
        else:
            update.message.reply_text("Пожалуйста, введите только числовое значение. Попробуйте еще раз:")
        return AGENT_IMPORTER_AMOUNT

    amount = float(text)
    currency = context.user_data.get('agent_importer_currency', 'USD')
    
    # Get USD rate first (we'll need this for all conversions)
    usd_rate = get_exchange_rate("USD_RUB")
    if usd_rate is None:
        if lang == "en":
            update.message.reply_text("Exchange rates are currently unavailable. Please try again later.")
        else:
            update.message.reply_text("Курсы валют временно недоступны. Пожалуйста, попробуйте позже.")
        return AGENT_IMPORTER_AMOUNT

    # Convert amount to USD for minimum check
    usd_amount = convert_to_usd(amount, currency)
    
    # Calculate commission
    commission_percent, commission_message = calculate_commission(usd_amount, usd_rate)
    if commission_percent is None:
        if lang == "en":
            update.message.reply_text(
                f"The minimum transfer amount is 5000 USD.\n"
                f"Your amount ({amount:.2f} {currency}) is equivalent to {usd_amount:.2f} USD."
            )
        else:
            update.message.reply_text(
                f"Минимальная сумма перевода 5000 USD.\n"
                f"Ваша сумма ({amount:.2f} {currency}) эквивалентна {usd_amount:.2f} USD."
            )
        return AGENT_IMPORTER_AMOUNT

    context.user_data["agent_importer_amount"] = text
    
    # Store commission info for later use
    context.user_data["agent_importer_commission_percent"] = commission_percent
    context.user_data["agent_importer_commission_message"] = commission_message

    if lang == "en":
        if "minimum" in commission_message:
            # For cases with minimum commission
            base_message = commission_message.replace("commission", "").replace("(", "").replace(")", "").strip()
            update.message.reply_text(
                f"Commission will be {base_message}. Do you want to continue?",
                reply_markup=yes_no_keyboard(lang)
            )
        else:
            # For regular commission cases
            base_message = commission_message.replace("commission", "").strip()
            update.message.reply_text(
                f"Commission will be {base_message}. Do you want to continue?",
                reply_markup=yes_no_keyboard(lang)
            )
    else:
        if "minimum" in commission_message:
            # For cases with minimum commission
            base_message = commission_message.replace("commission", "").replace("(", "").replace(")", "").strip()
            ru_message = base_message.replace("minimum", "минимум")
            update.message.reply_text(
                f"Комиссия составит {ru_message}. Хотите продолжить?",
                reply_markup=yes_no_keyboard(lang)
            )
        else:
            # For regular commission cases
            base_message = commission_message.replace("commission", "").strip()
            update.message.reply_text(
                f"Комиссия составит {base_message}. Хотите продолжить?",
                reply_markup=yes_no_keyboard(lang)
            )
    return AGENT_IMPORTER_COMMISSION_CHOICE

def agent_importer_commission_choice(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    choice = update.message.text.lower()
    if any(w in choice for w in ["yes","да"]):
        if lang == "en":
            update.message.reply_text("Enter sender's INN:", reply_markup=ReplyKeyboardRemove())
        else:
            update.message.reply_text("Введите ИНН отправителя:", reply_markup=ReplyKeyboardRemove())
        return AGENT_IMPORTER_INN
    else:
        return go_back_to_main_menu(update, context)

def agent_importer_inn(update: Update, context: CallbackContext) -> int:
    # For simplicity, let's allow any text. If you want numeric only, you can add check is_valid_number
    context.user_data['agent_importer_inn'] = update.message.text.strip()
    lang = get_user_lang(context)
    if lang == "en":
        update.message.reply_text("Enter payment purpose:")
    else:
        update.message.reply_text("Введите назначение платежа:")
    return AGENT_IMPORTER_PURPOSE

def agent_importer_purpose(update: Update, context: CallbackContext) -> int:
    context.user_data['agent_importer_purpose'] = update.message.text.strip()
    lang = get_user_lang(context)
    if lang == "en":
        update.message.reply_text("Please enter your phone number (e.g. +123456789):")
    else:
        update.message.reply_text("Пожалуйста, введите ваш номер телефона (например +123456789):")
    return AGENT_IMPORTER_PHONE

def agent_importer_phone(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    phone = update.message.text.strip()
    if not is_valid_phone(phone):
        if lang == "en":
            update.message.reply_text("Invalid phone number format. Try again:")
        else:
            update.message.reply_text("Неверный формат номера телефона. Попробуйте еще раз:")
        return AGENT_IMPORTER_PHONE

    context.user_data["agent_importer_phone"] = phone
    return agent_importer_preview(update, context)

def agent_importer_preview(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    ud = context.user_data
    user = update.effective_user

    # We'll keep user ID & username for reference
    ud['agent_user_id'] = user.id
    ud['agent_username'] = user.username

    if lang == "en":
        text = (
            "Check your data (Agent - Make Payment):\n\n"
            f"Recipient Country: {ud.get('agent_importer_country')}\n"
            f"Amount: {ud.get('agent_importer_amount')}\n"
            f"Currency: {ud.get('agent_importer_currency')}\n"
            f"Sender INN: {ud.get('agent_importer_inn')}\n"
            f"Payment Purpose: {ud.get('agent_importer_purpose')}\n"
            f"Phone Number: {ud.get('agent_importer_phone')}\n"
            "\n--- Your Telegram Data ---\n"
            f"Username: @{ud.get('agent_username')}\n\n"
            "We respect your privacy. Your data is kept secure and not shared with third parties.\n\n"
            "Is everything correct?"
        )
    else:
        text = (
            "Проверьте введенные данные (Агент - Произвести оплату):\n\n"
            f"Страна получателя: {ud.get('agent_importer_country')}\n"
            f"Сумма: {ud.get('agent_importer_amount')}\n"
            f"Валюта: {ud.get('agent_importer_currency')}\n"
            f"ИНН отправителя: {ud.get('agent_importer_inn')}\n"
            f"Назначение платежа: {ud.get('agent_importer_purpose')}\n"
            f"Номер телефона: {ud.get('agent_importer_phone')}\n"
            "\n--- Ваши Telegram-данные ---\n"
            f"Username: @{ud.get('agent_username')}\n\n"
            "Мы уважаем вашу конфиденциальность. Ваши данные в безопасности и не передаются третьим лицам.\n\n"
            "Все верно?"
        )

    update.message.reply_text(text, reply_markup=yes_no_keyboard(lang))
    return AGENT_IMPORTER_PREVIEW

def agent_importer_preview_choice(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    choice = update.message.text.lower().strip()
    if any(w in choice for w in ["yes","да"]):
        send_agent_importer_data_to_admin(context)
        if lang == "en":
            update.message.reply_text("Thank you! Data sent to the admin.")
        else:
            update.message.reply_text("Спасибо! Данные отправлены администратору.")
        return go_back_to_main_menu(update, context)
    else:
        if lang == "en":
            update.message.reply_text("Canceled. Returning to the main menu.")
        else:
            update.message.reply_text("Отменено. Возвращаемся в главное меню.")
        return go_back_to_main_menu(update, context)

def send_agent_importer_data_to_admin(context: CallbackContext):
    ud = context.user_data
    msg = (
        "Новый запрос (Агент - Произвести оплату):\n"
        f"Страна получателя: {ud.get('agent_importer_country')}\n"
        f"Сумма: {ud.get('agent_importer_amount')}\n"
        f"Валюта: {ud.get('agent_importer_currency')}\n"
        f"ИНН отправителя: {ud.get('agent_importer_inn')}\n"
        f"Назначение платежа: {ud.get('agent_importer_purpose')}\n"
        f"Номер телефона: {ud.get('agent_importer_phone')}\n"
        "\n--- User Info ---\n"
        f"User ID: {ud.get('agent_user_id')}\n"
        f"Username: @{ud.get('agent_username')}\n"
    )
    context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg)

# ---------------------
# Agent -> Exporter-like
# ---------------------
def agent_exporter_country(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    text = update.message.text.strip()
    if not is_valid_text(text):
        if lang == "en":
            update.message.reply_text("Please enter a valid text (no digits). Try again:")
        else:
            update.message.reply_text("Пожалуйста, введите текст без цифр. Попробуйте еще раз:")
        return AGENT_EXPORTER_COUNTRY

    context.user_data["agent_exporter_country"] = text
    if lang == "en":
        update.message.reply_text(
            "Please select the currency:",
            reply_markup=ReplyKeyboardMarkup([["USD", "EUR", "AED", "Others"]],
                                           one_time_keyboard=True, resize_keyboard=True)
        )
    else:
        update.message.reply_text(
            "Пожалуйста, выберите валюту:",
            reply_markup=ReplyKeyboardMarkup([["USD", "EUR", "AED", "Others"]],
                                           one_time_keyboard=True, resize_keyboard=True)
        )
    return AGENT_EXPORTER_CURRENCY

def agent_exporter_currency(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    text = update.message.text.strip().upper()
    
    # If this is the first entry (from menu)
    if text == "OTHERS":
        currencies = get_available_currencies()
        context.user_data['available_currencies'] = currencies
        message = format_currency_list(currencies, lang)
        update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
        return AGENT_EXPORTER_CURRENCY
    
    # Handle currency selection by number
    if context.user_data.get('available_currencies'):
        try:
            selection = int(text)
            currencies = context.user_data['available_currencies']
            
            if 1 <= selection <= len(currencies):
                selected_currency = currencies[selection - 1]
                context.user_data['agent_exporter_currency'] = selected_currency
                
                # Clear the available_currencies from context
                context.user_data.pop('available_currencies', None)
                
                if lang == "en":
                    update.message.reply_text(
                        f"You selected {selected_currency}. 💰 Enter transfer amount:",
                        reply_markup=ReplyKeyboardRemove()
                    )
                else:
                    update.message.reply_text(
                        f"Вы выбрали {selected_currency}. 💰 Введите сумму перевода:",
                        reply_markup=ReplyKeyboardRemove()
                    )
                return AGENT_EXPORTER_AMOUNT
            else:
                if lang == "en":
                    update.message.reply_text("Invalid number. Please select from the list above:")
                else:
                    update.message.reply_text("Неверный номер. Пожалуйста, выберите из списка выше:")
                return AGENT_EXPORTER_CURRENCY
                
        except ValueError:
            if lang == "en":
                update.message.reply_text("Please enter a valid number from the list:")
            else:
                update.message.reply_text("Пожалуйста, введите корректный номер из списка:")
            return AGENT_EXPORTER_CURRENCY
    
    # For standard currencies (USD, EUR, AED)
    if text not in ["USD", "EUR", "AED"]:
        if lang == "en":
            update.message.reply_text("Invalid option. Please choose one of: USD, EUR, AED, Others")
        else:
            update.message.reply_text("Неверный выбор. Пожалуйста, выберите из: USD, EUR, AED, Others")
        return AGENT_EXPORTER_CURRENCY

    context.user_data['agent_exporter_currency'] = text
    
    if lang == "en":
        update.message.reply_text(
            "💰 Enter transfer amount:",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        update.message.reply_text(
            "💰 Введите сумму перевода:",
            reply_markup=ReplyKeyboardRemove()
        )
    return AGENT_EXPORTER_AMOUNT

def agent_exporter_amount(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    text = update.message.text.strip()
    if not is_valid_number(text):
        if lang == "en":
            update.message.reply_text("Please enter a numeric value only. Try again:")
        else:
            update.message.reply_text("Пожалуйста, введите только числовое значение. Попробуйте еще раз:")
        return AGENT_EXPORTER_AMOUNT

    context.user_data["agent_exporter_amount"] = text
    if lang == "en":
        update.message.reply_text(
            "Commission from 1.5% (minimum commission 100,000 RUB). Continue?",
            reply_markup=yes_no_keyboard(lang)
        )
    else:
        update.message.reply_text(
            "Комиссия от 1.5% (минимальная комиссия 100 000 RUB). Продолжить?",
            reply_markup=yes_no_keyboard(lang)
        )
    return AGENT_EXPORTER_COMMISSION_CHOICE

def agent_exporter_purpose(update: Update, context: CallbackContext) -> int:
    context.user_data["agent_exporter_purpose"] = update.message.text.strip()
    lang = get_user_lang(context)
    update.message.reply_text(_("commission_15", lang), reply_markup=yes_no_keyboard(lang))
    return AGENT_EXPORTER_COMMISSION_CHOICE

def agent_exporter_commission_choice(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    choice = update.message.text.lower()
    if any(w in choice for w in ["yes","да"]):
        if lang == "en":
            update.message.reply_text("Send sender's details:", reply_markup=ReplyKeyboardRemove())
        else:
            update.message.reply_text("Отправьте реквизиты отправителя:", reply_markup=ReplyKeyboardRemove())
        return AGENT_EXPORTER_SENDER_DETAILS
    else:
        return go_back_to_main_menu(update, context)

def agent_exporter_sender_details(update: Update, context: CallbackContext) -> int:
    context.user_data["agent_exporter_sender_details"] = update.message.text.strip()
    lang = get_user_lang(context)
    if lang == "en":
        update.message.reply_text("Send receiver's details:")
    else:
        update.message.reply_text("Отправьте реквизиты получателя:")
    return AGENT_EXPORTER_RECEIVER_DETAILS

def agent_exporter_receiver_details(update: Update, context: CallbackContext) -> int:
    context.user_data["agent_exporter_receiver_details"] = update.message.text.strip()
    lang = get_user_lang(context)
    if lang == "en":
        update.message.reply_text("Please enter your phone number (e.g. +123456789):")
    else:
        update.message.reply_text("Пожалуйста, введите ваш номер телефона (например +123456789):")
    return AGENT_EXPORTER_PHONE

def agent_exporter_phone(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    phone = update.message.text.strip()
    if not is_valid_phone(phone):
        if lang == "en":
            update.message.reply_text("Invalid phone number format. Try again:")
        else:
            update.message.reply_text("Неверный формат номера телефона. Попробуйте еще раз:")
        return AGENT_EXPORTER_PHONE

    context.user_data["agent_exporter_phone"] = phone
    return agent_exporter_preview(update, context)

def agent_exporter_preview(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    ud = context.user_data
    user = update.effective_user

    ud["agent_user_id"] = user.id
    ud["agent_username"] = user.username

    if lang == "en":
        text = (
            "Check your data (Agent - Forex Rebate):\n\n"
            f"Sender Country: {ud.get('agent_exporter_country')}\n"
            f"Amount: {ud.get('agent_exporter_amount')}\n"
            f"Currency: {ud.get('agent_exporter_currency')}\n"
            f"Payment Purpose: {ud.get('agent_exporter_purpose')}\n"
            f"Sender Details: {ud.get('agent_exporter_sender_details')}\n"
            f"Receiver Details: {ud.get('agent_exporter_receiver_details')}\n"
            f"Phone Number: {ud.get('agent_exporter_phone')}\n"
            "\n--- Your Telegram Data ---\n"
            f"Username: @{ud.get('agent_username')}\n\n"
            "We respect your privacy. Your data is kept secure and not shared with third parties.\n\n"
            "Is everything correct?"
        )
    else:
        text = (
            "Проверьте введенные данные (Агент - Вернуть валютную выручку):\n\n"
            f"Страна отправителя: {ud.get('agent_exporter_country')}\n"
            f"Сумма: {ud.get('agent_exporter_amount')}\n"
            f"Валюта: {ud.get('agent_exporter_currency')}\n"
            f"Назначение платежа: {ud.get('agent_exporter_purpose')}\n"
            f"Реквизиты отправителя: {ud.get('agent_exporter_sender_details')}\n"
            f"Реквизиты получателя: {ud.get('agent_exporter_receiver_details')}\n"
            f"Номер телефона: {ud.get('agent_exporter_phone')}\n"
            "\n--- Ваши Telegram-данные ---\n"
            f"Username: @{ud.get('agent_username')}\n\n"
            "Мы уважаем вашу конфиденциальность. Ваши данные в безопасности и не передаются третьим лицам.\n\n"
            "Все верно?"
        )

    update.message.reply_text(text, reply_markup=yes_no_keyboard(lang))
    return AGENT_EXPORTER_PREVIEW

def agent_exporter_preview_choice(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    choice = update.message.text.lower().strip()
    if any(w in choice for w in ["yes","да"]):
        send_agent_exporter_data_to_admin(context)
        if lang == "en":
            update.message.reply_text("Thank you! Data sent to the admin.")
        else:
            update.message.reply_text("Спасибо! Данные отправлены администратору.")
        return go_back_to_main_menu(update, context)
    else:
        if lang == "en":
            update.message.reply_text("Canceled. Returning to main menu.")
        else:
            update.message.reply_text("Отменено. Возвращаемся в главное меню.")
        return go_back_to_main_menu(update, context)

def send_agent_exporter_data_to_admin(context: CallbackContext):
    ud = context.user_data
    msg = (
        "Новый запрос (Агент - Вернуть валютную выручку):\n"
        f"Страна отправителя: {ud.get('agent_exporter_country')}\n"
        f"Сумма: {ud.get('agent_exporter_amount')}\n"
        f"Валюта: {ud.get('agent_exporter_currency')}\n"
        f"Назначение: {ud.get('agent_exporter_purpose')}\n"
        f"Реквизиты отправителя: {ud.get('agent_exporter_sender_details')}\n"
        f"Реквизиты получателя: {ud.get('agent_exporter_receiver_details')}\n"
        f"Номер телефона: {ud.get('agent_exporter_phone')}\n"
        "\n--- User Info ---\n"
        f"User ID: {ud.get('agent_user_id')}\n"
        f"Username: @{ud.get('agent_username')}\n"
    )
    context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg)

#
# -------------------------------------------------------------------
# IMPORTER FLOW
# -------------------------------------------------------------------
#

def importer_country(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    text = update.message.text.strip()
    if not is_valid_text(text):
        if lang == "en":
            update.message.reply_text("Please enter valid text (no digits). Try again:")
        else:
            update.message.reply_text("Пожалуйста, введите текст без цифр. Попробуйте еще раз:")
        return IMPORTER_COUNTRY

    context.user_data['importer_country'] = text
    # Now ask the user to choose a currency:
    if lang == "en":
        update.message.reply_text(
            "Please select the currency:",
            reply_markup=ReplyKeyboardMarkup([["USD", "EUR", "AED", "Others"]],
                                           one_time_keyboard=True, resize_keyboard=True)
        )
    else:
        update.message.reply_text(
            "Пожалуйста, выберите валюту:",
            reply_markup=ReplyKeyboardMarkup([["USD", "EUR", "AED", "Others"]],
                                           one_time_keyboard=True, resize_keyboard=True)
        )
    return IMPORTER_CURRENCY

def importer_amount(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    text = update.message.text.strip()
    if not is_valid_number(text):
        if lang == "en":
            update.message.reply_text("Please enter a numeric value only. Try again:")
        else:
            update.message.reply_text("Пожалуйста, введите только числовое значение. Попробуйте еще раз:")
        return IMPORTER_AMOUNT

    amount = float(text)
    currency = context.user_data.get('importer_currency', 'USD')
    
    # Get USD rate first (we'll need this for all conversions)
    usd_rate = get_exchange_rate("USD_RUB")
    if usd_rate is None:
        if lang == "en":
            update.message.reply_text("Exchange rates are currently unavailable. Please try again later.")
        else:
            update.message.reply_text("Курсы валют временно недоступны. Пожалуйста, попробуйте позже.")
        return IMPORTER_AMOUNT

    # Convert amount to USD for minimum check
    usd_amount = convert_to_usd(amount, currency)
    
    # Calculate commission
    commission_percent, commission_message = calculate_commission(usd_amount, usd_rate)
    if commission_percent is None:
        if lang == "en":
            update.message.reply_text(
                f"The minimum transfer amount is 5000 USD.\n"
                f"Your amount ({amount:.2f} {currency}) is equivalent to {usd_amount:.2f} USD."
            )
        else:
            update.message.reply_text(
                f"Минимальная сумма перевода 5000 USD.\n"
                f"Ваша сумма ({amount:.2f} {currency}) эквивалентна {usd_amount:.2f} USD."
            )
        return IMPORTER_AMOUNT

    context.user_data["importer_amount"] = text
    
    # Store commission info for later use
    context.user_data["importer_commission_percent"] = commission_percent
    context.user_data["importer_commission_message"] = commission_message

    if lang == "en":
        if "minimum" in commission_message:
            # For cases with minimum commission
            base_message = commission_message.replace("commission", "").replace("(", "").replace(")", "").strip()
            update.message.reply_text(
                f"Commission will be {base_message}. Do you want to continue?",
                reply_markup=yes_no_keyboard(lang)
            )
        else:
            # For regular commission cases
            base_message = commission_message.replace("commission", "").strip()
            update.message.reply_text(
                f"Commission will be {base_message}. Do you want to continue?",
                reply_markup=yes_no_keyboard(lang)
            )
    else:
        if "minimum" in commission_message:
            # For cases with minimum commission
            base_message = commission_message.replace("commission", "").replace("(", "").replace(")", "").strip()
            ru_message = base_message.replace("minimum", "минимум")
            update.message.reply_text(
                f"Комиссия составит {ru_message}. Хотите продолжить?",
                reply_markup=yes_no_keyboard(lang)
            )
        else:
            # For regular commission cases
            base_message = commission_message.replace("commission", "").strip()
            update.message.reply_text(
                f"Комиссия составит {base_message}. Хотите продолжить?",
                reply_markup=yes_no_keyboard(lang)
            )
    return IMPORTER_COMMISSION_CHOICE

def get_available_currencies():
    """
    Gets list of available currencies from exchange_rates.json
    Returns a list of currency codes (without _RUB suffix)
    """
    try:
        with open("exchange_rates.json", "r") as f:
            data = json.load(f)
            # Filter out timestamp and get currency codes
            currencies = [key.replace('_RUB', '') for key in data.keys() if key != 'timestamp']
            return sorted(currencies)  # Sort alphabetically
    except (FileNotFoundError, json.JSONDecodeError):
        return ["USD", "EUR", "AED"]  # Fallback to default currencies

def format_currency_list(currencies: list, lang: str) -> str:
    """
    Formats the currency list as a numbered list
    """
    if lang == "en":
        header = "Available currencies:\n\n"
    else:
        header = "Доступные валюты:\n\n"
    
    currency_list = "\n".join(f"{i+1}. {currency}" for i, currency in enumerate(currencies))
    
    if lang == "en":
        footer = "\nPlease enter the number of your chosen currency:"
    else:
        footer = "\nВведите номер выбранной валюты:"
    
    return f"{header}{currency_list}{footer}"

def importer_currency(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    text = update.message.text.strip().upper()
    
    # If this is the first entry (from menu)
    if text == "OTHERS":
        currencies = get_available_currencies()
        context.user_data['available_currencies'] = currencies  # Store for later use
        message = format_currency_list(currencies, lang)
        update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
        return IMPORTER_CURRENCY
    
    # Handle currency selection by number
    if context.user_data.get('available_currencies'):
        try:
            selection = int(text)
            currencies = context.user_data['available_currencies']
            
            if 1 <= selection <= len(currencies):
                selected_currency = currencies[selection - 1]
                context.user_data['importer_currency'] = selected_currency
                context.user_data['importer_currency_manual'] = False
                
                # Clear the available_currencies from context as we don't need it anymore
                context.user_data.pop('available_currencies', None)
                
                if lang == "en":
                    update.message.reply_text(
                        f"You selected {selected_currency}. 💰 Enter transfer amount:",
                        reply_markup=ReplyKeyboardRemove()
                    )
                else:
                    update.message.reply_text(
                        f"Вы выбрали {selected_currency}. 💰 Введите сумму перевода:",
                        reply_markup=ReplyKeyboardRemove()
                    )
                return IMPORTER_AMOUNT
            else:
                if lang == "en":
                    update.message.reply_text("Invalid number. Please select from the list above:")
                else:
                    update.message.reply_text("Неверный номер. Пожалуйста, выберите из списка выше:")
                return IMPORTER_CURRENCY
                
        except ValueError:
            if lang == "en":
                update.message.reply_text("Please enter a valid number from the list:")
            else:
                update.message.reply_text("Пожалуйста, введите корректный номер из списка:")
            return IMPORTER_CURRENCY
    
    # For standard currencies (USD, EUR, AED)
    if text not in ["USD", "EUR", "AED"]:
        if lang == "en":
            update.message.reply_text("Invalid option. Please choose one of: USD, EUR, AED, Others")
        else:
            update.message.reply_text("Неверный выбор. Пожалуйста, выберите из: USD, EUR, AED, Others")
        return IMPORTER_CURRENCY

    context.user_data["importer_currency_manual"] = False
    context.user_data['importer_currency'] = text
    
    if lang == "en":
        update.message.reply_text(
            "💰 Enter transfer amount:",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        update.message.reply_text(
            "💰 Введите сумму перевода:",
            reply_markup=ReplyKeyboardRemove()
        )
    return IMPORTER_AMOUNT

def importer_currency_manual(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    currency_manual = update.message.text.strip()
    # You might perform additional checks here if desired.
    context.user_data['importer_currency'] = currency_manual
    if lang == "en":
        update.message.reply_text(
            "Note: The minimum transfer amount is 5000 USD equivalent and the minimum commission is 100,000 RUB. "
            "Your transaction will be subject to review."
        )
        update.message.reply_text("💰 Enter transfer amount:")
    else:
        update.message.reply_text(
            "Обратите внимание: минимальная сумма перевода эквивалентна 5000 USD, а минимальная комиссия 100 000 RUB. "
            "Ваша транзакция будет рассмотрена."
        )
        update.message.reply_text("💰 Введите сумму перевода:")
    return IMPORTER_AMOUNT

def importer_commission_choice(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    choice = update.message.text.lower()
    if any(w in choice for w in ["yes","да"]):
        if lang == "en":
            update.message.reply_text("Enter sender's INN:", reply_markup=ReplyKeyboardRemove())
        else:
            update.message.reply_text("Введите ИНН отправителя:", reply_markup=ReplyKeyboardRemove())
        return IMPORTER_INN
    else:
        return go_back_to_main_menu(update, context)

def importer_inn(update: Update, context: CallbackContext) -> int:
    context.user_data['importer_inn'] = update.message.text.strip()
    lang = get_user_lang(context)
    if lang == "en":
        update.message.reply_text("Enter payment purpose:")
    else:
        update.message.reply_text("Введите назначение платежа:")
    return IMPORTER_PURPOSE

def importer_purpose(update: Update, context: CallbackContext) -> int:
    context.user_data['importer_purpose'] = update.message.text.strip()
    lang = get_user_lang(context)
    # Ask for phone next
    if lang == "en":
        update.message.reply_text("Please enter your phone number (e.g. +123456789):")
    else:
        update.message.reply_text("Пожалуйста, введите ваш номер телефона (например +123456789):")
    return IMPORTER_PHONE

def importer_phone(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    phone = update.message.text.strip()
    if not is_valid_phone(phone):
        if lang == "en":
            update.message.reply_text("Invalid phone number format. Try again:")
        else:
            update.message.reply_text("Неверный формат номера телефона. Попробуйте еще раз:")
        return IMPORTER_PHONE

    context.user_data["importer_phone"] = phone
    return importer_preview(update, context)

def importer_preview(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    user = update.effective_user
    ud = context.user_data
    ud['importer_user_id']   = user.id
    ud['importer_username']  = user.username

    if lang == "en":
        text = (
            "Check your data (Importer):\n\n"
            f"Recipient country: {ud.get('importer_country')}\n"
            f"Amount: {ud.get('importer_amount')}\n"
            f"Currency: {ud.get('importer_currency')}\n"
            f"Sender INN: {ud.get('importer_inn')}\n"
            f"Payment purpose: {ud.get('importer_purpose')}\n"
            f"Phone number: {ud.get('importer_phone')}\n"
            "\n--- Your Telegram Data ---\n"
            f"Username: @{ud.get('importer_username')}\n\n"
            "We respect your privacy. Your data is kept secure and not shared with third parties.\n\n"
            "Is everything correct?"
        )
    else:
        text = (
            "Проверьте введенные данные (Импортер):\n\n"
            f"Страна получателя: {ud.get('importer_country')}\n"
            f"Сумма: {ud.get('importer_amount')}\n"
            f"Валюта: {ud.get('importer_currency')}\n"
            f"ИНН отправителя: {ud.get('importer_inn')}\n"
            f"Назначение платежа: {ud.get('importer_purpose')}\n"
            f"Номер телефона: {ud.get('importer_phone')}\n"
            "\n--- Ваши Telegram-данные ---\n"
            f"Username: @{ud.get('importer_username')}\n\n"
            "Мы уважаем вашу конфиденциальность. Ваши данные в безопасности и не передаются третьим лицам.\n\n"
            "Все верно?"
        )
    update.message.reply_text(text, reply_markup=yes_no_keyboard(lang))
    return IMPORTER_PREVIEW

def importer_preview_choice(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    choice = update.message.text.lower().strip()
    if any(w in choice for w in ["yes","да"]):
        send_importer_data_to_admin(context)
        if lang == "en":
            update.message.reply_text("Thank you! Data sent to the admin.")
        else:
            update.message.reply_text("Спасибо! Данные отправлены администратору.")
        return go_back_to_main_menu(update, context)
    else:
        if lang == "en":
            update.message.reply_text("Canceled. Returning to main menu.")
        else:
            update.message.reply_text("Отменено. Возвращаемся в главное меню.")
        return go_back_to_main_menu(update, context)

def send_importer_data_to_admin(context: CallbackContext):
    ud = context.user_data
    msg = (
        "Новый запрос (Импортер):\n"
        f"Страна: {ud.get('importer_country')}\n"
        f"Сумма: {ud.get('importer_amount')}\n"
        f"Валюта: {ud.get('importer_currency')}\n"
        f"ИНН отправителя: {ud.get('importer_inn')}\n"
        f"Назначение: {ud.get('importer_purpose')}\n"
        f"Телефон: {ud.get('importer_phone')}\n"
        "\n--- User Info ---\n"
        f"User ID: {ud.get('importer_user_id')}\n"
        f"Username: @{ud.get('importer_username')}\n"
    )
    context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg)


#
# -------------------------------------------------------------------
# EXPORTER FLOW
# -------------------------------------------------------------------
#

def exporter_country(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    text = update.message.text.strip()
    if not is_valid_text(text):
        if lang == "en":
            update.message.reply_text("Please enter a valid text (no digits). Try again:")
        else:
            update.message.reply_text("Пожалуйста, введите текст без цифр. Попробуйте еще раз:")
        return EXPORTER_COUNTRY

    context.user_data['exporter_country'] = text
    # Now ask the user to choose a currency:
    if lang == "en":
        update.message.reply_text(
            "Please select the currency:",
            reply_markup=ReplyKeyboardMarkup([["USD", "EUR", "AED", "Others"]],
                                           one_time_keyboard=True, resize_keyboard=True)
        )
    else:
        update.message.reply_text(
            "Пожалуйста, выберите валюту:",
            reply_markup=ReplyKeyboardMarkup([["USD", "EUR", "AED", "Others"]],
                                           one_time_keyboard=True, resize_keyboard=True)
        )
    return EXPORTER_CURRENCY

def exporter_currency(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    text = update.message.text.strip().upper()
    
    # If this is the first entry (from menu)
    if text == "OTHERS":
        currencies = get_available_currencies()
        context.user_data['available_currencies'] = currencies  # Store for later use
        message = format_currency_list(currencies, lang)
        update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
        return EXPORTER_CURRENCY
    
    # Handle currency selection by number
    if context.user_data.get('available_currencies'):
        try:
            selection = int(text)
            currencies = context.user_data['available_currencies']
            
            if 1 <= selection <= len(currencies):
                selected_currency = currencies[selection - 1]
                context.user_data['exporter_currency'] = selected_currency
                context.user_data['exporter_currency_manual'] = False
                
                # Clear the available_currencies from context
                context.user_data.pop('available_currencies', None)
                
                if lang == "en":
                    update.message.reply_text(
                        f"You selected {selected_currency}. 💰 Enter transfer amount:",
                        reply_markup=ReplyKeyboardRemove()
                    )
                else:
                    update.message.reply_text(
                        f"Вы выбрали {selected_currency}. 💰 Введите сумму перевода:",
                        reply_markup=ReplyKeyboardRemove()
                    )
                return EXPORTER_AMOUNT
            else:
                if lang == "en":
                    update.message.reply_text("Invalid number. Please select from the list above:")
                else:
                    update.message.reply_text("Неверный номер. Пожалуйста, выберите из списка выше:")
                return EXPORTER_CURRENCY
                
        except ValueError:
            if lang == "en":
                update.message.reply_text("Please enter a valid number from the list:")
            else:
                update.message.reply_text("Пожалуйста, введите корректный номер из списка:")
            return EXPORTER_CURRENCY
    
    # For standard currencies (USD, EUR, AED)
    if text not in ["USD", "EUR", "AED"]:
        if lang == "en":
            update.message.reply_text("Invalid option. Please choose one of: USD, EUR, AED, Others")
        else:
            update.message.reply_text("Неверный выбор. Пожалуйста, выберите из: USD, EUR, AED, Others")
        return EXPORTER_CURRENCY

    context.user_data["exporter_currency_manual"] = False
    context.user_data['exporter_currency'] = text
    
    if lang == "en":
        update.message.reply_text(
            "💰 Enter transfer amount:",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        update.message.reply_text(
            "💰 Введите сумму перевода:",
            reply_markup=ReplyKeyboardRemove()
        )
    return EXPORTER_AMOUNT

def exporter_amount(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    text = update.message.text.strip()
    if not is_valid_number(text):
        if lang == "en":
            update.message.reply_text("Please enter a numeric value only. Try again:")
        else:
            update.message.reply_text("Пожалуйста, введите только числовое значение. Попробуйте еще раз:")
        return EXPORTER_AMOUNT

    context.user_data['exporter_amount'] = text
    if lang == "en":
        update.message.reply_text(
            "Commission from 1.5% (minimum commission 100,000 RUB). Continue?",
            reply_markup=yes_no_keyboard(lang)
        )
    else:
        update.message.reply_text(
            "Комиссия от 1.5% (минимальная комиссия 100 000 RUB). Продолжить?",
            reply_markup=yes_no_keyboard(lang)
        )
    return EXPORTER_COMMISSION_CHOICE

def exporter_purpose(update: Update, context: CallbackContext) -> int:
    context.user_data['exporter_purpose'] = update.message.text.strip()
    lang = get_user_lang(context)
    update.message.reply_text(_("commission_15", lang), reply_markup=yes_no_keyboard(lang))
    return EXPORTER_COMMISSION_CHOICE

def exporter_commission_choice(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    choice = update.message.text.lower()
    if any(w in choice for w in ["yes","да"]):
        if lang == "en":
            update.message.reply_text("Send sender's details:", reply_markup=ReplyKeyboardRemove())
        else:
            update.message.reply_text("Отправьте реквизиты отправителя:", reply_markup=ReplyKeyboardRemove())
        return EXPORTER_SENDER_DETAILS
    else:
        return go_back_to_main_menu(update, context)

def exporter_sender_details(update: Update, context: CallbackContext) -> int:
    context.user_data['exporter_sender_details'] = update.message.text.strip()
    lang = get_user_lang(context)
    if lang == "en":
        update.message.reply_text("Send receiver's details:")
    else:
        update.message.reply_text("Отправьте реквизиты получателя:")
    return EXPORTER_RECEIVER_DETAILS

def exporter_receiver_details(update: Update, context: CallbackContext) -> int:
    context.user_data['exporter_receiver_details'] = update.message.text.strip()
    lang = get_user_lang(context)
    if lang == "en":
        update.message.reply_text("Please enter your phone number (e.g. +123456789):")
    else:
        update.message.reply_text("Пожалуйста, введите ваш номер телефона (например +123456789):")
    return EXPORTER_PHONE

def exporter_phone(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    phone = update.message.text.strip()
    if not is_valid_phone(phone):
        if lang == "en":
            update.message.reply_text("Invalid phone number format. Try again:")
        else:
            update.message.reply_text("Неверный формат номера телефона. Попробуйте еще раз:")
        return EXPORTER_PHONE

    context.user_data["exporter_phone"] = phone
    return exporter_preview(update, context)

def exporter_preview(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    user = update.effective_user
    ud   = context.user_data

    ud['exporter_user_id']    = user.id
    ud['exporter_username']   = user.username

    if lang == "en":
        text = (
            "Check your data (Exporter):\n\n"
            f"Sender country: {ud.get('exporter_country')}\n"
            f"Amount: {ud.get('exporter_amount')}\n"
            f"Currency: {ud.get('exporter_currency')}\n"
            f"Payment purpose: {ud.get('exporter_purpose')}\n"
            f"Sender details: {ud.get('exporter_sender_details')}\n"
            f"Receiver details: {ud.get('exporter_receiver_details')}\n"
            f"Phone number: {ud.get('exporter_phone')}\n"
            "\n--- Your Telegram Data ---\n"
            f"Username: @{ud.get('exporter_username')}\n\n"
            "We respect your privacy. Your data is kept secure and not shared with third parties.\n\n"
            "Is everything correct?"
        )
    else:
        text = (
            "Проверьте введенные данные (Экспортер):\n\n"
            f"Страна отправителя: {ud.get('exporter_country')}\n"
            f"Сумма: {ud.get('exporter_amount')}\n"
            f"Валюта: {ud.get('exporter_currency')}\n"
            f"Назначение платежа: {ud.get('exporter_purpose')}\n"
            f"Реквизиты отправителя: {ud.get('exporter_sender_details')}\n"
            f"Реквизиты получателя: {ud.get('exporter_receiver_details')}\n"
            f"Номер телефона: {ud.get('exporter_phone')}\n"
            "\n--- Ваши Telegram-данные ---\n"
            f"Username: @{ud.get('exporter_username')}\n\n"
            "Мы уважаем вашу конфиденциальность. Ваши данные в безопасности и не передаются третьим лицам.\n\n"
            "Все верно?"
        )
    update.message.reply_text(text, reply_markup=yes_no_keyboard(lang))
    return EXPORTER_PREVIEW

def exporter_preview_choice(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    choice = update.message.text.lower().strip()
    if any(w in choice for w in ["yes","да"]):
        send_exporter_data_to_admin(context)
        if lang == "en":
            update.message.reply_text("Thank you! Data sent to the admin.")
        else:
            update.message.reply_text("Спасибо! Данные отправлены администратору.")
        return go_back_to_main_menu(update, context)
    else:
        if lang == "en":
            update.message.reply_text("Canceled. Returning to main menu.")
        else:
            update.message.reply_text("Отменено. Возвращаемся в главное меню.")
        return go_back_to_main_menu(update, context)

def send_exporter_data_to_admin(context: CallbackContext):
    ud = context.user_data
    msg = (
        "Новый запрос (Экспортер):\n"
        f"Страна отправителя: {ud.get('exporter_country')}\n"
        f"Сумма: {ud.get('exporter_amount')}\n"
        f"Валюта: {ud.get('exporter_currency')}\n"
        f"Назначение: {ud.get('exporter_purpose')}\n"
        f"Реквизиты отправителя: {ud.get('exporter_sender_details')}\n"
        f"Реквизиты получателя: {ud.get('exporter_receiver_details')}\n"
        f"Телефон: {ud.get('exporter_phone')}\n"
        "\n--- User Info ---\n"
        f"User ID: {ud.get('exporter_user_id')}\n"
        f"Username: @{ud.get('exporter_username')}\n"
    )
    context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg)

#
# -------------------------------------------------------------------
# PHYSICAL PERSON FLOW
# -------------------------------------------------------------------
#

def physical_choices(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    choice = update.message.text.lower().strip()

    if any(word in choice for word in ["перевод себе", "transfer to self"]):
        context.user_data["physical_choice"] = "Перевод себе" if lang == "ru" else "Transfer to self"
        if lang == "en":
            update.message.reply_text("🌍 Enter recipient country:", reply_markup=ReplyKeyboardRemove())
        else:
            update.message.reply_text("🌍 Введите страну получателя:", reply_markup=ReplyKeyboardRemove())
        return PHYSICAL_COUNTRY

    elif any(word in choice for word in ["перевод родственнику", "transfer to relative"]):
        context.user_data["physical_choice"] = "Перевод родственнику" if lang == "ru" else "Transfer to relative"
        if lang == "en":
            update.message.reply_text("🌍 Enter recipient country:", reply_markup=ReplyKeyboardRemove())
        else:
            update.message.reply_text("🌍 Введите страну получателя:", reply_markup=ReplyKeyboardRemove())
        return PHYSICAL_COUNTRY

    elif any(word in choice for word in ["оплата услуг", "pay for services"]):
        context.user_data["physical_choice"] = "Оплата услуг" if lang == "ru" else "Pay for services"
        if lang == "en":
            update.message.reply_text("🌍 Enter recipient country:", reply_markup=ReplyKeyboardRemove())
        else:
            update.message.reply_text("🌍 Введите страну получателя:", reply_markup=ReplyKeyboardRemove())
        return PHYSICAL_COUNTRY

    elif any(word in choice for word in ["назад", "back"]):
        return go_back_to_main_menu(update, context)
    else:
        if lang == "en":
            update.message.reply_text("Please select from the menu.")
        else:
            update.message.reply_text("Пожалуйста, выберите из меню.")
        return PHYSICAL_CHOICES

def physical_country(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    text = update.message.text.strip()
    if not is_valid_text(text):
        if lang == "en":
            update.message.reply_text("Please enter a valid text (no digits). Try again:")
        else:
            update.message.reply_text("Пожалуйста, введите текст без цифр. Попробуйте еще раз:")
        return PHYSICAL_COUNTRY

    context.user_data['physical_country'] = text
    # Now ask the user to choose a currency:
    if lang == "en":
        update.message.reply_text(
            "Please select the currency:",
            reply_markup=ReplyKeyboardMarkup([["USD", "EUR", "AED", "Others"]],
                                           one_time_keyboard=True, resize_keyboard=True)
        )
    else:
        update.message.reply_text(
            "Пожалуйста, выберите валюту:",
            reply_markup=ReplyKeyboardMarkup([["USD", "EUR", "AED", "Others"]],
                                           one_time_keyboard=True, resize_keyboard=True)
        )
    return PHYSICAL_CURRENCY

def physical_currency(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    text = update.message.text.strip().upper()
    
    # If this is the first entry (from menu)
    if text == "OTHERS":
        currencies = get_available_currencies()
        context.user_data['available_currencies'] = currencies  # Store for later use
        message = format_currency_list(currencies, lang)
        update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
        return PHYSICAL_CURRENCY
    
    # Handle currency selection by number
    if context.user_data.get('available_currencies'):
        try:
            selection = int(text)
            currencies = context.user_data['available_currencies']
            
            if 1 <= selection <= len(currencies):
                selected_currency = currencies[selection - 1]
                context.user_data['physical_currency'] = selected_currency
                context.user_data['physical_currency_manual'] = False
                
                # Clear the available_currencies from context
                context.user_data.pop('available_currencies', None)
                
                if lang == "en":
                    update.message.reply_text(
                        f"You selected {selected_currency}. 💰 Enter transfer amount:",
                        reply_markup=ReplyKeyboardRemove()
                    )
                else:
                    update.message.reply_text(
                        f"Вы выбрали {selected_currency}. 💰 Введите сумму перевода:",
                        reply_markup=ReplyKeyboardRemove()
                    )
                return PHYSICAL_AMOUNT
            else:
                if lang == "en":
                    update.message.reply_text("Invalid number. Please select from the list above:")
                else:
                    update.message.reply_text("Неверный номер. Пожалуйста, выберите из списка выше:")
                return PHYSICAL_CURRENCY
                
        except ValueError:
            if lang == "en":
                update.message.reply_text("Please enter a valid number from the list:")
            else:
                update.message.reply_text("Пожалуйста, введите корректный номер из списка:")
            return PHYSICAL_CURRENCY
    
    # For standard currencies (USD, EUR, AED)
    if text not in ["USD", "EUR", "AED"]:
        if lang == "en":
            update.message.reply_text("Invalid option. Please choose one of: USD, EUR, AED, Others")
        else:
            update.message.reply_text("Неверный выбор. Пожалуйста, выберите из: USD, EUR, AED, Others")
        return PHYSICAL_CURRENCY

    context.user_data["physical_currency_manual"] = False
    context.user_data['physical_currency'] = text
    
    if lang == "en":
        update.message.reply_text(
            "💰 Enter transfer amount:",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        update.message.reply_text(
            "💰 Введите сумму перевода:",
            reply_markup=ReplyKeyboardRemove()
        )
    return PHYSICAL_AMOUNT

def physical_amount(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    text = update.message.text.strip()
    if not is_valid_number(text):
        if lang == "en":
            update.message.reply_text("Please enter a numeric value only. Try again:")
        else:
            update.message.reply_text("Пожалуйста, введите только числовое значение. Попробуйте еще раз:")
        return PHYSICAL_AMOUNT

    amount = float(text)
    currency = context.user_data.get('physical_currency', 'USD')
    
    # Convert amount to USD for minimum check
    usd_amount = convert_to_usd(amount, currency)
    
    if usd_amount < 20000:  # Minimum 20K USD check
        if lang == "en":
            update.message.reply_text(
                f"The minimum transfer amount is 20 000 USD.\n"
                f"Your amount ({amount:.2f} {currency}) is equivalent to {usd_amount:.2f} USD."
            )
        else:
            update.message.reply_text(
                f"Минимальная сумма перевода 20 000 USD.\n"
                f"Ваша сумма ({amount:.2f} {currency}) эквивалентна {usd_amount:.2f} USD."
            )
        return PHYSICAL_AMOUNT

    context.user_data['physical_amount'] = text
    
    if lang == "en":
        update.message.reply_text(
            "Commission is determined individually for each transaction. Continue?",
            reply_markup=yes_no_keyboard(lang)
        )
    else:
        update.message.reply_text(
            "Комиссия определяется индивидуально для каждой транзакции. Продолжить?",
            reply_markup=yes_no_keyboard(lang)
        )
    return PHYSICAL_COMMISSION_CHOICE

def physical_commission_choice(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    choice = update.message.text.lower().strip()
    if any(w in choice for w in ["yes","да"]):
        # ask phone before final preview
        if lang == "en":
            update.message.reply_text("Please enter your phone number (e.g. +123456789):", reply_markup=ReplyKeyboardRemove())
        else:
            update.message.reply_text("Пожалуйста, введите ваш номер телефона (например +123456789):", reply_markup=ReplyKeyboardRemove())
        return PHYSICAL_PHONE
    else:
        return go_back_to_main_menu(update, context)

def physical_phone(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    phone = update.message.text.strip()
    if not is_valid_phone(phone):
        if lang == "en":
            update.message.reply_text("Invalid phone number format. Try again:")
        else:
            update.message.reply_text("Неверный формат номера телефона. Попробуйте еще раз:")
        return PHYSICAL_PHONE

    context.user_data["physical_phone"] = phone
    return physical_preview(update, context)

def physical_preview(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    user = update.effective_user
    ud = context.user_data

    ud['physical_user_id'] = user.id
    ud['physical_username'] = user.username

    if lang == "en":
        text = (
            "Check your data (Individual):\n\n"
            f"Type: {ud.get('physical_choice')}\n"
            f"Recipient country: {ud.get('physical_country')}\n"
            f"Amount: {ud.get('physical_amount')}\n"
            f"Currency: {ud.get('physical_currency')}\n"
            f"Phone number: {ud.get('physical_phone')}\n"
            "\n--- Your Telegram Data ---\n"
            f"Username: @{ud.get('physical_username')}\n\n"
            "We respect your privacy. Your data is kept secure and not shared with third parties.\n\n"
            "Is everything correct?"
        )
    else:
        text = (
            "Проверьте введенные данные (Физ лицо):\n\n"
            f"Тип перевода: {ud.get('physical_choice')}\n"
            f"Страна получателя: {ud.get('physical_country')}\n"
            f"Сумма: {ud.get('physical_amount')}\n"
            f"Валюта: {ud.get('physical_currency')}\n"
            f"Номер телефона: {ud.get('physical_phone')}\n"
            "\n--- Ваши Telegram-данные ---\n"
            f"Username: @{ud.get('physical_username')}\n\n"
            "Мы уважаем вашу конфиденциальность. Ваши данные в безопасности и не передаются третьим лицам.\n\n"
            "Все верно?"
        )

    update.message.reply_text(text, reply_markup=yes_no_keyboard(lang))
    return PHYSICAL_PREVIEW

def physical_preview_choice(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    choice = update.message.text.lower().strip()
    if any(w in choice for w in ["yes","да"]):
        send_physical_data_to_admin(context)
        if lang == "en":
            update.message.reply_text("Thank you! Data sent to the admin.")
        else:
            update.message.reply_text("Спасибо! Данные отправлены администратору.")
        return go_back_to_main_menu(update, context)
    else:
        if lang == "en":
            update.message.reply_text("Canceled. Returning to main menu.")
        else:
            update.message.reply_text("Отменено. Возвращаемся в главное меню.")
        return go_back_to_main_menu(update, context)

def send_physical_data_to_admin(context: CallbackContext):
    ud = context.user_data
    msg = (
        "Новый запрос (Физ лицо):\n"
        f"Тип перевода: {ud.get('physical_choice')}\n"
        f"Страна: {ud.get('physical_country')}\n"
        f"Сумма: {ud.get('physical_amount')}\n"
        f"Валюта: {ud.get('physical_currency')}\n"
        f"Номер телефона: {ud.get('physical_phone')}\n"
        "\n--- User Info ---\n"
        f"User ID: {ud.get('physical_user_id')}\n"
        f"Username: @{ud.get('physical_username')}\n"
    )
    context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg)

#
# -------------------------------------------------------------------
# CANCEL / HELP / FAQ / CONTACT
# -------------------------------------------------------------------
#

def cancel_command(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    # Clear user_data except language
    lang_setting = context.user_data.get('lang')
    context.user_data.clear()
    context.user_data['lang'] = lang_setting

    if lang == "en":
        update.message.reply_text(
            "✖️ Current operation cancelled.\nReturning to the main menu...",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        update.message.reply_text(
            "✖️ Текущая операция отменена.\nВозвращаемся в главное меню...",
            reply_markup=ReplyKeyboardRemove()
        )
    return go_back_to_main_menu(update, context)

def help_command(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    if lang == "en":
        help_text = (
            "🔍 Available Commands:\n\n"
            "/menu - Return to main menu\n"
            "/cancel - Cancel current operation\n"
            "/contact - Contact support\n"
            "/faq - Frequently asked questions\n"
            "/language - Change language\n\n"
            "Need help? Contact our support: @support_username\n"
        )
    else:
        help_text = (
            "🔍 Доступные команды:\n\n"
            "/menu - Вернуться в главное меню\n"
            "/cancel - Отменить текущую операцию\n"
            "/contact - Связаться с поддержкой\n"
            "/faq - Частые вопросы\n"
            "/language - Изменить язык\n\n"
            "Нужна помощь? Свяжитесь с поддержкой: @support_username"
        )
    update.message.reply_text(help_text, reply_markup=ReplyKeyboardRemove())
    return MAIN_MENU

def faq_command(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    if lang == "en":
        faq_text = (
            "❓ *Frequently Asked Questions*\n\n"
            "*Q: How long does a transfer take?*\n"
            "A: Usually 2-5 business days\n\n"
            "*Q: What documents are needed?*\n"
            "A: ID and valid contract with the counterparty\n\n"
            "*Q: What are the commission rates?*\n"
            "A: - *Importers:*\n"
            "     🔹 *$10,000 – $50,000* → 5% (min. 100,000 RUB)\n"
            "     🔹 *$50,000 – $100,000* → 3.5%\n"
            "     🔹 *$100,000 – $500,000* → 3%\n"
            "     🔹 *$500,000+* → 2.5%\n"
            "     💰 *Minimum commission* (100,000 RUB) applies only to transfers of $10,000–$50,000 if 5% is lower than this amount.\n\n"
            "   - *Exporters:* from 1.5%\n"
            "   - *Individual transfers:* varies by country, minimum commission 100,000 RUB.\n\n"
            "*Q: Which countries do you support?*\n"
            "A: We support transfers to/from more than 200 countries."
        )
    else:
        faq_text = (
            "❓ *Частые вопросы*\n\n"
            "*В: Сколько времени занимает перевод?*\n"
            "О: Обычно 2-5 рабочих дней\n\n"
            "*В: Какие документы нужны?*\n"
            "О: Удостоверение личности и рабочий контракт с контрагентом\n\n"
            "*В: Какие комиссии?*\n"
            "О: - *Импортеры:*\n"
            "     🔹 *$10,000 – $50,000* → 5% (мин. 100,000 RUB)\n"
            "     🔹 *$50,000 – $100,000* → 3.5%\n"
            "     🔹 *$100,000 – $500,000* → 3%\n"
            "     🔹 *$500,000+* → 2.5%\n"
            "     💰 *Минимальная комиссия* (100,000 RUB) применяется только для переводов $10,000–$50,000, если 5% меньше этой суммы.\n\n"
            "   - *Экспортеры:* от 1.5%\n"
            "   - *Физ. лица:* зависит от страны, минимальная комиссия 100 тыс. руб.\n\n"
            "*В: Какие страны поддерживаются?*\n"
            "О: Мы проводим оплаты в более чем 200 странах."
        )
    update.message.reply_text(faq_text, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
    return MAIN_MENU

def contact_command(update: Update, context: CallbackContext) -> int:
    lang = get_user_lang(context)
    if lang == "en":
        contact_text = (
            "📞 Contact Us\n\n"
            "Support Team: @support_username\n"
            "Working hours: 24/7\n\n"
            "For urgent matters:\n"
            "Email: support@example.com"
        )
    else:
        contact_text = (
            "📞 Связаться с нами\n\n"
            "Команда поддержки: @support_username\n"
            "Время работы: 24/7\n\n"
            "Для срочных вопросов:\n"
            "Email: support@example.com"
        )
    update.message.reply_text(contact_text, reply_markup=ReplyKeyboardRemove())
    return MAIN_MENU

def convert_to_usd(amount: float, currency: str) -> float:
    """Convert given amount from specified currency to USD"""
    if currency == "USD":
        return amount
        
    # Get USD rate first (we'll need this for all conversions)
    usd_rate = get_exchange_rate("USD_RUB")
    if usd_rate is None:
        return 0  # Return 0 if we can't get the rate
        
    # If it's not USD, get the rate for the specified currency
    cur_rate = get_exchange_rate(f"{currency}_RUB")
    if cur_rate is None:
        return 0  # Return 0 if we can't get the rate
        
    # Convert to USD using cross-rate
    return (amount * cur_rate) / usd_rate