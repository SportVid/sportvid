from django.http import JsonResponse
from django.contrib import auth
from django.views.decorators.http import require_http_methods

from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import transaction
import logging
import json

from django.views import View
from django.contrib.auth import update_session_auth_hash

from backend.models import (
    SportVidUser,
    Video,
    TrackingData,
    PluginRun,
    PluginRunResult,
    Timeline,
    Annotation,
    AnnotationCategory,
    Shortcut,
    AnnotationShortcut,
    CalibrationAssets,
)

logger = logging.getLogger(__name__)


# def get_csrf_token(request):
#     token = get_token(request)
#     return JsonResponse({"token": token})


@ensure_csrf_cookie
def get_csrf_token(request):
    # token = get_token(request)
    return JsonResponse({"status": "ok"})


class UserGet(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"status": "error", "error": {"type": "not_authenticated"}})

        try:
            user = request.user
            return JsonResponse(
                {
                    "status": "ok",
                    "data": {
                        "id": user.id,
                        "username": user.get_username(),
                        "email": user.email,
                        "role": user.role,
                        "max_storage_size": user.max_storage_size,
                        "used_storage_size": user.used_storage_size,
                        "max_video_size": user.max_video_size,
                        "max_file_size": user.max_file_size,
                        "date_joined": user.date_joined
                    },
                }
            )
        except Exception:
            logger.exception('Failed to get user info')
            return JsonResponse({"status": "error"})


@require_http_methods(["POST"])
def login(request):
    try:
        body = request.body.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        body = request.body

    try:
        data = json.loads(body)
    except Exception as e:
        logger.exception('Could not load JSON for login')
        return JsonResponse({"status": "error"})

    if "name" not in data["params"]:
        logger.warning('Name not supplied for login')
        return JsonResponse({"status": "error", "message": "Name missing"})

    if "password" not in data["params"]:
        logger.warning('Password not supplied for login')
        return JsonResponse({"status": "error", "message": "Password missing"})

    username = data["params"]["name"]
    password = data["params"]["password"]

    if username == "" or password == "":
        return JsonResponse({"status": "error", "message": "Value empty"})

    user = auth.authenticate(username=username, password=password)
    if user is not None:
        auth.login(request, user)
        return JsonResponse(
            {
                "status": "ok",
                "data": {
                    "id": user.id,
                    "username": user.get_username(),
                    "email": user.email,
                    "role": user.role,
                    "max_storage_size": user.max_storage_size,
                    "used_storage_size": user.used_storage_size,
                    "max_video_size": user.max_video_size,
                    "max_file_size": user.max_file_size,
                    "date_joined": user.date_joined
                },
            }
        )

    return JsonResponse({"status": "error", "message": "Invalid login credentials"})


@require_http_methods(["POST"])
def register(request):
    try:
        body = request.body.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        body = request.body

    try:
        data = json.loads(body)
    except Exception as e:
        logger.exception('Could not load JSON for register')
        return JsonResponse({"status": "error"})

    if "name" not in data["params"]:
        logger.warning('Name not supplied for registration')
        return JsonResponse({"status": "error", "message": "Name missing"})

    if "password" not in data["params"]:
        logger.warning('Password not supplied for registration')
        return JsonResponse({"status": "error", "message": "Password missing"})

    if "email" not in data["params"]:
        logger.warning('EMail not supplied for registration')
        return JsonResponse({"status": "error", "message": "E-Mail missing"})

    username = data["params"]["name"]
    password = data["params"]["password"]
    email = data["params"]["email"]

    if username == "" or password == "" or email == "":
        logger.warning("An input is missing for registration.")
        return JsonResponse({"status": "error", "message": "Input empty"})

    if auth.get_user_model().objects.filter(username=username).count() > 0:
        logger.warning("User already exists. Abort.")
        return JsonResponse({"status": "error", "message": "User already exists"})

    # TODO Add EMail register here
    user = auth.get_user_model().objects.create_user(username, email, password)
    user = auth.authenticate(username=username, password=password)
    logger.info('New user registered')

    if user is not None:
        auth.login(request, user)
        return JsonResponse({"status": "ok"})

    return JsonResponse({"status": "error"})


