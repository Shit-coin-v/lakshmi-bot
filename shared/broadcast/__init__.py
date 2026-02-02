"""Shared broadcast functionality for backend and bots."""

from .django_sender import send_with_django

__all__ = ["send_with_django"]
