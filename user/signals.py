from django.contrib.auth.models import Group, Permission
from django.apps import apps
from django.conf import settings

APP_MODELS = getattr(
    settings,
    "APP_MODELS",
    {"cms": ["Category", "Product", "ProductVariant"]}
)
ROLES = {
    "CATALOG_VIEWER": ["view"],
    "CATALOG_EDITOR": ["view", "add", "change"],
    "CATALOG_ADMIN":  ["view", "add", "change", "delete"],
}

def create_roles_on_migrate(sender, **kwargs):
    """
    Signal handler to create user roles and assign permissions after migrations.

    This function is intended to be connected to Django's post_migrate signal.
    It creates groups for each role defined in ROLES and assigns the appropriate
    permissions for models listed in APP_MODELS.
    """
    for role_name, actions in ROLES.items():
        group, _ = Group.objects.get_or_create(name=role_name)
        for app_label, model_names in APP_MODELS.items():
            for model_name in model_names:
                try:
                    model = apps.get_model(app_label, model_name)
                except LookupError:
                    continue
                for action in actions:
                    codename = f"{action}_{model._meta.model_name}"
                    try:
                        perm = Permission.objects.get(
                            content_type__app_label=app_label,
                            codename=codename,
                        )
                        group.permissions.add(perm)
                    except Permission.DoesNotExist:
                        continue
