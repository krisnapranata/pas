from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Notifikasi dalam aplikasi (§11)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifikasi"
    )
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    pengajuan = models.ForeignKey(
        "pas.Pengajuan",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifikasi",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notifikasi"
        verbose_name_plural = "Notifikasi"

    def __str__(self):
        return f"{self.user.username} - {self.title}"
