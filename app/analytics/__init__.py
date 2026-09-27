# app/analytics/__init__.py

from .forecast import ForecastAnalytics
from .inventory import InventoryAnalytics
from .kpis import KPIAnalytics
from .procurement import ProcurementAnalytics
from .suppliers import SupplierAnalytics

__all__ = [
    "ForecastAnalytics",
    "InventoryAnalytics",
    "KPIAnalytics",
    "ProcurementAnalytics",
    "SupplierAnalytics",
]