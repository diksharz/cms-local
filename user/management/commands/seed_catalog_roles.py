from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.apps import apps

# Edit these to match where your models live and which models you want to control
# Example assumes your product/category models are in the "cms" app.
APP_MODELS = {
    "cms": ["Category", "Product", "ProductVariant"],  # remove any that don't exist
}

ROLES = {
    "CATALOG_VIEWER": ["view"],
    "CATALOG_EDITOR": ["view", "add", "change"],
    "CATALOG_ADMIN":  ["view", "add", "change", "delete"],
}

class Command(BaseCommand):
    help = "Create catalog roles (Groups) and attach model permissions"

    def handle(self, *args, **kwargs):
        for role_name, actions in ROLES.items():
            group, _ = Group.objects.get_or_create(name=role_name)

            for app_label, model_names in APP_MODELS.items():
                for model_name in model_names:
                    try:
                        model = apps.get_model(app_label, model_name)
                    except LookupError:
                        self.stdout.write(self.style.WARNING(
                            f"Skipping missing model {app_label}.{model_name}"
                        ))
                        continue

                    for action in actions:
                        codename = f"{action}_{model._meta.model_name}"
                        try:
                            perm = Permission.objects.get(
                                content_type__app_label=app_label,
                                codename=codename,
                            )
                        except Permission.DoesNotExist:
                            self.stdout.write(self.style.WARNING(
                                f"Permission not found: {app_label}.{codename}"
                            ))
                            continue

                        group.permissions.add(perm)

            self.stdout.write(self.style.SUCCESS(f"Role {role_name} updated."))

        self.stdout.write(self.style.SUCCESS("All roles created/updated."))
