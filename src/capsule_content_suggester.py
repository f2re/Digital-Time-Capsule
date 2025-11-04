"""
Intelligent content suggestion system for time capsules with contextual prompts based on user behavior and time.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import logging
from enum import Enum

from .translations import t
from .database import get_user_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContentSuggestionType(Enum):
    REFLECTION = "reflection"
    GOALS = "goals"
    GRATITUDE = "gratitude"
    MOMENT_CAPTURE = "moment_capture"
    LETTERS = "letters"
    CHALLENGES = "challenges"

    @classmethod
    def get_all_types(cls):
        """Get all content suggestion types as a list."""
        return [item for item in cls]


class CapsuleType(Enum):
    """Specific capsule types with dedicated workflows."""
    REFLECTION = "reflection_capsule"
    DREAM = "dream_capsule" 
    MEMORY = "memory_capsule"
    LETTER_TO_FUTURE = "letter_to_future"
    GRATITUDE = "gratitude_capsule"
    CHALLENGE = "challenge_capsule"

    @classmethod
    def get_all_types(cls):
        """Get all capsule types as a list."""
        return [item for item in cls]


class CapsuleContentSuggester:
    """Intelligent content suggestion engine for time capsules"""
    
    # Content prompts by type and context
    CONTENT_PROMPTS = {
        'reflection_evening': {
            'ru': {
                'trigger': 'День подходит к концу 🌙\n\nЗапиши одну мысль перед сном\nЧерез месяц будешь благодарен\n\n[Вечерняя капсула]',
                'prompts': [
                    'Что было сегодня?',
                    'Не весь день — один момент\nТот, который запомнился',
                    'Можно всего пару строк ✨'
                ],
                'random_suggestions': [
                    '• Что сегодня удивило?',
                    '• За что благодарен?',
                    '• Что хочу изменить завтра?',
                    '• Кто повлиял на настроение?',
                    '• Какое открытие сделал?'
                ]
            },
            'en': {
                'trigger': 'Day is coming to an end 🌙\n\nWrite one thought before sleep\nYou\'ll be grateful in a month\n\n[Evening capsule]',
                'prompts': [
                    'What happened today?',
                    'Not the whole day — one moment\nThe one you remember',
                    'Just a couple lines is enough ✨'
                ],
                'random_suggestions': [
                    '• What surprised you today?',
                    '• What are you grateful for?',
                    '• What do you want to change tomorrow?',
                    '• Who influenced your mood?',
                    '• What discovery did you make?'
                ]
            }
        },
        
        'goals_morning': {
            'ru': {
                'trigger': 'Новая неделя, новые возможности ✨\n\nЗагадай мечту — запиши её как факт\n\n"Через [срок] я уже..."',
                'prompts': [
                    'Представь: это уже произошло',
                    'Опиши в деталях:\n• Где ты?\n• Что чувствуешь?\n• Что изменилось в жизни?',
                    'Пиши в настоящем времени — как будто это сейчас 🌅'
                ],
                'enhancement_tips': [
                    'Добавь детали — они работают как карта:',
                    '✓ Конкретные цифры',
                    '✓ Имена людей',
                    '✓ Места',
                    '✓ Ощущения в теле',
                    '✓ Что видишь вокруг',
                    'Чем точнее — тем мощнее'
                ]
            },
            'en': {
                'trigger': 'New week, new opportunities ✨\n\nWish for a dream — write it as a fact\n\n"In [timeframe] I already..."',
                'prompts': [
                    'Imagine: it already happened',
                    'Describe in detail:\n• Where are you?\n• What do you feel?\n• What changed in life?',
                    'Write in present tense — as if it\'s now 🌅'
                ],
                'enhancement_tips': [
                    'Add details — they work like a map:',
                    '✓ Specific numbers',
                    '✓ Names of people',
                    '✓ Place names',
                    '✓ Body sensations',
                    '✓ What you see around',
                    'The more precise — the stronger'
                ]
            }
        },
        
        'gratitude_sunday': {
            'ru': {
                'trigger': 'Доброе утро! ☀️\n\nНеделя прошла — за что ты благодарен?\n\nОдин человек, момент или событие\nЗапиши — это станет якорем 🙏',
                'prompts': [
                    'Благодарность — это суперсила',
                    'За что спасибо:\n• Человеку\n• Себе\n• Жизни\n• Моменту',
                    'Опиши, почему это важно 💛'
                ]
            },
            'en': {
                'trigger': 'Good morning! ☀️\n\nWeek is over — what are you grateful for?\n\nOne person, moment or event\nWrite it — it will become an anchor 🙏',
                'prompts': [
                    'Gratitude is a superpower',
                    'Thanks for:\n• A person\n• Yourself\n• Life\n• A moment',
                    'Describe why this is important 💛'
                ]
            }
        },
        
        'moment_capture': {
            'ru': {
                'trigger': 'Остановись на секунду ⏸\n\nПрямо сейчас — что происходит?\nГде ты, что чувствуешь, что вокруг?\n\nЧерез год этот момент исчезнет\nСохрани его ✨',
                'prompts': [
                    'Опиши этот момент — деталями:',
                    '👁 Что видишь?',
                    '👂 Что слышишь?',
                    '💭 О чём думаешь?',
                    '❤️ Что чувствуешь?',
                    'Даже обычное — станет ценным'
                ],
                'format_tip': 'Пиши поток сознания\n\nНе редактируй, не думай — просто пиши\nУ тебя 60 секунд ⏱\n\n[Начать записывать]'
            },
            'en': {
                'trigger': 'Stop for a second ⏸\n\nRight now — what\'s happening?\nWhere are you, what do you feel, what\'s around?\n\nIn a year this moment will disappear\nSave it ✨',
                'prompts': [
                    'Describe this moment — in detail:',
                    '👁 What do you see?',
                    '👂 What do you hear?',
                    '💭 What are you thinking?',
                    '❤️ What do you feel?',
                    'Even ordinary — will become valuable'
                ],
                'format_tip': 'Write stream of consciousness\n\nDon\'t edit, don\'t think — just write\nYou have 60 seconds ⏱\n\n[Start recording]'
            }
        }
    }
    
    # Time-based trigger conditions
    TIMING_CONDITIONS = {
        'morning_motivation': {
            'hours': [7, 8, 9, 10],
            'days': [0, 1, 2, 3, 4],  # Monday-Friday
            'content_type': 'goals_morning'
        },
        'evening_reflection': {
            'hours': [21, 22, 23],
            'content_type': 'reflection_evening'
        },
        'sunday_gratitude': {
            'hours': [9, 10, 11],
            'days': [6],  # Sunday
            'content_type': 'gratitude_sunday'
        },
        'afternoon_moment': {
            'hours': [14, 15, 16],
            'content_type': 'moment_capture'
        }
    }
    
    # Emotional patterns for content recommendation
    EMOTIONAL_PATTERNS = {
        'reflective': {
            'keywords': ['чувствую', 'думаю', 'осознал', 'понял', 'чувствую', 'осознанно', 'осознание'],
            'recommendations': [ContentSuggestionType.REFLECTION, ContentSuggestionType.MOMENT_CAPTURE],
            'en_keywords': ['feel', 'think', 'realized', 'understand', 'aware', 'awareness', 'conscious']
        },
        'goal_oriented': {
            'keywords': ['хочу', 'планирую', 'достигну', 'цель', 'поставлю', 'добьюсь', 'пойду'],
            'recommendations': [ContentSuggestionType.GOALS, ContentSuggestionType.CHALLENGES],
            'en_keywords': ['want', 'plan', 'achieve', 'goal', 'set', 'succeed', 'go']
        },
        'nostalgic': {
            'keywords': ['помню', 'был', 'тогда', 'раньше', 'вспоминаю', 'прошлое', 'воспоминание'],
            'recommendations': [ContentSuggestionType.REFLECTION, ContentSuggestionType.MOMENT_CAPTURE],
            'en_keywords': ['remember', 'was', 'then', 'before', 'recall', 'past', 'memory']
        },
        'grateful': {
            'keywords': ['спасибо', 'благодарен', 'ценю', 'рад', 'счастлив', 'благодарность'],
            'recommendations': [ContentSuggestionType.GRATITUDE, ContentSuggestionType.LETTERS],
            'en_keywords': ['thank', 'grateful', 'appreciate', 'happy', 'blessed', 'gratitude']
        }
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def get_contextual_prompt(content_type: str, lang: str, user_data: dict = None) -> dict:
        """Get contextual prompt based on type and user data"""
        prompt_data = CapsuleContentSuggester.CONTENT_PROMPTS.get(content_type, {}).get(lang, {})
        
        if user_data:
            # Personalize with user data
            if 'trigger' in prompt_data:
                trigger = prompt_data['trigger']
                # Replace placeholders with user data
                if 'preferred_timeframe' in user_data:
                    trigger = trigger.replace('[срок]', user_data['preferred_timeframe'])
                    trigger = trigger.replace('[timeframe]', user_data['preferred_timeframe'])
                prompt_data['trigger'] = trigger
        
        return prompt_data
    
    @staticmethod
    def should_trigger_suggestion(user_data: dict, current_time: datetime) -> Optional[str]:
        """Determine if we should suggest content creation based on timing"""
        current_hour = current_time.hour
        current_weekday = current_time.weekday()  # 0=Monday, 6=Sunday
        
        # Check each timing condition
        for trigger_name, conditions in CapsuleContentSuggester.TIMING_CONDITIONS.items():
            if current_hour in conditions['hours']:
                if 'days' in conditions:
                    if current_weekday in conditions['days']:
                        return conditions['content_type']
                else:
                    return conditions['content_type']
        
        return None
    
    @staticmethod
    def analyze_user_emotional_profile(content: str, lang: str) -> str:
        """Analyze emotional profile from content text"""
        content_lower = content.lower()
        
        # Determine language for keyword matching
        if lang == 'ru':
            # Russian language analysis
            for profile, data in CapsuleContentSuggester.EMOTIONAL_PATTERNS.items():
                keywords = data['keywords']
                for keyword in keywords:
                    if keyword in content_lower:
                        return profile
        else:
            # English language analysis
            for profile, data in CapsuleContentSuggester.EMOTIONAL_PATTERNS.items():
                keywords = data['en_keywords']
                for keyword in keywords:
                    if keyword in content_lower:
                        return profile
        
        # Default to unknown if no strong indicators found
        return 'unknown'
    
    def suggest_content_type_for_user(self, user_id: int, current_time: datetime) -> Optional[ContentSuggestionType]:
        """Suggest the best content type for a specific user based on their behavior and current time"""
        user_data = get_user_data(user_id)
        if not user_data:
            return None
        
        # Get timing-based suggestion
        time_based_suggestion = self.should_trigger_suggestion(user_data, current_time)
        
        # Get emotional profile-based suggestion
        emotional_profile = user_data.get('emotional_profile', 'unknown')
        if emotional_profile != 'unknown':
            emotional_suggestions = self.EMOTIONAL_PATTERNS.get(emotional_profile, {}).get('recommendations', [])
            if emotional_suggestions:
                return emotional_suggestions[0]
        
        # If no emotional profile, use time-based
        if time_based_suggestion:
            # Map content type to suggestion type
            type_mapping = {
                'reflection_evening': ContentSuggestionType.REFLECTION,
                'goals_morning': ContentSuggestionType.GOALS,
                'gratitude_sunday': ContentSuggestionType.GRATITUDE,
                'moment_capture': ContentSuggestionType.MOMENT_CAPTURE
            }
            return type_mapping.get(time_based_suggestion)
        
        # Default suggestion based on user preferences
        preferred_types = user_data.get('preferred_capsule_types', [])
        if preferred_types:
            type_mapping = {
                'reflection': ContentSuggestionType.REFLECTION,
                'goals': ContentSuggestionType.GOALS,
                'gratitude': ContentSuggestionType.GRATITUDE,
                'moment': ContentSuggestionType.MOMENT_CAPTURE,
                'letters': ContentSuggestionType.LETTERS,
                'challenges': ContentSuggestionType.CHALLENGES
            }
            for pref_type in preferred_types:
                if pref_type in type_mapping:
                    return type_mapping[pref_type]
        
        # Default fallback
        return ContentSuggestionType.REFLECTION
    
    def get_smart_suggestions(self, user_id: int, current_time: datetime) -> Dict:
        """Get comprehensive smart suggestions for a user"""
        user_data = get_user_data(user_id)
        if not user_data:
            return {}
        
        lang = user_data.get('language_code', 'ru')
        
        # Get the suggested content type
        suggested_type = self.suggest_content_type_for_user(user_id, current_time)
        
        if not suggested_type:
            return {}
        
        # Convert suggestion type to content type key
        type_to_content_map = {
            ContentSuggestionType.REFLECTION: 'reflection_evening',
            ContentSuggestionType.GOALS: 'goals_morning',
            ContentSuggestionType.GRATITUDE: 'gratitude_sunday',
            ContentSuggestionType.MOMENT_CAPTURE: 'moment_capture'
        }
        
        content_type_key = type_to_content_map.get(suggested_type)
        if not content_type_key:
            return {}
        
        # Get context-aware prompt
        prompt_data = self.get_contextual_prompt(content_type_key, lang, user_data)
        
        # Calculate personalization metrics
        streak_count = user_data.get('streak_count', 0)
        total_created = user_data.get('total_capsules_created', 0)
        
        # Add streak-based encouragement
        if streak_count > 0:
            streak_encouragement = {
                'ru': f'Ты на {streak_count}-дневной серии! 🔥 Продолжай 🌟',
                'en': f'You\'re on a {streak_count}-day streak! 🔥 Keep going 🌟'
            }
            prompt_data['streak_encouragement'] = streak_encouragement[lang]
        
        # Add activity-based encouragement
        if total_created > 0:
            activity_encouragement = {
                'ru': f'Всего создано: {total_created} капсул 📦 Продолжай копить воспоминания!',
                'en': f'Total created: {total_created} capsules 📦 Keep collecting memories!'
            }
            prompt_data['activity_encouragement'] = activity_encouragement[lang]
        
        return {
            'suggested_type': suggested_type.value,
            'prompt_data': prompt_data,
            'should_trigger': True,
            'personalization_level': 'high' if user_data.get('emotional_profile') != 'unknown' else 'medium'
        }

    def get_writing_templates(self, content_type: ContentSuggestionType, lang: str = 'ru') -> Dict:
        """Get writing templates and assistance for different content types."""
        templates = {
            ContentSuggestionType.REFLECTION: {
                'ru': {
                    'title': 'Шаблон рефлексии',
                    'introduction': 'Подумай о прошедшем дне или важном событии:',
                    'prompts': [
                        'Что сегодня произвело на тебя наибольшее впечатление?',
                        'Что ты почувствовал в этот момент?',
                        'Как это событие повлияло на тебя?',
                        'Что бы ты хотел запомнить навсегда?',
                        'Какие уроки ты извлек?'
                    ],
                    'writing_tips': [
                        'Пиши от первого лица',
                        'Описывай чувства, а не только события',
                        'Будь честным с собой',
                        'Не бойся делиться уязвимыми моментами',
                        'Пиши так, как будто обращаешься к близкому другу'
                    ]
                },
                'en': {
                    'title': 'Reflection Template',
                    'introduction': 'Think about the day gone by or an important event:',
                    'prompts': [
                        'What impressed you most today?',
                        'How did you feel in this moment?',
                        'How did this event affect you?',
                        'What would you like to remember forever?',
                        'What lessons did you learn?'
                    ],
                    'writing_tips': [
                        'Write in first person',
                        'Describe feelings, not just events',
                        'Be honest with yourself',
                        'Don\'t be afraid to share vulnerable moments',
                        'Write as if addressing a close friend'
                    ]
                }
            },
            ContentSuggestionType.GOALS: {
                'ru': {
                    'title': 'Шаблон целей',
                    'introduction': 'Задай себе вопросы о будущем:',
                    'prompts': [
                        'Чего ты хочешь достичь за следующие 3 месяца?',
                        'Как ты будешь чувствовать себя, достигнув цели?',
                        'Какие шаги ты можешь предпринять уже сегодня?',
                        'Что тебе нужно изменить, чтобы приблизиться к цели?',
                        'Как ты будешь отмечать достижение цели?'
                    ],
                    'writing_tips': [
                        'Формулируй цели конкретно',
                        'Описывай результат в деталях',
                        'Назначь сроки',
                        'Пиши в настоящем времени, как будто цель уже достигнута',
                        'Добавляй эмоциональные связи с целями'
                    ]
                },
                'en': {
                    'title': 'Goals Template',
                    'introduction': 'Ask yourself questions about the future:',
                    'prompts': [
                        'What do you want to achieve in the next 3 months?',
                        'How will you feel when you reach your goal?',
                        'What steps can you take today?',
                        'What do you need to change to get closer to your goal?',
                        'How will you celebrate achieving your goal?'
                    ],
                    'writing_tips': [
                        'Formulate goals specifically',
                        'Describe the result in detail',
                        'Assign deadlines',
                        'Write in present tense as if the goal is already achieved',
                        'Add emotional connections to goals'
                    ]
                }
            },
            ContentSuggestionType.GRATITUDE: {
                'ru': {
                    'title': 'Шаблон благодарности',
                    'introduction': 'Сосредоточься на вещах, за которые ты благодарен:',
                    'prompts': [
                        'За что ты благодарен сегодня?',
                        'Кто оказал на тебя положительное влияние?',
                        'Какое событие сделало твой день лучше?',
                        'Что ты часто принимаешь как должное?',
                        'Как благодарность влияет на твое настроение?'
                    ],
                    'writing_tips': [
                        'Будь конкретным, а не общим',
                        'Описывай почему ты благодарен',
                        'Сосредоточься на людях, отношениях, здоровье',
                        'Включай даже маленькие радости',
                        'Используй чувственные описания'
                    ]
                },
                'en': {
                    'title': 'Gratitude Template',
                    'introduction': 'Focus on things you are grateful for:',
                    'prompts': [
                        'What are you grateful for today?',
                        'Who had a positive influence on you?',
                        'What event made your day better?',
                        'What do you often take for granted?',
                        'How does gratitude affect your mood?'
                    ],
                    'writing_tips': [
                        'Be specific rather than general',
                        'Describe why you are grateful',
                        'Focus on people, relationships, health',
                        'Include even small joys',
                        'Use sensory descriptions'
                    ]
                }
            },
            ContentSuggestionType.MOMENT_CAPTURE: {
                'ru': {
                    'title': 'Шаблон запечатления момента',
                    'introduction': 'Запечатли этот момент как есть:',
                    'prompts': [
                        'Где ты находишься прямо сейчас?',
                        'Какую музыку ты слышишь или хотел бы слышать?',
                        'Что ты чувствуешь в теле?',
                        'Какое впечатление ты производишь на окружающих?',
                        'Что ты хотел бы сказать себе в этот момент?'
                    ],
                    'writing_tips': [
                        'Описывай чувства и ощущения',
                        'Используй как можно больше чувств',
                        'Пиши в потоке сознания',
                        'Не редактируй, просто записывай',
                        'Сохраняй атмосферу момента'
                    ]
                },
                'en': {
                    'title': 'Moment Capture Template',
                    'introduction': 'Capture this moment as it is:',
                    'prompts': [
                        'Where are you right now?',
                        'What music are you hearing or would like to hear?',
                        'What are you feeling in your body?',
                        'What impression are you making on others?',
                        'What would you like to tell yourself at this moment?'
                    ],
                    'writing_tips': [
                        'Describe feelings and sensations',
                        'Use as many senses as possible',
                        'Write in stream of consciousness',
                        'Don\'t edit, just record',
                        'Preserve the atmosphere of the moment'
                    ]
                }
            },
            ContentSuggestionType.LETTERS: {
                'ru': {
                    'title': 'Шаблон писем',
                    'introduction': 'Напиши письмо кому-то важному:',
                    'prompts': [
                        'Кому ты хочешь написать и почему?',
                        'Что ты хотел бы сказать, но не сказал?',
                        'Какие воспоминания вы связаны?',
                        'Что ты хочешь, чтобы они знали?',
                        'Как твое письмо может повлиять на них?'
                    ],
                    'writing_tips': [
                        'Обращайся к человеку по имени',
                        'Будь искренним и открытым',
                        'Делись личными мыслями',
                        'Выражай чувства, а не только факты',
                        'Представляй, как человек будет читать это'
                    ]
                },
                'en': {
                    'title': 'Letters Template',
                    'introduction': 'Write a letter to someone important:',
                    'prompts': [
                        'Who do you want to write to and why?',
                        'What did you want to say but never said?',
                        'What memories do you share?',
                        'What do you want them to know?',
                        'How might your letter affect them?'
                    ],
                    'writing_tips': [
                        'Address the person by name',
                        'Be sincere and open',
                        'Share personal thoughts',
                        'Express feelings, not just facts',
                        'Imagine how the person will read this'
                    ]
                }
            },
            ContentSuggestionType.CHALLENGES: {
                'ru': {
                    'title': 'Шаблон испытаний',
                    'introduction': 'Поделись текущими испытаниями или вызовами:',
                    'prompts': [
                        'С какими трудностями ты сталкиваешься?',
                        'Как ты справляешься с ними?',
                        'Что ты узнал о себе в процессе?',
                        'Какие ресурсы ты используешь?',
                        'Что ты хотел бы изменить в подходе?'
                    ],
                    'writing_tips': [
                        'Признавай сложности без осуждения',
                        'Фокусируйся на процессе, а не только на результате',
                        'Отмечай небольшие победы',
                        'Делай акцент на личностном росте',
                        'Пиши с доброжелательностью к себе'
                    ]
                },
                'en': {
                    'title': 'Challenges Template',
                    'introduction': 'Share current challenges or challenges:',
                    'prompts': [
                        'What difficulties are you facing?',
                        'How are you coping with them?',
                        'What have you learned about yourself?',
                        'What resources are you using?',
                        'What would you like to change in your approach?'
                    ],
                    'writing_tips': [
                        'Acknowledge difficulties without judgment',
                        'Focus on process, not just outcomes',
                        'Note small victories',
                        'Emphasize personal growth',
                        'Write with self-compassion'
                    ]
                }
            }
        }
        
        return templates.get(content_type, {}).get(lang, templates[ContentSuggestionType.REFLECTION]['ru'])

    def get_contextual_suggestions(self, user_id: int, current_time: datetime) -> Dict:
        """Get comprehensive contextual suggestions based on user data and time."""
        user_data = get_user_data(user_id)
        if not user_data:
            return {}
        
        lang = user_data.get('language_code', 'ru')
        
        # Determine if we should show suggestions based on context
        suggestions = []
        
        # Time-based suggestions
        time_suggestions = self.should_trigger_suggestion(user_data, current_time)
        if time_suggestions:
            suggestions.append({
                'type': 'time_based',
                'content_type': time_suggestions,
                'prompt_data': self.get_contextual_prompt(time_suggestions, lang, user_data)
            })
        
        # Emotion-based suggestions
        emotional_profile = user_data.get('emotional_profile', 'unknown')
        if emotional_profile != 'unknown':
            emotional_suggestions = self.EMOTIONAL_PATTERNS.get(emotional_profile, {}).get('recommendations', [])
            for content_type in emotional_suggestions[:2]:  # Limit to 2 emotional suggestions
                suggestions.append({
                    'type': 'emotion_based',
                    'content_type': content_type.value,
                    'prompt_data': self.get_contextual_prompt(
                        self.map_content_type_to_prompt(content_type.value), 
                        lang, 
                        user_data
                    )
                })
        
        # Activity-based suggestions
        last_activity = user_data.get('last_activity_time')
        if last_activity:
            from datetime import timedelta
            time_since_activity = current_time - (last_activity if isinstance(last_activity, datetime) 
                                                 else datetime.fromisoformat(str(last_activity)))
            
            if time_since_activity > timedelta(days=2):
                # User hasn't been active recently, suggest re-engagement
                suggestions.append({
                    'type': 're_engagement',
                    'content_type': 'reflection_evening',  # generic re-engagement content
                    'prompt_data': self.get_contextual_prompt('moment_capture', lang, user_data)
                })
        
        return {
            'suggestions': suggestions,
            'user_profile': {
                'emotional_profile': emotional_profile,
                'streak_count': user_data.get('streak_count', 0),
                'capsules_created': user_data.get('total_capsules_created', 0)
            },
            'should_show_suggestions': len(suggestions) > 0
        }

    def map_content_type_to_prompt(self, content_type: str) -> str:
        """Map content suggestion types to appropriate prompt keys."""
        mapping = {
            'reflection': 'reflection_evening',
            'goals': 'goals_morning', 
            'gratitude': 'gratitude_sunday',
            'moment_capture': 'moment_capture',
            'letters': 'moment_capture',  # Using moment capture as default for letters
            'challenges': 'moment_capture'  # Using moment capture as default for challenges
        }
        return mapping.get(content_type, 'moment_capture')


class NotificationManager:
    """Manages intelligent, contextual notifications"""
    
    # Critical onboarding moments (research-based)
    ONBOARDING_SEQUENCE = {
        'day_1_evening': {
            'trigger_hours': [19, 20, 21],
            'condition': 'no_second_capsule_created',
            'messages': {
                'ru': 'Привет снова 🌙\n\nУ тебя уже есть одна капсула в пути\nМногие создают вторую — для другого настроения\n\n[Создать вечернюю капсулу]',
                'en': 'Hello again 🌙\n\nYou already have one capsule on its way\nMany create a second one — for a different mood\n\n[Create evening capsule]'
            }
        },
        
        'day_2_morning': {
            'trigger_hours': [9, 10],
            'condition': 'no_activity_yesterday',
            'messages': {
                'ru': 'Доброе утро!\n\nВчера ты создал капсулу\nСегодня ты уже немного другой\n\nЗаписать эту разницу? ☕️\n[Новая мысль]',
                'en': 'Good morning!\n\nYesterday you created a capsule\nToday you\'re already a bit different\n\nRecord this difference? ☕️\n[New thought]'
            }
        },
        
        'day_3_critical': {
            'trigger_hours': [11, 16, 20],
            'condition': 'no_activity_2_days',
            'messages': {
                'ru': 'Твоя первая капсула откроется [дата]\n\nПока она в пути, можешь создать ещё:\n• Голосовое сообщение себе 🎤\n• Фото этого момента 📸\n• Просто пару строк 📝\n\nКаждая капсула — это точка на карте твоей жизни',
                'en': 'Your first capsule will open on [date]\n\nWhile it\'s on its way, you can create more:\n• Voice message to yourself 🎤\n• Photo of this moment 📸\n• Just a few lines 📝\n\nEach capsule is a point on your life map'
            }
        }
    }
    
    # Behavioral triggers
    BEHAVIORAL_TRIGGERS = {
        'after_emotional_capsule': {
            'condition': 'capsule_opened_with_positive_reaction',
            'delay_minutes': 10,
            'messages': {
                'ru': 'Рад, что попало в точку 💫\n\nЗнаешь, что круто?\nЧем больше капсул — тем ценнее\n\nСоздать следующую?\n[Да ✨]',
                'en': 'Glad it hit the mark 💫\n\nKnow what\'s cool?\nThe more capsules — the more valuable\n\nCreate the next one?\n[Yes ✨]'
            }
        },
        
        'streak_building': {
            'condition': 'consecutive_days_2',
            'messages': {
                'ru': '2 дня подряд 🔥\n\nНачинается серия!\nПродолжай завтра — это формирует привычку\n\n[Создать капсулу на сегодня]',
                'en': '2 days in a row 🔥\n\nA streak is starting!\nContinue tomorrow — this builds a habit\n\n[Create capsule for today]'
            }
        },
        
        'milestone_celebration': {
            'condition': 'capsules_count_10',
            'messages': {
                'ru': '10 капсул — это целая коллекция! 💎\n\nТы в топ-20% пользователей\nСпасибо, что доверяешь нам своё время\n\nНебольшой подарок:\n[+3 премиум капсулы бесплатно]',
                'en': '10 capsules — that\'s a whole collection! 💎\n\nYou\'re in the top 20% of users\nThanks for trusting us with your time\n\nSmall gift:\n[+3 premium capsules for free]'
            }
        }
    }
    
    # Capsule opening experience
    OPENING_SEQUENCE = {
        'pre_opening_24h': {
            'messages': {
                'ru': 'Завтра откроется твоя капсула\n\nПомнишь, что писал [дата создания]?\nВремя узнать 👀',
                'en': 'Your capsule opens tomorrow\n\nRemember what you wrote on [creation_date]?\nTime to find out 👀'
            }
        },
        
        'opening_moment': {
            'messages': {
                'ru': 'Привет из прошлого 👋\n\nТы писал это [количество] дней назад\nЧитай медленно\n\n---\n[ТЕКСТ КАПСУЛЫ]\n---\n\nЧто изменилось с тех пор?',
                'en': 'Hello from the past 👋\n\nYou wrote this [number] days ago\nRead slowly\n\n---\n[CAPSULE TEXT]\n---\n\nWhat has changed since then?'
            }
        },
        
        'post_opening_reaction': {
            'messages': {
                'ru': 'Как эти слова?\n\n[Душевно 💛] [Странно 😅] [Мотивирует 🔥] [Грустно 😔]\n\n[Создать ответ себе в прошлое]',
                'en': 'How do these words feel?\n\n[Heartfelt 💛] [Strange 😅] [Motivating 🔥] [Sad 😔]\n\n[Create response to past self]'
            }
        }
    }
    
    @staticmethod
    def should_send_notification(user_data: dict, notification_type: str, current_time) -> bool:
        """Determine if notification should be sent based on user behavior"""
        
        # Anti-spam protection
        last_notification = user_data.get('last_notification_time')
        if last_notification:
            try:
                # Convert to datetime if it's a string
                if isinstance(last_notification, str):
                    last_notification = datetime.fromisoformat(last_notification.replace('Z', '+00:00'))
                hours_since_last = (current_time - last_notification).total_seconds() / 3600
                if hours_since_last < 6:  # Minimum 6 hours between notifications
                    return False
            except Exception:
                pass  # If date parsing fails, continue with notification evaluation
        
        # Check specific conditions
        if notification_type == 'onboarding_day_1_evening':
            return (user_data.get('total_capsules_created', 0) == 1 and 
                   not user_data.get('created_capsule_today', False))
        
        elif notification_type == 'streak_building':
            return user_data.get('streak_count', 0) == 2
        
        elif notification_type == 'milestone_10':
            return user_data.get('total_capsules_created', 0) == 10
        
        return False

    @staticmethod
    def get_personalized_message(message_template: str, user_data: dict) -> str:
        """Personalize message with user data"""
        
        replacements = {
            '[имя]': user_data.get('first_name', 'друг'),
            '[количество_капсул]': str(user_data.get('total_capsules_created', 0)),
            '[streak]': str(user_data.get('streak_count', 0)),
            '[дата]': user_data.get('last_capsule_date', 'недавно')
        }
        
        personalized = message_template
        for placeholder, value in replacements.items():
            personalized = personalized.replace(placeholder, value)
        
        return personalized


class SmartScheduler:
    """Enhanced scheduler with behavioral triggers and personalized timing"""
    
    # Timing patterns for different user types
    USER_TIMING_PROFILES = {
        'morning_person': {
            'optimal_hours': [7, 8, 9],
            'avoid_hours': [22, 23, 0, 1, 2, 3, 4, 5, 6],
            'peak_engagement': [8, 9]
        },
        'evening_person': {
            'optimal_hours': [19, 20, 21, 22],
            'avoid_hours': [6, 7, 8, 9],
            'peak_engagement': [20, 21]
        },
        'unknown': {
            'optimal_hours': [10, 14, 18, 20],
            'avoid_hours': [1, 2, 3, 4, 5, 6],
            'peak_engagement': [14, 20]
        }
    }
    
    @staticmethod
    def schedule_smart_notification(user_id: int, notification_type: str, user_data: dict):
        """Schedule notification at optimal time for user"""
        
        # Determine user's timing profile
        timing_profile = SmartScheduler.determine_user_profile(user_data)
        optimal_hours = SmartScheduler.USER_TIMING_PROFILES[timing_profile]['optimal_hours']
        
        # Calculate next optimal time
        current_time = datetime.now()
        target_time = None
        
        for hour in optimal_hours:
            candidate_time = current_time.replace(hour=hour, minute=0, second=0, microsecond=0)
            if candidate_time > current_time:
                target_time = candidate_time
                break
        
        # If no time today, schedule for tomorrow
        if not target_time:
            target_time = current_time.replace(hour=optimal_hours[0], minute=0, second=0, microsecond=0)
            target_time += timedelta(days=1)
        
        # Import scheduler here to avoid circular imports
        from .scheduler import scheduler
        
        # Schedule the job
        scheduler.add_job(
            func=send_smart_notification,
            trigger='date',
            run_date=target_time,
            args=[user_id, notification_type],
            id=f"smart_notify_{user_id}_{notification_type}_{int(target_time.timestamp())}"
        )
    
    @staticmethod
    def determine_user_profile(user_data: dict) -> str:
        """Analyze user behavior to determine timing profile"""
        
        creation_hours = user_data.get('capsule_creation_hours', [])
        if not creation_hours:
            return 'unknown'
        
        # Count occurrences for each hour
        hour_counts = {}
        for hour in creation_hours:
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        # Calculate morning vs evening preference
        morning_count = sum(hour_counts.get(h, 0) for h in range(6, 12))
        evening_count = sum(hour_counts.get(h, 0) for h in range(18, 24))
        
        if morning_count > evening_count * 1.5:
            return 'morning_person'
        elif evening_count > morning_count * 1.5:
            return 'evening_person'
        else:
            return 'unknown'


def send_smart_notification(user_id: int, notification_type: str):
    """Send intelligent notification to user"""
    # This function would be called by the scheduler
    # Implementation would require bot instance
    pass


# Behavioral trigger detection
def check_behavioral_triggers(application):
    """Check for behavioral triggers across all users"""
    from .database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        # Find users who just opened emotional capsules
        try:
            recent_positive_reactions = conn.execute(text("""
                SELECT DISTINCT user_id FROM capsule_reactions 
                WHERE reaction IN ('heartfelt', 'motivating') 
                AND created_at > datetime('now', '-1 hour')
            """)).fetchall()
            
            for (user_id,) in recent_positive_reactions:
                from .database import get_user_data
                user_data = get_user_data(user_id)
                if user_data:
                    SmartScheduler.schedule_smart_notification(
                        user_id, 
                        'after_emotional_capsule',
                        user_data
                    )
        except Exception as e:
            logger.error(f"Error checking positive reactions: {e}")
        
        # Find users building streaks
        try:
            streak_users = conn.execute(text("""
                SELECT id FROM users 
                WHERE streak_count = 2 
                AND last_activity_time > date('now', '-1 day')
            """)).fetchall()
            
            for (user_id,) in streak_users:
                from .database import get_user_data
                user_data = get_user_data(user_id)
                if user_data:
                    SmartScheduler.schedule_smart_notification(
                        user_id,
                        'streak_building', 
                        user_data
                    )
        except Exception as e:
            logger.error(f"Error checking streak users: {e}")