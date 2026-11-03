import os
import json
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.conf import settings

from backend.models import (
    SportVidUser,
    Video,
    AnnotationCategory,
    Annotation,
    Shortcut,
    Timeline
)
from backend.plugin_manager import PluginManager


class Command(BaseCommand):
    help = "..."

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        for x in SportVidUser.objects.raw(
            'SELECT "auth_user"."id", "auth_user"."password", "auth_user"."last_login", "auth_user"."is_superuser", "auth_user"."username", "auth_user"."first_name", "auth_user"."last_name", "auth_user"."email", "auth_user"."is_staff", "auth_user"."is_active", "auth_user"."date_joined" FROM "auth_user"'):
            user = SportVidUser()
            user.id = x.id
            user.password = x.password
            user.last_login = x.last_login
            user.is_superuser = x.is_superuser
            user.username = x.username
            user.first_name = x.first_name
            user.last_name = x.last_name
            user.email = x.email
            user.is_staff = x.is_staff
            user.is_active = x.is_active
            user.date_joined = x.date_joined

            user.save()