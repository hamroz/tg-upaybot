from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackQueryHandler
)
from config import BOT_TOKEN
from handlers import (
    start,
    main_menu,
    about_command,
    language_command,
    language_callback,
    cancel_command,
    help_command,
    contact_command,
    faq_command,
    go_back_to_main_menu,

    # Agent
    agent_submenu,
    agent_importer_country,
    agent_importer_amount,
    agent_importer_currency,
    agent_importer_commission_choice,
    agent_importer_inn,
    agent_importer_purpose,
    agent_importer_phone,
    agent_importer_preview_choice,

    agent_exporter_country,
    agent_exporter_amount,
    agent_exporter_currency,
    agent_exporter_purpose,
    agent_exporter_commission_choice,
    agent_exporter_sender_details,
    agent_exporter_receiver_details,
    agent_exporter_phone,
    agent_exporter_preview_choice,

    # Importer
    importer_country,
    importer_amount,
    importer_currency,
    importer_commission_choice,
    importer_inn,
    importer_purpose,
    importer_phone,
    importer_preview_choice,

    # Exporter
    exporter_country,
    exporter_amount,
    exporter_currency,
    exporter_purpose,
    exporter_commission_choice,
    exporter_sender_details,
    exporter_receiver_details,
    exporter_phone,
    exporter_preview_choice,

    # Physical
    physical_choices,
    physical_country,
    physical_amount,
    physical_currency,
    physical_commission_choice,
    physical_phone,
    physical_preview_choice,
)
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

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Global commands (outside conv)
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("faq", faq_command))
    dp.add_handler(CommandHandler("contact", contact_command))
    dp.add_handler(CommandHandler("about", about_command))
    dp.add_handler(CommandHandler("language", language_command))

    # Callback queries (for language switch)
    dp.add_handler(CallbackQueryHandler(language_callback, pattern=r"^set_lang_"))

    # Conversation
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                MessageHandler(Filters.text & ~Filters.command, main_menu)
            ],

            # AGENT SUBMENU
            AGENT_SUBMENU: [
                MessageHandler(Filters.text & ~Filters.command, agent_submenu),
            ],
            # Agent Importer
            AGENT_IMPORTER_COUNTRY: [
                MessageHandler(Filters.text & ~Filters.command, agent_importer_country),
            ],
            AGENT_IMPORTER_AMOUNT: [
                MessageHandler(Filters.text & ~Filters.command, agent_importer_amount),
            ],
            AGENT_IMPORTER_CURRENCY: [
                MessageHandler(Filters.text & ~Filters.command, agent_importer_currency),
            ],
            AGENT_IMPORTER_COMMISSION_CHOICE: [
                MessageHandler(Filters.text & ~Filters.command, agent_importer_commission_choice),
            ],
            AGENT_IMPORTER_INN: [
                MessageHandler(Filters.text & ~Filters.command, agent_importer_inn),
            ],
            AGENT_IMPORTER_PURPOSE: [
                MessageHandler(Filters.text & ~Filters.command, agent_importer_purpose),
            ],
            AGENT_IMPORTER_PHONE: [
                MessageHandler(Filters.text & ~Filters.command, agent_importer_phone),
            ],
            AGENT_IMPORTER_PREVIEW: [
                MessageHandler(Filters.text & ~Filters.command, agent_importer_preview_choice),
            ],

            # Agent Exporter
            AGENT_EXPORTER_COUNTRY: [
                MessageHandler(Filters.text & ~Filters.command, agent_exporter_country),
            ],
            AGENT_EXPORTER_AMOUNT: [
                MessageHandler(Filters.text & ~Filters.command, agent_exporter_amount),
            ],
            AGENT_EXPORTER_CURRENCY: [
                MessageHandler(Filters.text & ~Filters.command, agent_exporter_currency),
            ],
            AGENT_EXPORTER_PURPOSE: [
                MessageHandler(Filters.text & ~Filters.command, agent_exporter_purpose),
            ],
            AGENT_EXPORTER_COMMISSION_CHOICE: [
                MessageHandler(Filters.text & ~Filters.command, agent_exporter_commission_choice),
            ],
            AGENT_EXPORTER_SENDER_DETAILS: [
                MessageHandler(Filters.text & ~Filters.command, agent_exporter_sender_details),
            ],
            AGENT_EXPORTER_RECEIVER_DETAILS: [
                MessageHandler(Filters.text & ~Filters.command, agent_exporter_receiver_details),
            ],
            AGENT_EXPORTER_PHONE: [
                MessageHandler(Filters.text & ~Filters.command, agent_exporter_phone),
            ],
            AGENT_EXPORTER_PREVIEW: [
                MessageHandler(Filters.text & ~Filters.command, agent_exporter_preview_choice),
            ],

            # Importer
            IMPORTER_COUNTRY: [
                MessageHandler(Filters.text & ~Filters.command, importer_country),
            ],
            IMPORTER_AMOUNT: [
                MessageHandler(Filters.text & ~Filters.command, importer_amount),
            ],
            IMPORTER_CURRENCY: [
                MessageHandler(Filters.text & ~Filters.command, importer_currency),
            ],
            IMPORTER_COMMISSION_CHOICE: [
                MessageHandler(Filters.text & ~Filters.command, importer_commission_choice),
            ],
            IMPORTER_INN: [
                MessageHandler(Filters.text & ~Filters.command, importer_inn),
            ],
            IMPORTER_PURPOSE: [
                MessageHandler(Filters.text & ~Filters.command, importer_purpose),
            ],
            IMPORTER_PHONE: [
                MessageHandler(Filters.text & ~Filters.command, importer_phone),
            ],
            IMPORTER_PREVIEW: [
                MessageHandler(Filters.text & ~Filters.command, importer_preview_choice),
            ],

            # Exporter
            EXPORTER_COUNTRY: [
                MessageHandler(Filters.text & ~Filters.command, exporter_country),
            ],
            EXPORTER_AMOUNT: [
                MessageHandler(Filters.text & ~Filters.command, exporter_amount),
            ],
            EXPORTER_CURRENCY: [
                MessageHandler(Filters.text & ~Filters.command, exporter_currency),
            ],
            EXPORTER_PURPOSE: [
                MessageHandler(Filters.text & ~Filters.command, exporter_purpose),
            ],
            EXPORTER_COMMISSION_CHOICE: [
                MessageHandler(Filters.text & ~Filters.command, exporter_commission_choice),
            ],
            EXPORTER_SENDER_DETAILS: [
                MessageHandler(Filters.text & ~Filters.command, exporter_sender_details),
            ],
            EXPORTER_RECEIVER_DETAILS: [
                MessageHandler(Filters.text & ~Filters.command, exporter_receiver_details),
            ],
            EXPORTER_PHONE: [
                MessageHandler(Filters.text & ~Filters.command, exporter_phone),
            ],
            EXPORTER_PREVIEW: [
                MessageHandler(Filters.text & ~Filters.command, exporter_preview_choice),
            ],

            # Physical
            PHYSICAL_CHOICES: [
                MessageHandler(Filters.text & ~Filters.command, physical_choices),
            ],
            PHYSICAL_COUNTRY: [
                MessageHandler(Filters.text & ~Filters.command, physical_country),
            ],
            PHYSICAL_AMOUNT: [
                MessageHandler(Filters.text & ~Filters.command, physical_amount),
            ],
            PHYSICAL_CURRENCY: [
                MessageHandler(Filters.text & ~Filters.command, physical_currency),
            ],
            PHYSICAL_COMMISSION_CHOICE: [
                MessageHandler(Filters.text & ~Filters.command, physical_commission_choice),
            ],
            PHYSICAL_PHONE: [
                MessageHandler(Filters.text & ~Filters.command, physical_phone),
            ],
            PHYSICAL_PREVIEW: [
                MessageHandler(Filters.text & ~Filters.command, physical_preview_choice),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
            CommandHandler("menu", go_back_to_main_menu),
            CommandHandler("help", help_command),
            CommandHandler("contact", contact_command),
            CommandHandler("faq", faq_command),
        ],
    )

    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()