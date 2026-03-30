#!/usr/bin/env python
"""
Главный файл для управления Django-проектом.
Через него запускаются все команды: runserver, migrate, createsuperuser и т.д.
Без него ничего не работает.
"""

import os
import sys


def main():
    """Запускает административные задачи Django."""
    # Указываем, какой файл настроек использовать
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Habit_Tracker.settings')
    try:
        # Пытаемся импортировать функцию для выполнения команд
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # Если Django не установлен - показываем понятную ошибку
        raise ImportError(
            "Не удалось импортировать Django. Убедитесь, что он установлен "
            "и доступен в виртуальном окружении."
        ) from exc
    # Выполняем команду из командной строки
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()