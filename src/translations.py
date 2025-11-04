# src/translations.py

TRANSLATIONS = {
    'ru': {
        # Main UI
        'start_message': 'Добро пожаловать в Digital Time Capsule! 🕰\n\nОтправляйте сообщения в будущее себе или близким.\n\nВыберите язык / Choose language:',
        'language_selected': 'Язык установлен: русский 🇷🇺',
        'main_menu': 'Главное меню',
        'back': 'Назад',
        'cancel': 'Отмена',
        'yes': 'Да',
        'no': 'Нет',
        
        # Menu items
        'create_capsule': 'Создать капсулу',
        'my_capsules': 'Мои капсулы', 
        'subscription': 'Подписка',
        'settings': 'Настройки',
        'help': 'Помощь',
        
        # Content types
        'content_text': 'Текст',
        'content_photo': 'Фото',
        'content_video': 'Видео', 
        'content_document': 'Документ',
        'content_voice': 'Голосовое сообщение',
        
        # Time options
        'time_1hour': '1 час',
        'time_1day': '1 день',
        'time_1week': '1 неделя',
        'time_1month': '1 месяц',
        'time_3months': '3 месяца',
        'time_6months': '6 месяцев',
        'time_1year': '1 год',
        'time_5years': '5 лет',
        'time_10years': '10 лет',
        'time_25years': '25 лет',
        'time_custom': 'Другое время',
        
        # Recipients
        'recipient_self': 'Себе',
        'forward_prompt': 'Перешлите сообщение из чата/канала или напишите @username получателя:',
        'forward_error': 'Пожалуйста, перешлите сообщение из чата или напишите @username',
        
        # Confirmation
        'confirm_capsule': 'Подтвердите создание капсулы:\n\n📝 Тип: {type}\n⏰ Доставка: {time}\n👤 Получатель: {recipient}',
        'confirm_yes': 'Создать',
        'confirm_no': 'Отменить',
        
        # Creation flow
        'select_content_type': 'Выберите тип содержимого капсулы:',
        'send_content': 'Отправьте {type}:',
        'content_received': 'Содержимое получено! ✅',
        'select_time': 'Выберите время доставки:',
        'enter_date': 'Введите дату и время в формате:\n\nДД.ММ.ГГГГ ЧЧ:ММ\n\nНапример: 25.12.2024 18:00',
        
        # Success/Error messages  
        'capsule_created': 'Капсула создана! 🎉\nДоставка: {time}',
        'capsule_created_with_link': 'Капсула создана! 🎉\nПолучатель: {username}\nДоставка: {time}\n\nОтправьте получателю эту ссылку:\n{invite_link}',
        'capsule_for_group_created': 'Капсула для группы "{group_name}" создана! 🎉\nДоставка: {delivery_time}',
        'creation_cancelled': 'Создание капсулы отменено.',
        'error_occurred': 'Произошла ошибка. Попробуйте еще раз.',
        'insufficient_balance': 'Недостаточно капсул! Купите капсулы в разделе "Подписка".',
        'no_capsule_balance': 'У вас нет доступных капсул! Купите их в разделе "Подписка".',
        
        # Subscription
        'buy_capsules': 'Купить капсулы',
        'upgrade_premium': 'Оформить Premium',
        'subscription_menu': 'Управление подпиской',
        
        # Storage
        'storage_limit_reached': 'Достигнут лимит хранилища ({limit})! Удалите старые капсулы или оформите Premium.',
        'file_too_large': 'Файл слишком большой! Максимум 50 МБ.',
        
        # Time limits
        'time_limit_exceeded': 'Превышен лимит времени! Оформите Premium для доставки до 25 лет.',
        'date_must_be_future': 'Дата должна быть в будущем!',
        'invalid_date_format': 'Неверный формат даты! Используйте ДД.ММ.ГГГГ ЧЧ:ММ',
        
        # Validation
        'invalid_username': 'Неверное имя пользователя!',
        'invalid_chat_id': 'Неверный ID чата!',
        'bot_not_in_chat': 'Бот не является участником чата "{chat_title}"',
        'no_post_rights': 'У бота нет прав на отправку сообщений в канал "{chat_title}"',
        
        # DELIVERY MESSAGES - FIXED TRANSLATIONS
        'capsule_delivered_title': 'Капсула времени доставлена!',
        'from': 'От',
        'created': 'Создано',
        'capsule_has_media': '[Медиафайл]',
        
        # Delivery notifications
        'delivery_pending_notification': 'Капсула ожидает активации пользователем {username}.\n\nОтправьте ему эту ссылку:\n{invite_link}',
        'delivery_failed_blocked': 'Не удалось доставить капсулу: пользователь заблокировал бота.',
        'delivery_failed_invalid_chat': 'Не удалось доставить капсулу: чат не найден или недоступен.',
        'delivery_failed_error': 'Ошибка при доставке капсулы.',
        'group_not_member': 'Не удалось доставить капсулу: бот больше не участник группы.',
        
        # Ideas UI (existing)
        'ideas_button': 'Идеи',
        'ideas_menu_title': 'Выберите категорию идей',
        'ideas_select_template_from': 'Выберите идею из категории',
        'ideas_preset_time': 'Предзаполнённое время доставки',
        'ideas_hints': 'Подсказки',
        'ideas_use_template': 'Использовать',
        'ideas_edit_text': 'Редактировать текст',
        'ideas_enter_text': 'Отправьте текст для капсулы:',
        
        # Categories
        'ideas_category_self_motivation': 'Самомотивация',
        'ideas_category_holidays': 'Праздники', 
        'ideas_category_daily_reflection': 'Подведение итогов',
        'ideas_category_relationships': 'Отношения',
        'ideas_category_goals_plans': 'Цели и планы',
        'ideas_category_memories': 'Воспоминания',
    },
    
    'en': {
        # Main UI
        'start_message': 'Welcome to Digital Time Capsule! 🕰\n\nSend messages to the future for yourself or loved ones.\n\nChoose language:',
        'language_selected': 'Language set: English 🇺🇸',
        'main_menu': 'Main Menu',
        'back': 'Back',
        'cancel': 'Cancel',
        'yes': 'Yes',
        'no': 'No',
        
        # Menu items
        'create_capsule': 'Create Capsule',
        'my_capsules': 'My Capsules',
        'subscription': 'Subscription',
        'settings': 'Settings', 
        'help': 'Help',
        
        # Content types
        'content_text': 'Text',
        'content_photo': 'Photo',
        'content_video': 'Video',
        'content_document': 'Document', 
        'content_voice': 'Voice Message',
        
        # Time options
        'time_1hour': '1 Hour',
        'time_1day': '1 Day',
        'time_1week': '1 Week',
        'time_1month': '1 Month',
        'time_3months': '3 Months',
        'time_6months': '6 Months', 
        'time_1year': '1 Year',
        'time_5years': '5 Years',
        'time_10years': '10 Years',
        'time_25years': '25 Years',
        'time_custom': 'Custom Time',
        
        # Recipients
        'recipient_self': 'To Myself',
        'forward_prompt': 'Forward a message from chat/channel or type @username of recipient:',
        'forward_error': 'Please forward a message from chat or type @username',
        
        # Confirmation 
        'confirm_capsule': 'Confirm capsule creation:\n\n📝 Type: {type}\n⏰ Delivery: {time}\n👤 Recipient: {recipient}',
        'confirm_yes': 'Create',
        'confirm_no': 'Cancel',
        
        # Creation flow
        'select_content_type': 'Select capsule content type:',
        'send_content': 'Send {type}:',
        'content_received': 'Content received! ✅',
        'select_time': 'Select delivery time:',
        'enter_date': 'Enter date and time in format:\n\nDD.MM.YYYY HH:MM\n\nExample: 25.12.2024 18:00',
        
        # Success/Error messages
        'capsule_created': 'Capsule created! 🎉\nDelivery: {time}',
        'capsule_created_with_link': 'Capsule created! 🎉\nRecipient: {username}\nDelivery: {time}\n\nSend this link to recipient:\n{invite_link}',
        'capsule_for_group_created': 'Capsule for group "{group_name}" created! 🎉\nDelivery: {delivery_time}',
        'creation_cancelled': 'Capsule creation cancelled.',
        'error_occurred': 'An error occurred. Please try again.',
        'insufficient_balance': 'Insufficient capsules! Buy capsules in "Subscription" section.',
        'no_capsule_balance': 'You have no available capsules! Buy them in "Subscription" section.',
        
        # Subscription
        'buy_capsules': 'Buy Capsules',
        'upgrade_premium': 'Upgrade to Premium',
        'subscription_menu': 'Manage Subscription',
        
        # Storage
        'storage_limit_reached': 'Storage limit reached ({limit})! Delete old capsules or upgrade to Premium.',
        'file_too_large': 'File too large! Maximum 50 MB.',
        
        # Time limits
        'time_limit_exceeded': 'Time limit exceeded! Upgrade to Premium for delivery up to 25 years.',
        'date_must_be_future': 'Date must be in the future!',
        'invalid_date_format': 'Invalid date format! Use DD.MM.YYYY HH:MM',
        
        # Validation
        'invalid_username': 'Invalid username!',
        'invalid_chat_id': 'Invalid chat ID!',
        'bot_not_in_chat': 'Bot is not a member of chat "{chat_title}"',
        'no_post_rights': 'Bot has no rights to post messages in channel "{chat_title}"',
        
        # DELIVERY MESSAGES - FIXED TRANSLATIONS
        'capsule_delivered_title': 'Time Capsule Delivered!',
        'from': 'From',
        'created': 'Created',
        'capsule_has_media': '[Media File]',
        
        # Delivery notifications
        'delivery_pending_notification': 'Capsule is waiting for activation by user {username}.\n\nSend them this link:\n{invite_link}',
        'delivery_failed_blocked': 'Failed to deliver capsule: user blocked the bot.',
        'delivery_failed_invalid_chat': 'Failed to deliver capsule: chat not found or unavailable.',
        'delivery_failed_error': 'Error delivering capsule.',
        'group_not_member': 'Failed to deliver capsule: bot is no longer a group member.',
        
        # Ideas UI (existing)
        'ideas_button': 'Ideas',
        'ideas_menu_title': 'Choose an ideas category',
        'ideas_select_template_from': 'Choose a template from',
        'ideas_preset_time': 'Preset delivery time',
        'ideas_hints': 'Hints',
        'ideas_use_template': 'Use template',
        'ideas_edit_text': 'Edit text',
        'ideas_enter_text': 'Send text for the capsule:',
        
        # Categories
        'ideas_category_self_motivation': 'Self-motivation',
        'ideas_category_holidays': 'Holidays',
        'ideas_category_daily_reflection': 'Daily reflection',
        'ideas_category_relationships': 'Relationships',
        'ideas_category_goals_plans': 'Goals & plans',
        'ideas_category_memories': 'Memories',
    }
}

def t(lang: str, key: str, **kwargs) -> str:
    """Get translated string with optional formatting"""
    try:
        if lang not in TRANSLATIONS:
            lang = 'en'  # Fallback to English
            
        translation = TRANSLATIONS[lang].get(key, TRANSLATIONS['en'].get(key, key))
        
        if kwargs:
            return translation.format(**kwargs)
        return translation
        
    except Exception as e:
        print(f"Translation error for key '{key}' in lang '{lang}': {e}")
        return key  # Return key as fallback


# Helper function to get available languages
def get_available_languages():
    return list(TRANSLATIONS.keys())