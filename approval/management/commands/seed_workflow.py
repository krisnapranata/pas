from django.core.management.base import BaseCommand

from approval.models import ApprovalStep, ApprovalWorkflow


class Command(BaseCommand):
    help = "Seed default approval workflow"

    def handle(self, *args, **options):
        wf, created = ApprovalWorkflow.objects.get_or_create(
            kode="DEFAULT",
            defaults={"nama": "Workflow Approval Default", "is_default": True, "deskripsi": "Admin PAS -> Verifikator -> Security/AVSEC -> Pejabat Berwenang"},
        )
        steps = [
            (1, "ADMIN_PAS", "Admin PAS"),
            (2, "VERIFIKATOR", "Verifikator"),
            (3, "SECURITY", "Security / AVSEC"),
            (4, "APPROVER", "Pejabat Berwenang"),
        ]
        for level, role, nama in steps:
            ApprovalStep.objects.get_or_create(
                workflow=wf, level=level,
                defaults={"role": role, "nama": nama},
            )
        self.stdout.write(self.style.SUCCESS(f"Workflow default siap ({'dibuat' if created else 'ada'})."))
