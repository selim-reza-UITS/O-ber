from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'src.apps.accounts'

    def ready(self):
        import src.apps.accounts.signals
