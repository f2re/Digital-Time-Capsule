# src/utils/legal_helper.py

from ..config import (
    SELLER_NAME_RU, SELLER_NAME_EN, SELLER_INN, SELLER_LOCATION_RU, SELLER_LOCATION_EN,
    SUPPORT_EMAIL, REFUND_EMAIL, SUPPORT_TELEGRAM, SUPPORT_HOURS_RU, SUPPORT_HOURS_EN,
    RETURN_DAYS, RETURN_DAYS_PREMIUM, RESPONSE_TIME_HOURS,
    DELIVERY_ACCURACY_MINUTES, CAPSULE_PRICE_STARS, CAPSULE_PRICE_RUB, CAPSULE_PRICE_USD,
    CAPSULE_PACKS, PREMIUM_MONTH_STARS, PREMIUM_MONTH_RUB, PREMIUM_MONTH_USD,
    PREMIUM_MONTH_CAPSULES, PREMIUM_YEAR_STARS, PREMIUM_YEAR_RUB, PREMIUM_YEAR_USD,
    PREMIUM_YEAR_CAPSULES, FREE_STORAGE_LIMIT, PREMIUM_STORAGE_LIMIT,
    FREE_TIME_LIMIT_DAYS, PREMIUM_TIME_LIMIT_DAYS
)


def get_seller_info_text(lang: str) -> str:
    """Generate seller info text from config"""

    if lang == 'ru':
        return f'''📋 <b>ИНФОРМАЦИЯ О ПРОДАВЦЕ</b>

<b>Наименование:</b> {SELLER_NAME_RU}
<b>ИНН:</b> <code>{SELLER_INN}</code>
<b>Местоположение:</b> {SELLER_LOCATION_RU}

<b>Контактная информация:</b>
📧 Email: <code>{SUPPORT_EMAIL}</code>
📱 Telegram: {SUPPORT_TELEGRAM}
🌐 Тех-поддержка: /support

<b>Режим работы поддержки:</b>
{SUPPORT_HOURS_RU}

<b>Время ответа:</b>
Среднее время ответа: {RESPONSE_TIME_HOURS} час(ов)

<b>Способы связи:</b>
Электронная почта является основным каналом связи. Обращайтесь в техподдержку через команду /support.
'''
    else:
        return f'''📋 <b>SELLER INFORMATION</b>

<b>Business Name:</b> {SELLER_NAME_EN}
<b>Tax ID:</b> <code>{SELLER_INN}</code>
<b>Location:</b> {SELLER_LOCATION_EN}

<b>Contact Information:</b>
📧 Email: <code>{SUPPORT_EMAIL}</code>
📱 Telegram: {SUPPORT_TELEGRAM}
🌐 Technical Support: /support

<b>Support Hours:</b>
{SUPPORT_HOURS_EN}

<b>Response Time:</b>
Average response time: {RESPONSE_TIME_HOURS} hour(s)

<b>Ways to Contact:</b>
Email is the primary communication channel. Contact technical support using /support command.
'''


