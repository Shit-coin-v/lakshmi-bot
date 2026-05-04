from rest_framework.response import Response

from apps.crm_api.views._base import CRMAPIView


# Стаб-матрица. Реальная классификация — отдельный milestone (M2).
_STUB_MATRIX_SKU = {
    "AX": 84, "AY": 56, "AZ": 18,
    "BX": 142, "BY": 168, "BZ": 92,
    "CX": 218, "CY": 384, "CZ": 240,
}
_STUB_MATRIX_REVENUE = {
    "AX": 4_830_000, "AY": 2_980_000, "AZ": 840_000,
    "BX": 1_640_000, "BY": 1_390_000, "BZ": 680_000,
    "CX": 490_000, "CY": 470_000, "CZ": 290_000,
}


def _share_from_counts(matrix: dict[str, int]) -> dict[str, float]:
    total = sum(matrix.values()) or 1
    return {k: round(v * 100.0 / total, 1) for k, v in matrix.items()}


class AbcXyzView(CRMAPIView):
    """GET /api/crm/abc-xyz/ — матрица распределения SKU по ABC×XYZ.

    На M1 возвращает стаб-данные. Реальная классификация — отдельная
    задача (требует pipeline для расчёта по продажам)."""

    def get(self, request):
        return Response({
            "matrixSku": _STUB_MATRIX_SKU,
            "matrixRevenue": _STUB_MATRIX_REVENUE,
            "matrixShare": _share_from_counts(_STUB_MATRIX_SKU),
        })
