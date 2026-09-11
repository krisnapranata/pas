from django.core.management.base import BaseCommand

from pas.models import DaftarHitam, Layanan


class Command(BaseCommand):
    help = "Seed master data layanan dan contoh daftar hitam"

    def handle(self, *args, **options):
        layanan = [
            {
                "kode_layanan": "GREET",
                "nama_layanan": "Greet Service",
                "deskripsi": "Layanan penyambutan tamu",
                "minimal_pendamping": 1,
                "maksimal_pendamping": 5,
                "jenis_tarif": Layanan.JenisTarif.PER_HARI,
                "harga": 1000000,
                "satuan": "Per hari",
            },
            {
                "kode_layanan": "GREET_DESK",
                "nama_layanan": "Greet & Desk Service",
                "deskripsi": "Layanan penyambutan dan desk service",
                "minimal_pendamping": 1,
                "maksimal_pendamping": 5,
                "jenis_tarif": Layanan.JenisTarif.PER_HARI,
                "harga": 1500000,
                "satuan": "Per hari",
            },
            {
                "kode_layanan": "GREET_GROUP",
                "nama_layanan": "Greet Group Service",
                "deskripsi": "Layanan penyambutan grup",
                "minimal_pendamping": 6,
                "maksimal_pendamping": 0,
                "jenis_tarif": Layanan.JenisTarif.PER_PENDAMPING_PER_HARI,
                "harga": 200000,
                "satuan": "Per pendamping / hari",
            },
        ]

        for item in layanan:
            layanan_obj, created = Layanan.objects.get_or_create(
                kode_layanan=item["kode_layanan"],
                defaults={
                    "nama_layanan": item["nama_layanan"],
                    "deskripsi": item["deskripsi"],
                    "minimal_pendamping": item["minimal_pendamping"],
                    "maksimal_pendamping": item["maksimal_pendamping"],
                    "jenis_tarif": item["jenis_tarif"],
                    "harga": item["harga"],
                    "satuan": item["satuan"],
                },
            )
            if created:
                self.stdout.write(f"  Layanan {item['kode_layanan']} dibuat")

        # Contoh daftar hitam
        daftar_hitam = [
            ("ORANG", "Budi Hitam", "Nama terdaftar dalam daftar hitam keamanan bandara."),
            ("PERUSAHAAN", "PT Contoh Terlarang", "Perusahaan tidak diizinkan mendapatkan PAS."),
        ]
        for tipe, nama, alasan in daftar_hitam:
            _, c = DaftarHitam.objects.get_or_create(
                tipe=tipe, nama=nama, defaults={"alasan": alasan}
            )
            if c:
                self.stdout.write(f"  DaftarHitam [{tipe}] {nama} dibuat")

        self.stdout.write(self.style.SUCCESS("Seed master data selesai."))
