import os

from django.conf import settings
from django.contrib import auth
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Local development only: make sure an active admin account exists, with the "
        "username DEV_ADMIN_USERNAME (default 'admin') and the password DEV_ADMIN_PASSWORD "
        "from .env. Refuses to run unless ENVIRONMENT=local."
    )

    def handle(self, *args, **options):
        if not settings.IS_LOCAL:
            raise CommandError(f"ensure_dev_admin only runs with ENVIRONMENT=local (got {settings.ENVIRONMENT!r}).")

        username = os.getenv("DEV_ADMIN_USERNAME", "admin")
        password = os.getenv("DEV_ADMIN_PASSWORD")
        if not password:
            self.stdout.write("DEV_ADMIN_PASSWORD is not set; no development admin created.")
            return

        user, created = auth.get_user_model().objects.get_or_create(
            username=username, defaults={"email": f"{username}@localhost"}
        )
        # Keep the account usable even if someone changed it locally.
        user.role = "admin"
        user.is_active = True
        user.set_password(password)
        user.save()
        self.stdout.write(f"Development admin '{username}' {'created' if created else 'updated'}.")
