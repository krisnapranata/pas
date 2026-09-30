from django.db import migrations
from django.utils import timezone

TERBIT = ("PAS_TERBIT", "DILAKSANAKAN", "SELESAI")


def backfill(apps, schema_editor):
    Pengajuan = apps.get_model("pas", "Pengajuan")
    for p in Pengajuan.objects.filter(tanggal_berlaku_pas__isnull=True, status__in=TERBIT):
        p.tanggal_berlaku_pas = p.tanggal_pelaksanaan or timezone.localtime(p.created_at).date()
        p.save(update_fields=["tanggal_berlaku_pas"])


def unbackfill(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("pas", "0005_daftarhitam_nik_dokumenpendamping_nik_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill, unbackfill),
    ]
