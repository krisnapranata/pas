from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    action = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} - {self.object_id or self.model_name}"


def log_action(request, action, model_name="", object_id="", old_value="", new_value=""):
    """Catat aksi penting ke audit log."""
    if request is None:
        return None
    ip = request.META.get("REMOTE_ADDR")
    ua = request.META.get("HTTP_USER_AGENT", "")[:255]
    return AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        old_value=old_value,
        new_value=new_value,
        ip_address=ip,
        user_agent=ua,
    )
