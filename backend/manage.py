#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path


def main():
    """Run administrative tasks."""
    # Добавляем корень репозитория (~/lakshmi_bot) в PYTHONPATH,
    # чтобы импорты вида `from src...` работали при запуске из backend/.
    PROJECT_ROOT = Path(__file__).resolve().parent.parent  # ~/lakshmi_bot
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

