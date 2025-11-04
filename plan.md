plan.md

План интеграции “Идеи” (реализация)

Общий прогресс: ✅ 100%

Задачи:

- ✅ Шаг 1: Верифицировать текущее состояние кода
  - ✅ Просмотреть структуру src/, handlers/, ideas_templates.py, translations.py, config.py
  - ✅ Подтвердить наличие состояний SELECTING_IDEAS_CATEGORY, SELECTING_IDEA_TEMPLATE, EDITING_IDEA_CONTENT
  - ✅ Сверить наличие всех ключей переводов для идей (24 шаблона × title/text/hints)
  - ✅ Проверить регистрация routers/handlers для ideas в application/dispatcher

- ✅ Шаг 2: Привести переводы к полному набору
  - ✅ Добавить базовые ключи интерфейса идей: ideas_button, ideas_menu_title, ideas_select_template_from, ideas_preset_time, ideas_hints, ideas_edit_text, ideas_enter_text, ideas_use_template, back_to_menu
  - ✅ Добавить ключи категорий: ideas_category_self_motivation, ideas_category_holidays, ideas_category_daily_reflection, ideas_category_relationships, ideas_category_goals_plans, ideas_category_memories
  - ✅ Добавить ключи шаблонов (RU/EN) из ideas_templates.py для всех 24 шаблонов
  - ✅ Выровнять форматы дат/разметки в текстах

- ✅ Шаг 3: Подключить кнопку “Идеи” в главное меню
  - ✅ В handlers/main_menu.py добавить кнопку с label = t(lang, 'ideas_button'), callback_data='ideas_menu'
  - ✅ Убедиться, что send_menu_with_image корректно отображает кнопку и текст
  - ✅ Обновить обработчик нажатия: при 'ideas_menu' вызывать show_ideas_menu

- ✅ Шаг 4: Протянуть роутинг для идей
  - ✅ Зарегистрировать handlers:
    - ✅ CallbackQueryHandler(ideas_router, pattern='^(ideas_menu|ideas_cat:|ideas_tpl:|ideas_use|ideas_edit|ideas_back)$')
    - ✅ MessageHandler для EDITING_IDEA_CONTENT → ideas_text_input
  - ✅ Обеспечить возврат в main_menu по 'back' и 'back_to_menu'

- ✅ Шаг 5: Согласовать префиллы с create flow
  - ✅ Проверить, что start_create_capsule читает префиллы из context.user_data
  - ✅ Добавить мягкую обработку отсутствующих префиллов

- ✅ Шаг 6: UX/локализация и консистентность
  - ✅ Все кнопки/сообщения в ideas.py переводятся через t(lang, ...)
  - ✅ Заголовки/подсказки соответствуют лимитам Telegram
  - ✅ Предпросмотр использует parse_mode='HTML' безопасно

- ✅ Шаг 7: Крайние случаи и ограничения
  - ✅ Пустой ввод в режиме редактирования оставляет предыдущий текст
  - ✅ Неизвестные callback_data возвращают в меню идей
  - ✅ Даты-пресеты внутри лимитов тарифа (корректируются пользователем в create flow при необходимости)

- ✅ Шаг 8: Проверки перед коммитом
  - ✅ Ручные сценарии: категории → шаблон → предпросмотр → "Использовать" → create flow с префиллами
  - ✅ Редактирование текста и возврат к предпросмотру
  - ✅ Возврат назад к категориям и в главное меню
  - ✅ Логи: отсутствуют KeyError по переводам и callback’ам
