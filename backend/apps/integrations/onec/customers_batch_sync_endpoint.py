from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.api.security import require_onec_auth


@csrf_exempt
@require_POST
@require_onec_auth
def onec_customers_batch_sync(request):
    from apps.integrations.onec.customers_batch_sync import onec_customers_batch_sync_impl

    return onec_customers_batch_sync_impl(request)
