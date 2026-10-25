from django.apps import AppConfig


class PackagesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "packages"

    def ready(self):
        from . import signals  # noqa: F401
