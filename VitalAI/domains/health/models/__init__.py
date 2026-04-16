"""Health domain models."""

from VitalAI.domains.health.models.alert_history import HealthAlertEntry, HealthAlertSnapshot
from VitalAI.domains.health.models.health_alert_record import HealthAlertRecordModel

__all__ = ["HealthAlertEntry", "HealthAlertRecordModel", "HealthAlertSnapshot"]
