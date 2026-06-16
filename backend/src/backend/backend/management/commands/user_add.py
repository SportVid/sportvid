from django.core.management.base import BaseCommand
from django.contrib import auth


class Command(BaseCommand):
    help = "..."

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        username = input("username: ")
        password = input("password: ")
        email = input("email: ")

        print(f"{username} {password}")

        if auth.get_user_model().objects.filter(username=username).count() > 0:
            self.stdout.write(self.style.ERROR(f"User with name {username} already exists."))

        user = auth.get_user_model().objects.create_user(username, email, password)
        user.save()

        self.stdout.write(self.style.SUCCESS(f"User with id {user.id} created."))
