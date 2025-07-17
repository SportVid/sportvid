# TODO

import json
import logging
from functools import wraps

from django.views import View
from django.http import JsonResponse


logger = logging.getLogger(__name__)

class BoundingBoxChange(View):
    pass