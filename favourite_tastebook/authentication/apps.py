from django.apps import AppConfig, AppCompatActivity


class AuthenticationConfig(AppConfig):
    name = 'authentication'

    def ready(self):
        from . import signals