def get_refund_policy_text(lang: str) -> str:
    """Generate refund policy text with dynamic values from config"""

    if lang == 'ru':
        return f'''💰 <b>ПОЛИТИКА ВОЗВРАТА СРЕДСТВ</b>

<b>1. ОБЩИЕ ПОЛОЖЕНИЯ</b>

Возврат денежных средств осуществляется в соответствии со ст. 32 Закона РФ "О защите прав потребителей". Покупатель вправе отказаться от услуги до момента ее фактического использования.

<b>2. УСЛОВИЯ ВОЗВРАТА</b>

Возврат возможен в течение <b>{RETURN_DAYS} календарных дней</b> с момента оплаты:

✅ <b>Одиночная капсула ({CAPSULE_PRICE_STARS} ⭐ / {CAPSULE_PRICE_RUB}₽):</b>
• Если капсула не была создана — возврат 100%
• Если создана, но не доставлена — возврат 50%
• После доставки — возврат невозможен

✅ <b>Пакеты капсул:</b>
• Если ни одна капсула не использована — возврат 100%
• Частичный возврат пропорционально неиспользованным капсулам

✅ <b>Premium подписка:</b>
• В первые {RETURN_DAYS_PREMIUM} дня — возврат 100%
• С {RETURN_DAYS_PREMIUM + 1} по {RETURN_DAYS} день — возврат 50%
• После {RETURN_DAYS} дней — возврат невозможен

<b>3. ПРОЦЕДУРА ВОЗВРАТА</b>

Для возврата средств:
1. Напишите в техподдержку: /support
2. Укажите номер заказа и причину возврата
3. Приложите подтверждение оплаты

<b>Срок рассмотрения:</b> 3 рабочих дня
<b>Срок возврата:</b> до 10 рабочих дней

<b>4. СПОСОБ ВОЗВРАТА</b>

Возврат осуществляется на ту же карту/счет.

<b>5. КОНТАКТЫ</b>

📧 Email: <code>{REFUND_EMAIL}</code>
💬 Telegram: /support
⏰ Время ответа: до {RESPONSE_TIME_HOURS} часов

<b>Дата последнего обновления:</b> 05.11.2025
'''
    else:
        return f'''💰 <b>REFUND POLICY</b>

<b>1. GENERAL PROVISIONS</b>

Refunds processed per consumer protection laws. Customer may refuse service before use.

<b>2. REFUND CONDITIONS</b>

Refund available within <b>{RETURN_DAYS} calendar days</b> from payment:

✅ <b>Single Capsule ({CAPSULE_PRICE_STARS}⭐ / ${CAPSULE_PRICE_USD}):</b>
• If not created — 100% refund
• If created but not delivered — 50% refund
• After delivery — no refund

✅ <b>Capsule Packs:</b>
• If no capsules used — 100% refund
• Partial refund proportional to unused

✅ <b>Premium Subscription:</b>
• First {RETURN_DAYS_PREMIUM} days — 100% refund
• Days {RETURN_DAYS_PREMIUM + 1}-{RETURN_DAYS} — 50% refund
• After {RETURN_DAYS} days — no refund

<b>3. REFUND PROCEDURE</b>

To request refund:
1. Contact support: /support
2. Provide order number and reason
3. Attach payment confirmation

<b>Review period:</b> 3 business days
<b>Processing:</b> up to 10 business days

<b>4. REFUND METHOD</b>

Refund to original payment method.

<b>5. CONTACTS</b>

📧 Email: <code>{REFUND_EMAIL}</code>
💬 Telegram: /support
⏰ Response: {RESPONSE_TIME_HOURS} hours

<b>Last updated:</b> 05.11.2025
'''


