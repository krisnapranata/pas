from django.contrib import admin

from .models import Approval, ApprovalStep, ApprovalWorkflow


class ApprovalStepInline(admin.TabularInline):
    model = ApprovalStep
    extra = 0


@admin.register(ApprovalWorkflow)
class ApprovalWorkflowAdmin(admin.ModelAdmin):
    list_display = ("nama", "kode", "jenis_pas", "is_default", "aktif")
    list_filter = ("aktif", "is_default")
    search_fields = ("nama", "kode")
    inlines = [ApprovalStepInline]


@admin.register(ApprovalStep)
class ApprovalStepAdmin(admin.ModelAdmin):
    list_display = ("workflow", "level", "role", "nama", "aktif")
    list_filter = ("workflow", "role", "aktif")


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = ("pengajuan", "level", "role", "approver", "status", "approved_at")
    list_filter = ("status", "role")
    search_fields = ("pengajuan__nomor_pengajuan",)
