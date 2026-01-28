from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.api.security import require_onec_auth


@csrf_exempt
@require_POST
@require_onec_auth
def onec_product_sync(request):
    from apps.integrations.onec.product_sync import onec_product_sync_impl

    return onec_product_sync_impl(request)
