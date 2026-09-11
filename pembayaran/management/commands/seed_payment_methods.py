from django.core.management.base import BaseCommand

from pembayaran.models import PaymentMethod


class Command(BaseCommand):
    help = "Seed master data metode pembayaran"

    def handle(self, *args, **options):
        methods = [
            ("QRIS", "QRIS", "QRIS", "", 1, {}),
            ("BCA_VA", "BCA Virtual Account", "VIRTUAL_ACCOUNT", "", 2, {}),
            ("BNI_VA", "BNI Virtual Account", "VIRTUAL_ACCOUNT", "", 3, {}),
            ("BRI_VA", "BRI Virtual Account", "VIRTUAL_ACCOUNT", "", 4, {}),
            ("MANDIRI_VA", "Mandiri Virtual Account", "VIRTUAL_ACCOUNT", "", 5, {}),
            (
                "MANUAL_TRANSFER",
                "Transfer Manual",
                "MANUAL_TRANSFER",
                "",
                6,
                {"bank": "BCA", "norek": "1234567890", "nama": "PT Bandara Layanan"},
            ),
            ("CASH", "Tunai", "CASH", "", 7, {}),
            ("DANA", "DANA", "E_WALLET", "", 8, {}),
            ("GOPAY", "GoPay", "E_WALLET", "", 9, {}),
            ("OVO", "OVO", "E_WALLET", "", 10, {}),
        ]
        created = 0
        for code, name, type_, provider, sort, config in methods:
            obj, c = PaymentMethod.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "type": type_,
                    "provider": provider,
                    "sort_order": sort,
                    "configuration": config,
                },
            )
            if not c and config and not obj.configuration:
                obj.configuration = config
                obj.save(update_fields=["configuration"])
            created += int(c)
        self.stdout.write(self.style.SUCCESS(f"Seed metode pembayaran selesai ({created} baru)."))
