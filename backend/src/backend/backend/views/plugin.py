import logging
from django.views import View
from django.http import HttpResponse, JsonResponse
from django.conf import settings

from backend.models import Video, PluginRun
from backend.permissions import readable
from backend.plugin_catalogue import available_plugins
from backend.plugin_manager import PluginManager


logger = logging.getLogger(__name__)


class PluginAvailable(View):
    """Backend plugins whose Ray plugins are all deployed (audit B6).

    plugins is null when the analyser cannot be asked; clients then offer everything.
    """

    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"status": "error", "type": "not_authenticated"}, status=401)
        return JsonResponse({"status": "ok", "plugins": available_plugins()})


class PluginList(View):
    def get(self, request):
        plugin_manager = PluginManager()
        try:
            if not request.user.is_authenticated:
                return JsonResponse({"status": "error"})
            video_id = request.GET.get("video_id")
            if video_id:
                video_db = readable(Video, request.user).get(id=video_id)
                analyses = PluginRun.objects.filter(video=video_db)
            else:
                analyses = readable(PluginRun, request.user)

            add_results = request.GET.get("add_results")
            if add_results:
                entries = []
                for x in analyses:
                    results = plugin_manager.get_results(x)
                    if results:
                        entries.append({**x.to_dict(), "results": results})
                    else:
                        entries.append({**x.to_dict()})
            else:
                entries = [x.to_dict() for x in analyses]

            return JsonResponse({"status": "ok", "entries": entries})
        except Exception:
            logger.exception('Failed to list plugins')
            return JsonResponse({"status": "error"})
