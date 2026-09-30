from django.db import migrations


def backfill(apps, schema_editor):
    """Pengajuan lama yang sudah mengunggah bukti tapi statusnya masih
    Menunggu Pembayaran dinaikkan menjadi BUKTI_TERUNGGAH."""
    Pengajuan = apps.get_model("pas", "Pengajuan")
    PaymentTransaction = apps.get_model("pembayaran", "PaymentTransaction")

    nomor = (
        PaymentTransaction.objects.filter(status="PENDING", manual__isnull=False)
        .values_list("invoice__pengajuan_id", flat=True)
    )
    for pk in set(nomor):
        Pengajuan.objects.filter(pk=pk, status="MENUNGGU_PEMBAYARAN").update(
            status="BUKTI_TERUNGGAH"
        )


def balikkan(apps, schema_editor):
    Pengajuan = apps.get_model("pas", "Pengajuan")
    Pengajuan.objects.filter(status="BUKTI_TERUNGGAH").update(
        status="MENUNGGU_PEMBAYARAN"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("pas", "0008_alter_pengajuan_status_alter_statusriwayat_status"),
        ("pembayaran", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill, balikkan),
    ]
