from getpass import getpass

from django.contrib import auth
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create an active user. Prompts for the name, password (hidden) and email."

    def add_arguments(self, parser):
        parser.add_argument("--role", choices=["user", "researcher", "admin"], default="user")

    def handle(self, *args, **options):
        username = input("username: ")
        if auth.get_user_model().objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f"User with name {username} already exists."))
            return

        password = getpass("password: ")
        email = input("email: ")
        try:
            validate_password(password)
        except ValidationError as e:
            self.stdout.write(self.style.ERROR(" ".join(e.messages)))
            return

        # Created by an admin on the command line, so active without approval.
        user = auth.get_user_model().objects.create_user(username, email, password)
        user.role = options["role"]
        user.save()

        self.stdout.write(self.style.SUCCESS(f"User {username} (id {user.id}, role {user.role}) created."))
