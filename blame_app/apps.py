from django.apps import AppConfig


class BlameAppConfig(AppConfig):
    name = "blame_app"


# Backward-compatible alias
ZitAppConfig = BlameAppConfig
