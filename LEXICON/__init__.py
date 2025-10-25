# LEXICON/__init__.py

from typing import Any
from .RU.LEXICON_RU import LEXICON_RU
# from .EN.LEXICON_EN import LEXICON_EN

LEXICON_MAP:dict[str, Any] = {
    'ru': LEXICON_RU,
    # 'en': LEXICON_EN,
}

def get_text(key: str, lang: str) -> str:
    """
    Возвращает текст по ключу для указанного языка.
    Если язык не поддерживается или ключ отсутствует — возвращает текст на русском или [key].
    """
    # Если язык не поддерживается — используем русский
    lexicon = LEXICON_MAP.get(lang, LEXICON_MAP['ru'])

    keys = key.split('.')
    value = lexicon

    try:
        for k in keys:
            value = value[k]
        return value
    except (KeyError, TypeError):
        # Попробуем найти на русском как последний fallback
        if lang != 'ru':
            try:
                value = LEXICON_MAP['ru']
                for k in keys:
                    value = value[k]
                return value
            except (KeyError, TypeError):
                pass
        return f"[{key}]"