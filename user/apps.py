from django.apps import AppConfig
from django.db.models.signals import post_migrate

class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user'

    def ready(self):
        from .signals import create_roles_on_migrate
        post_migrate.connect(create_roles_on_migrate, sender=self)
