# src/translations.py

TRANSLATIONS = {
    'ru': {
        'select_language': '🌐 Выберите язык / Select language:',
        'language_russian': '🇷🇺 Русский',
        'language_english': '🇬🇧 English',
        'start_welcome': '🕰 Добро пожаловать в Digital Time Capsule!\n\nЯ помогу вам создать капсулу времени - отправить сообщение в будущее себе, другу или группе!',
        'main_menu': '📋 Главное меню',
        'create_capsule': 'Создать капсулу',
        'my_capsules': 'Мои капсулы',
        'subscription': 'Подписка',
        'settings': 'Настройки',
        'help': 'Помощь',
        'language': '🌐 Язык',
        'select_content_type': '📝 Выберите тип содержимого капсулы:',
        'content_text': '📄 Текст',
        'content_photo': '🖼 Фото',
        'content_video': '🎥 Видео',
        'content_document': '📎 Документ',
        'content_voice': '🎤 Голосовое сообщение',
        'back': '◀️ Назад',
        'cancel': '❌ Отмена',
        'send_content': 'Отправьте {type}:',
        'content_received': '✅ Содержимое получено!',
        'select_time': '⏰ Когда доставить капсулу?',
        'time_1hour': '1 час',
        'time_1day': '1 день',
        'time_1week': '1 неделя',
        'time_1month': '1 месяц',
        'time_3months': '3 месяца',
        'time_6months': '6 месяцев',
        'time_1year': '1 год',
        'time_custom': '📅 Выбрать дату',
        'enter_date': 'Введите дату в формате ДД.ММ.ГГГГ ЧЧ:ММ\nНапример: 31.12.2025 23:59',
        'invalid_date': '❌ Неверный формат даты. Попробуйте снова.',
        'date_too_far': '❌ Эта дата слишком далеко для вашего тарифа.\n\nБесплатный: до {days} дней\nПремиум: до {years} лет',
        'select_recipient': '👤 Кому отправить капсулу?',
        'recipient_self': '👤 Себе',
        'recipient_user': '👥 Другому пользователю',
        'recipient_group': '👨‍👩‍👧‍👦 В группу',
        'enter_user_id': 'Введите @username или ID пользователя:',
        'enter_group_id': 'Добавьте меня в группу и отправьте /group_id',
        'user_not_found': '❌ Пользователь не найден',
        'confirm_capsule': '✨ Подтвердите создание капсулы:\n\n📦 Тип: {type}\n⏰ Доставка: {time}\n👤 Получатель: {recipient}\n\nВсе верно?',
        'confirm_yes': '✅ Да, создать!',
        'confirm_no': '❌ Нет, отменить',
        'capsule_created': '🎉 Капсула создана!\n\nВаша капсула будет доставлена {time}',
        'capsule_cancelled': '❌ Создание капсулы отменено',
        'quota_exceeded': '⚠️ Превышен лимит!\n\n{message}\n\nОбновите подписку для снятия ограничений.',
        'upgrade_subscription': '⬆️ Обновить подписку',
        'no_capsules': 'У вас пока нет капсул',
        'capsule_list': '📦 Ваши капсулы ({count}/{limit}):',
        'capsule_item': '{emoji} {type} → {recipient}\nДоставка: {time}\nСоздана: {created}',
        'delete_capsule': '🗑 Удалить',
        'view_details': '👁 Подробнее',
        'subscription_info': '💎 Ваша подписка: {tier}\n\n{details}',
        'free_tier_details': '📊 Статистика:\n• Капсулы: {count}/{limit}\n• Хранилище: {used}/{total}\n• Срок хранения: до {days} дней',
        'premium_tier_details': '📊 Статистика:\n• Капсулы: {count} (безлимит)\n• Хранилище: {used}/{total}\n• Срок хранения: до {years} лет\n• Истекает: {expires}',
        'buy_premium_single': '💳 Одна капсула - {price}₽',
        'buy_premium_year': '💳 Год подписки - {price}₽',
        'buy_stars_single': '⭐ Одна капсула - {stars} звезд',
        'buy_stars_year': '⭐ Год подписки - {stars} звезд',
        'language_changed': '🌐 Язык изменен',
        'help_text': '❓ Помощь\n\nDigital Time Capsule позволяет создавать капсулы времени - сообщения, которые будут доставлены в будущем.\n\n🔐 Безопасность:\n• Все файлы шифруются\n• Хранение в Yandex S3\n• Никто не может прочитать ваши капсулы\n\n📋 Команды:\n/start - Главное меню\n/create - Создать капсулу\n/capsules - Мои капсулы\n/subscription - Подписка\n/help - Помощь',
        'delivery_title': '🎁 Капсула времени!',
        'delivery_text': 'Вы получили капсулу времени!\n\nСоздана: {created}\nОт: {sender}',
        'error_occurred': '❌ Произошла ошибка. Попробуйте позже.',
        'file_too_large': '❌ Файл слишком большой!\n\nМаксимальный размер:\n• Бесплатно: 10 МБ на все капсулы\n• Премиум: 1 ГБ на все капсулы',
        'select_recipient_enhanced': '👤 Кому отправить капсулу?',
        'recipient_user_list': '📋 Выбрать из списка',
        'enter_user_id_instruction': '👤 Введите @username или ID пользователя:\n\nПример:\n• @username\n• 123456789',
        'enter_group_id_instruction': '👨‍👩‍👧‍👦 Введите ID группы:\n\nПример:\n• -1001234567890\n• 1234567890 (я добавлю знак минус)',
        'invalid_recipient_id': '❌ Неверный ID получателя. Попробуйте снова.',
        'no_users_found': '❌ В базе нет других пользователей.\n\nПригласите друзей использовать бота!',
        'select_user_from_list': '📋 Выберите пользователя из списка:',
        'delivery_failed': '❌ Не удалось доставить капсулу получателю {recipient}.\n\nОшибка: {error}\n\nВозможные причины:\n• Пользователь заблокировал бота\n• Неверный ID группы\n• Бот исключен из группы',
        'persistent_menu_text': '🏠 **Главное меню**\n\nВыберите действие:',
        'back_to_menu': '🏠 В главное меню',
        'stats': 'Статистика',
        'user_stats': '📊 **Ваша статистика**\n\n📦 Всего капсул: **{capsules_total}**\n⏳ Активных: **{capsules_active}**\n💾 Хранилище: **{storage_used} МБ / {storage_max} МБ**\n💎 Подписка: **{subscription}**',
        'start_welcome_full':'🚀🕰 Добро пожаловать в Digital Time Capsule!\n\nВаш личный сервис для отправки сообщений в будущее. Безопасно. Зашифровано. Надежно.\n\n🔧 Технологии:\n• 🔐 Шифрование Fernet — военный уровень защиты\n• ☁️ Облачное хранилище Yandex S3 — ваши данные в безопасности\n• ⏰ Автоматическая доставка — точность до минуты\n• 🌍 Двуязычный интерфейс — русский и английский\n📊 Тарифы:\n• FREE: 3 капсулы, 10 МБ, до 1 года\n• PREMIUM: безлимит капсул, 1 ГБ, до 25 лет\n\n💎 Премиум от 20 звезд Telegram — цифровые платежи прямо в боте!\n\n⚡ Создайте первую капсулу за 30 секунд!',
        'buy_single_capsule': '💎 Купить 1 капсулу - {stars}⭐',
        'buy_pack_3': '📦 3 капсулы - {stars}⭐ (скидка {discount}%)',
        'buy_pack_10': '📦 10 капсул - {stars}⭐ (скидка {discount}%)',
        'buy_pack_25': '📦 25 капсул - {stars}⭐ (скидка {discount}%)',
        'buy_pack_100': '📦 100 капсул - {stars}⭐ (скидка {discount}%)',
        'buy_premium_month': '💎 Премиум Месяц - {stars}⭐ ({capsules} капсул)',
        'buy_premium_year': '💎 Премиум Год - {stars}⭐ ({capsules} капсул)',

        'no_capsule_balance': '❌ У вас нет капсул!\n\nКупите капсулы или подписку для создания капсул времени.',
        'buy_capsules': '💰 Купить капсулы',
        'pay_button': '💳 Оплатить {stars}⭐',

        'invoice_title_single': 'Одна капсула',
        'invoice_desc_single': 'Создайте одну капсулу времени любого типа',
        'invoice_title_pack': '{count} капсул',
        'invoice_desc_pack': 'Пакет из {count} капсул со скидкой {discount}%',
        'invoice_title_premium_month': 'Премиум на месяц',
        'invoice_desc_premium_month': 'Премиум подписка на 1 месяц + {capsules} капсул',
        'invoice_title_premium_year': 'Премиум на год',
        'invoice_desc_premium_year': 'Премиум подписка на 1 год + {capsules} капсул',
        'storage_limit_reached': '''❌ Превышен лимит хранилища!

💾 Использовано: {used_mb:.1f} МБ / {limit_mb:.0f} МБ

Освободите место или купите премиум подписку:
• FREE: 100 МБ
• PREMIUM: 500 МБ''',
        'payment_success': '🎉 Оплата успешна!\n\n✅ Добавлено капсул: {capsules}\n💎 Тип покупки: {type}',

        'free_subscription_details': '''📊 Статистика:
💎 Капсулы в балансе: {capsules}
💾 Хранилище: {used} / {total}
⏰ Срок доставки: до 1 года''',

        'premium_subscription_details': '''📊 Статистика:
💎 Капсулы в балансе: {capsules}
💾 Хранилище: {used} / {total}
⏰ Срок доставки: до 25 лет
📅 Действует до: {expires}''',

        'paysupport_text': '''💬 Поддержка по платежам

Если у вас проблемы с оплатой:
• Проверьте баланс: /subscription
• Для возврата: @your_support
• Укажите ID транзакции

⚠️ Политика возврата:
• Технические проблемы: возврат в течение 24ч
• Неиспользованные капсулы: пропорциональный возврат

⏱ Время ответа: до 24 часов'''
    },
    'en': {
        'select_language': '🌐 Выберите язык / Select language:',
        'language_russian': '🇷🇺 Русский',
        'language_english': '🇬🇧 English',
        'start_welcome': '🕰 Welcome to Digital Time Capsule!\n\nI will help you create time capsules - send messages to the future to yourself, a friend, or a group!',
        'main_menu': '📋 Main Menu',
        'create_capsule': 'Create Capsule',
        'my_capsules': 'My Capsules',
        'subscription': 'Subscription',
        'settings': 'Settings',
        'help': 'Help',
        'language': '🌐 Language',
        'select_content_type': '📝 Select capsule content type:',
        'content_text': '📄 Text',
        'content_photo': '🖼 Photo',
        'content_video': '🎥 Video',
        'content_document': '📎 Document',
        'content_voice': '🎤 Voice Message',
        'back': '◀️ Back',
        'cancel': '❌ Cancel',
        'send_content': 'Send {type}:',
        'content_received': '✅ Content received!',
        'select_time': '⏰ When to deliver the capsule?',
        'time_1hour': '1 hour',
        'time_1day': '1 day',
        'time_1week': '1 week',
        'time_1month': '1 month',
        'time_3months': '3 months',
        'time_6months': '6 months',
        'time_1year': '1 year',
        'time_custom': '📅 Choose date',
        'enter_date': 'Enter date in format DD.MM.YYYY HH:MM\nExample: 31.12.2025 23:59',
        'invalid_date': '❌ Invalid date format. Try again.',
        'date_too_far': '❌ This date is too far for your plan.\n\nFree: up to {days} days\nPremium: up to {years} years',
        'select_recipient': '👤 Who will receive the capsule?',
        'recipient_self': '👤 Myself',
        'recipient_user': '👥 Another user',
        'recipient_group': '👨‍👩‍👧‍👦 To a group',
        'enter_user_id': 'Enter @username or user ID:',
        'enter_group_id': 'Add me to the group and send /group_id',
        'user_not_found': '❌ User not found',
        'confirm_capsule': '✨ Confirm capsule creation:\n\n📦 Type: {type}\n⏰ Delivery: {time}\n👤 Recipient: {recipient}\n\nIs everything correct?',
        'confirm_yes': '✅ Yes, create!',
        'confirm_no': '❌ No, cancel',
        'capsule_created': '🎉 Capsule created!\n\nYour capsule will be delivered on {time}',
        'capsule_cancelled': '❌ Capsule creation cancelled',
        'quota_exceeded': '⚠️ Limit exceeded!\n\n{message}\n\nUpgrade your subscription to remove limits.',
        'upgrade_subscription': '⬆️ Upgrade Subscription',
        'no_capsules': 'You have no capsules yet',
        'capsule_list': '📦 Your capsules ({count}/{limit}):',
        'capsule_item': '{emoji} {type} → {recipient}\nDelivery: {time}\nCreated: {created}',
        'delete_capsule': '🗑 Delete',
        'view_details': '👁 Details',
        'subscription_info': '💎 Your subscription: {tier}\n\n{details}',
        'free_tier_details': '📊 Statistics:\n• Capsules: {count}/{limit}\n• Storage: {used}/{total}\n• Storage period: up to {days} days',
        'premium_tier_details': '📊 Statistics:\n• Capsules: {count} (unlimited)\n• Storage: {used}/{total}\n• Storage period: up to {years} years\n• Expires: {expires}',
        'buy_premium_single': '💳 Single capsule - {price}₽',
        'buy_premium_year': '💳 Yearly subscription - {price}₽',
        'buy_stars_single': '⭐ Single capsule - {stars} stars',
        'buy_stars_year': '⭐ Yearly subscription - {stars} stars',
        'language_changed': '🌐 Language changed',
        'help_text': '❓ Help\n\nDigital Time Capsule lets you create time capsules - messages that will be delivered in the future.\n\n🔐 Security:\n• All files are encrypted\n• Stored in Yandex S3\n• No one can read your capsules\n\n📋 Commands:\n/start - Main menu\n/create - Create capsule\n/capsules - My capsules\n/subscription - Subscription\n/help - Help',
        'delivery_title': '🎁 Time Capsule!',
        'delivery_text': 'You received a time capsule!\n\nCreated: {created}\nFrom: {sender}',
        'error_occurred': '❌ An error occurred. Try again later.',
        'file_too_large': '❌ File is too large!\n\nMax size:\n• Free: 10 MB for all capsules\n• Premium: 1 GB for all capsules',
        'select_recipient_enhanced': '👤 Who will receive the capsule?',
        'recipient_user_list': '📋 Choose from list',
        'enter_user_id_instruction': '👤 Enter @username or user ID:\n\nExample:\n• @username\n• 123456789',
        'enter_group_id_instruction': '👨‍👩‍👧‍👦 Enter group ID:\n\nExample:\n• -1001234567890\n• 1234567890 (I will add minus sign)',
        'invalid_recipient_id': '❌ Invalid recipient ID. Try again.',
        'no_users_found': '❌ No other users in database.\n\nInvite friends to use the bot!',
        'select_user_from_list': '📋 Choose user from list:',
        'delivery_failed': '❌ Failed to deliver capsule to {recipient}.\n\nError: {error}\n\nPossible reasons:\n• User blocked the bot\n• Invalid group ID\n• Bot was removed from group',
        'persistent_menu_text': '🏠 **Main Menu**\n\nChoose an action:',
        'back_to_menu': '🏠 Back to menu',
        'stats': 'Statistics',
        'user_stats': '📊 **Your Statistics**\n\n📦 Total capsules: **{capsules_total}**\n⏳ Active: **{capsules_active}**\n💾 Storage: **{storage_used} MB / {storage_max} MB**\n💎 Subscription: **{subscription}**',
        'start_welcome_full':'🚀🕰 Welcome to Digital Time Capsule!\n\nYour personal service for sending messages to the future. Secure. Encrypted. Reliable.\n\n🔧 Technology:\n• 🔐 Fernet encryption — military-grade security\n• ☁️ Yandex S3 cloud storage — your data is safe\n• ⏰ Automatic delivery — accurate to the minute\n• 🌍 Bilingual interface — Russian and English\n\n📊 Plans:\n• FREE: 3 capsules, 10 MB, up to 1 year\n• PREMIUM: unlimited capsules, 1 GB, up to 25 years\n\n💎 Premium from 20 Telegram Stars — digital payments right in the bot!\n\n⚡ Create your first capsule in 30 seconds!',
        'buy_single_capsule': '💎 Buy 1 capsule - {stars}⭐',
        'buy_pack_3': '📦 3 capsules - {stars}⭐ ({discount}% off)',
        'buy_pack_10': '📦 10 capsules - {stars}⭐ ({discount}% off)',
        'buy_pack_25': '📦 25 capsules - {stars}⭐ ({discount}% off)',
        'buy_pack_100': '📦 100 capsules - {stars}⭐ ({discount}% off)',
        'buy_premium_month': '💎 Premium Month - {stars}⭐ ({capsules} capsules)',
        'buy_premium_year': '💎 Premium Year - {stars}⭐ ({capsules} capsules)',

        'no_capsule_balance': '❌ You have no capsules!\n\nBuy capsules or subscription to create time capsules.',
        'buy_capsules': '💰 Buy Capsules',
        'pay_button': '💳 Pay {stars}⭐',

        'invoice_title_single': 'One Capsule',
        'invoice_desc_single': 'Create one time capsule of any type',
        'invoice_title_pack': '{count} Capsules',
        'invoice_desc_pack': 'Pack of {count} capsules with {discount}% discount',
        'invoice_title_premium_month': 'Premium Month',
        'invoice_desc_premium_month': 'Premium subscription for 1 month + {capsules} capsules',
        'invoice_title_premium_year': 'Premium Year',
        'invoice_desc_premium_year': 'Premium subscription for 1 year + {capsules} capsules',
        'storage_limit_reached': '''❌ Storage limit exceeded!

💾 Used: {used_mb:.1f} MB / {limit_mb:.0f} MB

Free up space or buy premium subscription:
• FREE: 100 MB
• PREMIUM: 500 MB''',
        'payment_success': '🎉 Payment successful!\n\n✅ Capsules added: {capsules}\n💎 Purchase type: {type}',

        'free_subscription_details': '''📊 Statistics:
💎 Capsule balance: {capsules}
💾 Storage: {used} / {total}
⏰ Delivery period: up to 1 year''',

        'premium_subscription_details': '''📊 Statistics:
💎 Capsule balance: {capsules}
💾 Storage: {used} / {total}
⏰ Delivery period: up to 25 years
📅 Valid until: {expires}''',

        'paysupport_text': '''💬 Payment Support

If you have payment issues:
• Check balance: /subscription
• For refunds: @your_support
• Include transaction ID

⚠️ Refund Policy:
• Technical issues: refund within 24h
• Unused capsules: prorated refund

⏱ Response time: within 24 hours'''
        }
}

def t(lang: str, key: str, **kwargs) -> str:
    """Get translated text"""
    text = TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)
    return text.format(**kwargs) if kwargs else text
