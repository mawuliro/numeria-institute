from django.apps import AppConfig


class CoursConfig(AppConfig):
    name = 'cours'

    def ready(self):
        # Ensure models are loaded during app setup so legacy proxy aliases are registered.
        from . import models  # noqa: F401