@require_http_methods(["POST"])
def user_update(request):
    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "error": {"type": "not_authenticated"}})

    try:
        body = request.body.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        body = request.body

    try:
        data = json.loads(body)
    except Exception:
        logger.exception("Could not decode JSON for user_update")
        return JsonResponse({"status": "error"})

    params = data.get("params", {})
    update_type = params.get("update_type", "user")

    try:
        with transaction.atomic():
            if update_type == "user":
                user = request.user
                email = params.get("email", None)
                pwd_current = params.get("password_current", "")
                pwd_new = params.get("password_new", "")

                updated = False
                pwd_changed = False
                if email is not None and email != user.email:
                    user.email = email
                    updated = True

                if pwd_current or pwd_new:
                    if not pwd_current or not pwd_new:
                        return JsonResponse({"status": "error", "message": "Both current and new passwords are required"})
                    if not user.check_password(pwd_current):
                        return JsonResponse({"status": "error", "message": "Invalid current password"})
                    user.set_password(pwd_new)
                    pwd_changed = True
                    updated = True

                if updated:
                    user.save()
                    if pwd_changed:
                        try:
                            update_session_auth_hash(request, user)
                        except Exception:
                            logger.exception("Failed to update session auth hash after password change")

                return JsonResponse({"status": "ok"})
            
            elif update_type == "admin":
                user_id = params.get("id")
                if not user_id:
                    return JsonResponse({"status": "error", "message": "User ID missing for admin update"})

                try:
                    user = SportVidUser.objects.get(id=user_id)
                except SportVidUser.DoesNotExist:
                    return JsonResponse({"status": "error", "message": "User not found"})

                fields_to_update = ["email", "role", "max_storage_size", "max_video_size", "max_file_size"]
                updated = False

                for field in fields_to_update:
                    if field in params:
                        setattr(user, field, params[field])
                        updated = True

                if updated:
                    user.save()

                user_data = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "max_storage_size": user.max_storage_size,
                    "used_storage_size": user.used_storage_size,
                    "max_video_size": user.max_video_size,
                    "max_file_size": user.max_file_size,
                }

                return JsonResponse({"status": "ok", "data": user_data})

            else:
                return JsonResponse({"status": "error", "message": "Invalid update type"})
        

    except Exception:
        logger.exception("Failed to update user")
        return JsonResponse({"status": "error"})

@require_http_methods(["POST"])
def user_delete(request):
    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "error": {"type": "not_authenticated"}})

    try:
        body = request.body.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        body = request.body

    try:
        data = json.loads(body)
    except Exception:
        logger.exception("Could not decode JSON for user_delete")
        return JsonResponse({"status": "error"})

    params = data.get("params", {})
    update_type = params.get("update_type", "user")

    if update_type == "admin":
        user_id = params.get("id", None)

        if user_id == request.user.id:
            logger.warning("Admins cannot delete themselves via admin panel")
            return JsonResponse({"status": "error"})

        try:
            user = SportVidUser.objects.get(id=user_id)
        except SportVidUser.DoesNotExist:
            return JsonResponse({"status": "error", "message": "User not found"})
    
    else: 
        password = params.get("password", "")
        if password == "":
            logger.warning("Password not supplied for user_delete")
            return JsonResponse({"status": "error", "message": "Password missing"})

        user = request.user
        if not user.check_password(password):
            logger.warning("Invalid password supplied for user_delete")
            return JsonResponse({"status": "error", "message": "Invalid password"})

    try:
        with transaction.atomic():
            uid = user.id
            username = user.username

            # 1) Explicitly delete plugin run results for user's videos
            try:
                prrs = PluginRunResult.objects.filter(plugin_run__video__owner=user)
                for prr in prrs:
                    try:
                        prr.delete()
                    except Exception:
                        logger.exception(f"Failed deleting PluginRunResult {prr.id}")
            except Exception:
                logger.exception("Failed to enumerate PluginRunResults for user_delete")

            # 2) Delete plugin runs
            try:
                PluginRun.objects.filter(video__owner=user).delete()
            except Exception:
                logger.exception("Failed to delete PluginRuns for user_delete")

            # 3) Delete timelines (and related timeline segments/annotations)
            try:
                Timeline.objects.filter(video__owner=user).delete()
            except Exception:
                logger.exception("Failed to delete Timelines for user_delete")

            # 4) Delete annotations, categories, shortcuts and calibration assets
            try:
                Annotation.objects.filter(owner=user).delete()
                AnnotationCategory.objects.filter(owner=user).delete()
                Shortcut.objects.filter(owner=user).delete()
                AnnotationShortcut.objects.filter(annotation__owner=user).delete()
                AnnotationShortcut.objects.filter(shortcut__owner=user).delete()
                CalibrationAssets.objects.filter(owner=user).delete()
            except Exception:
                logger.exception("Failed to delete annotation-related objects for user_delete")

            # 5) Delete tracking data (post_delete will remove files)
            try:
                TrackingData.objects.filter(owner=user).delete()
            except Exception:
                logger.exception("Failed to delete TrackingData for user_delete")

            # 6) Delete videos (this will cascade and trigger post_delete for files)
            try:
                Video.objects.filter(owner=user).delete()
            except Exception:
                logger.exception("Failed to delete Videos for user_delete")

            # Finally delete user and log out
            user.delete()
            if update_type == "user":
                auth.logout(request)

        logger.info(f"User {username} (id={uid}) deleted")
        return JsonResponse({"status": "ok"})
    except Exception:
        logger.exception("Failed to delete user")
        return JsonResponse({"status": "error"})


@require_http_methods(["POST"])
def logout(request):
    auth.logout(request)
    return JsonResponse({"status": "ok"})

@require_http_methods(["GET"])
def user_list(request):
    if request.user.role != "admin":
        return JsonResponse({"status": "error", "error": "not_authorized"})

    users = SportVidUser.objects.all()
    
    data = [u.to_dict() for u in users]

    return JsonResponse({"status": "ok", "data": data})