def get_product_catalog_text(lang: str) -> str:
    """Generate product catalog with all prices from config"""

    pack_3 = CAPSULE_PACKS['pack_3']
    pack_10 = CAPSULE_PACKS['pack_10']
    pack_25 = CAPSULE_PACKS['pack_25']
    pack_100 = CAPSULE_PACKS['pack_100']

    if lang == 'ru':
        return f'''📦 <b>КАТАЛОГ УСЛУГ</b>

<b>1. ОДИНОЧНАЯ КАПСУЛА ВРЕМЕНИ</b>
💎 Цена: {CAPSULE_PRICE_STARS}⭐ / {CAPSULE_PRICE_RUB}₽

Цифровая капсула времени — сервис отложенной доставки сообщения в будущее.

<b>Что входит:</b>
• 1 капсула времени (текст, фото, видео, документ, голос)
• Шифрование AES-128
• Гарантия доставки в срок
• Хранилище: {FREE_STORAGE_LIMIT // (1024*1024)}МБ (свободный аккаунт)

---

<b>2. НАБОР ИЗ 3 КАПСУЛ</b>
💎 Цена: {pack_3['price_stars']}⭐ / {pack_3['price_rub']}₽
📊 Скидка: {pack_3['discount']}%
💰 По одной: {CAPSULE_PRICE_STARS * 3}⭐

<b>3. НАБОР ИЗ 10 КАПСУЛ</b>
💎 Цена: {pack_10['price_stars']}⭐ / {pack_10['price_rub']}₽
📊 Скидка: {pack_10['discount']}%
💰 По одной: {CAPSULE_PRICE_STARS * 10}⭐

<b>4. НАБОР ИЗ 25 КАПСУЛ</b>
💎 Цена: {pack_25['price_stars']}⭐ / {pack_25['price_rub']}₽
📊 Скидка: {pack_25['discount']}%
💰 По одной: {CAPSULE_PRICE_STARS * 25}⭐

<b>5. НАБОР ИЗ 100 КАПСУЛ</b>
💎 Цена: {pack_100['price_stars']}⭐ / {pack_100['price_rub']}₽
📊 Скидка: {pack_100['discount']}%
💰 По одной: {CAPSULE_PRICE_STARS * 100}⭐

---

<b>6. PREMIUM ПОДПИСКА (1 МЕСЯЦ)</b>
💎 Цена: {PREMIUM_MONTH_STARS}⭐ / {PREMIUM_MONTH_RUB}₽

<b>Включает:</b>
• {PREMIUM_MONTH_CAPSULES} капсул в месяц
• Хранилище: {PREMIUM_STORAGE_LIMIT // (1024*1024)}МБ
• Срок доставки: до {PREMIUM_TIME_LIMIT_DAYS // 365} лет
• Приоритетная поддержка

---

<b>7. PREMIUM ПОДПИСКА (1 ГОД)</b>
💎 Цена: {PREMIUM_YEAR_STARS}⭐ / {PREMIUM_YEAR_RUB}₽
💰 Экономия: {PREMIUM_MONTH_STARS * 12 - PREMIUM_YEAR_STARS}⭐ ({int(((PREMIUM_MONTH_STARS * 12 - PREMIUM_YEAR_STARS) / (PREMIUM_MONTH_STARS * 12)) * 100)}%)

<b>Включает:</b>
• {PREMIUM_YEAR_CAPSULES} капсул в год ({PREMIUM_YEAR_CAPSULES // 12} в месяц)
• Хранилище: {PREMIUM_STORAGE_LIMIT // (1024*1024)}МБ
• Срок доставки: до {PREMIUM_TIME_LIMIT_DAYS // 365} лет
• Приоритетная поддержка

---

<b>ГАРАНТИИ:</b>
✅ Доставка точно в срок
✅ Защита данных шифрованием
✅ Техподдержка {SUPPORT_HOURS_RU}
✅ Возврат в течение {RETURN_DAYS} дней при неиспользовании
'''
    else:
        return f'''📦 <b>SERVICE CATALOG</b>

<b>1. SINGLE TIME CAPSULE</b>
💎 Price: {CAPSULE_PRICE_STARS}⭐ / ${CAPSULE_PRICE_USD}

A digital time capsule service for scheduling message delivery.

<b>What\'s Included:</b>
• 1 time capsule (text, photo, video, document, voice)
• AES-128 encryption
• Guaranteed on-time delivery
• Storage: {FREE_STORAGE_LIMIT // (1024*1024)}MB (free account)

---

<b>2. PACK OF 3 CAPSULES</b>
💎 Price: {pack_3['price_stars']}⭐ / ${pack_3['price_usd']}
📊 Discount: {pack_3['discount']}%
💰 Individual: {CAPSULE_PRICE_STARS * 3}⭐

<b>3. PACK OF 10 CAPSULES</b>
💎 Price: {pack_10['price_stars']}⭐ / ${pack_10['price_usd']}
📊 Discount: {pack_10['discount']}%
💰 Individual: {CAPSULE_PRICE_STARS * 10}⭐

<b>4. PACK OF 25 CAPSULES</b>
💎 Price: {pack_25['price_stars']}⭐ / ${pack_25['price_usd']}
📊 Discount: {pack_25['discount']}%
💰 Individual: {CAPSULE_PRICE_STARS * 25}⭐

<b>5. PACK OF 100 CAPSULES</b>
💎 Price: {pack_100['price_stars']}⭐ / ${pack_100['price_usd']}
📊 Discount: {pack_100['discount']}%
💰 Individual: {CAPSULE_PRICE_STARS * 100}⭐

---

<b>6. PREMIUM SUBSCRIPTION (1 MONTH)</b>
💎 Price: {PREMIUM_MONTH_STARS}⭐ / ${PREMIUM_MONTH_USD}

<b>Includes:</b>
• {PREMIUM_MONTH_CAPSULES} capsules per month
• Storage: {PREMIUM_STORAGE_LIMIT // (1024*1024)}MB
• Delivery period: up to {PREMIUM_TIME_LIMIT_DAYS // 365} years
• Priority support

---

<b>7. PREMIUM SUBSCRIPTION (1 YEAR)</b>
💎 Price: {PREMIUM_YEAR_STARS}⭐ / ${PREMIUM_YEAR_USD}
💰 Save: {PREMIUM_MONTH_STARS * 12 - PREMIUM_YEAR_STARS}⭐ ({int(((PREMIUM_MONTH_STARS * 12 - PREMIUM_YEAR_STARS) / (PREMIUM_MONTH_STARS * 12)) * 100)}%)

<b>Includes:</b>
• {PREMIUM_YEAR_CAPSULES} capsules per year ({PREMIUM_YEAR_CAPSULES // 12} per month)
• Storage: {PREMIUM_STORAGE_LIMIT // (1024*1024)}MB
• Delivery period: up to {PREMIUM_TIME_LIMIT_DAYS // 365} years
• Priority support

---

<b>GUARANTEES:</b>
✅ On-time delivery
✅ Data encryption protection
✅ Support {SUPPORT_HOURS_EN}
✅ Refund within {RETURN_DAYS} days if unused
'''


