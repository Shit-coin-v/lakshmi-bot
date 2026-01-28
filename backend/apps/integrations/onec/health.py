from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.api.security import require_onec_auth


@csrf_exempt
@require_POST
@require_onec_auth
def onec_health(_request):
    return JsonResponse({"status": "ok"})
