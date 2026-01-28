from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET


@require_GET
@csrf_exempt
def healthz(_request):
    """Public health-check endpoint for container orchestration."""
    return JsonResponse({"status": "ok"})