def get_privacy_policy_text(lang: str) -> str:
    """Generate privacy policy with data retention info"""

    if lang == 'ru':
        return f'''🔒 <b>ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ</b>

<b>1. ВВЕДЕНИЕ</b>

Мы уважаем вашу конфиденциальность и обязуемся защищать ваши личные данные.

<b>2. СОБИРАЕМЫЕ ДАННЫЕ</b>

Мы собираем следующую информацию:
• Telegram ID
• Имя пользователя (username)
• Дата и время регистрации
• Содержимое загруженных капсул

<b>3. ИСПОЛЬЗОВАНИЕ ДАННЫХ</b>

Ваши данные используются исключительно для:
• Предоставления услуги
• Связи с вами
• Улучшения качества сервиса
• Соблюдения законодательства

<b>4. ЗАЩИТА ДАННЫХ</b>

✅ Все данные зашифрованы по стандарту AES-128
✅ Хранение на защищенных серверах
✅ Доступ ограничен только необходимым персоналом
✅ Регулярное резервное копирование

<b>5. ОБРАБОТКА ПЕРСОНАЛЬНЫХ ДАННЫХ</b>

Обработка осуществляется в соответствии с ФЗ-152 "О персональных данных".

<b>6. ПЕРЕДАЧА ТРЕТЬИМ ЛИЦАМ</b>

Ваши данные НЕ передаются третьим лицам без вашего согласия, кроме:
• Обработки платежей (Robokassa, Telegram Stars)
• Требований закона или суда

<b>7. УДАЛЕНИЕ ДАННЫХ</b>

Вы можете запросить удаление всех ваших данных через команду /support.

<b>8. СРОКИ ХРАНЕНИЯ</b>

• Активные капсулы: до момента доставки
• Доставленные капсулы: после доставки уничтожаются автоматически
• История платежей: 3 года (по требованиям налогового законодательства)

<b>9. КОНТАКТЫ</b>

По вопросам конфиденциальности пишите: /support
Ответ: до {RESPONSE_TIME_HOURS} часов
'''
    else:
        return f'''🔒 <b>PRIVACY POLICY</b>

<b>1. INTRODUCTION</b>

We respect your privacy and are committed to protecting your personal data.

<b>2. DATA WE COLLECT</b>

We collect the following information:
• Telegram ID
• Username
• Registration date and time
• Uploaded capsule content

<b>3. HOW WE USE DATA</b>

Your data is used exclusively for:
• Providing the service
• Communication with you
• Improving service quality
• Compliance with laws

<b>4. DATA PROTECTION</b>

✅ All data encrypted with AES-128 standard
✅ Storage on secure servers
✅ Limited access to necessary personnel
✅ Regular backups

<b>5. PERSONAL DATA PROCESSING</b>

Processing complies with applicable data protection regulations.

<b>6. THIRD PARTY SHARING</b>

Your data is NOT shared with third parties without consent, except for:
• Payment processing (Robokassa, Telegram Stars)
• Legal or court requirements

<b>7. DATA DELETION</b>

You can request deletion of all your data via /support.

<b>8. RETENTION PERIODS</b>

• Active capsules: until delivery
• Delivered capsules: automatically desctroyed after delivery
• Payment history: 3 years (tax requirements)

<b>9. CONTACTS</b>

For privacy inquiries: /support
Response time: {RESPONSE_TIME_HOURS} hours
'''