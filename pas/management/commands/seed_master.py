from django.core.management.base import BaseCommand

from pas.models import DaftarHitam, Layanan


LAYANAN_MASTER = [
    {
        "kode_layanan": "DEP_ASSIST",
        "nama_layanan": "Departure Assistance (maks 5 orang)",
        "deskripsi": "Pendampingan keberangkatan, maksimum 5 orang.",
        "lokasi": Layanan.Lokasi.DEPARTURE,
        "minimal_pendamping": 1,
        "maksimal_pendamping": 5,
        "jenis_tarif": Layanan.JenisTarif.FIXED,
        "harga": 1000000,
        "satuan": "Per pengajuan",
    },
    {
        "kode_layanan": "GREET",
        "nama_layanan": "Greet Service (Maks. 5 orang)",
        "deskripsi": "Layanan penyambutan tamu, maksimum 5 orang.",
        "lokasi": Layanan.Lokasi.ARRIVAL,
        "minimal_pendamping": 1,
        "maksimal_pendamping": 5,
        "jenis_tarif": Layanan.JenisTarif.FIXED,
        "harga": 1000000,
        "satuan": "Per pengajuan",
    },
    {
        "kode_layanan": "GREET_DESK",
        "nama_layanan": "Greet & Desk Service (Maks. 5 orang)",
        "deskripsi": "Layanan penyambutan dan desk service, maksimum 5 orang.",
        "lokasi": Layanan.Lokasi.ARRIVAL,
        "minimal_pendamping": 1,
        "maksimal_pendamping": 5,
        "jenis_tarif": Layanan.JenisTarif.FIXED,
        "harga": 1500000,
        "satuan": "Per pengajuan",
    },
    {
        "kode_layanan": "GREET_GROUP",
        "nama_layanan": "Greet Group Service (s.d. 10 orang)",
        "deskripsi": "Layanan penyambutan grup sampai 10 orang.",
        "lokasi": Layanan.Lokasi.ARRIVAL,
        "minimal_pendamping": 1,
        "maksimal_pendamping": 10,
        "jenis_tarif": Layanan.JenisTarif.FIXED,
        "harga": 2000000,
        "satuan": "Per pengajuan",
    },
    {
        "kode_layanan": "GREET_DESK_GROUP",
        "nama_layanan": "Greet & Desk Group Service (Meja & Maks. 10 orang)",
        "deskripsi": "Layanan penyambutan grup dengan meja desk, maksimum 10 orang.",
        "lokasi": Layanan.Lokasi.ARRIVAL,
        "minimal_pendamping": 1,
        "maksimal_pendamping": 10,
        "jenis_tarif": Layanan.JenisTarif.FIXED,
        "harga": 2500000,
        "satuan": "Per pengajuan",
    },
]


class Command(BaseCommand):
    help = "Seed master data layanan (Departure/Arrival) dan contoh daftar hitam"

    def handle(self, *args, **options):
        for item in LAYANAN_MASTER:
            _, created = Layanan.objects.get_or_create(
                kode_layanan=item["kode_layanan"], defaults=item
            )
            self.stdout.write(
                f"  {'Dibuat' if created else 'Sudah ada (tidak diubah)'} layanan {item['kode_layanan']}"
            )

        daftar_hitam = [
            {
                "tipe": DaftarHitam.Tipe.ORANG,
                "nik": "3175000000000001",
                "nama": "Budi Hitam",
                "alasan": "Terdaftar dalam daftar hitam keamanan bandara.",
            },
            {
                "tipe": DaftarHitam.Tipe.PERUSAHAAN,
                "nik": "",
                "nama": "PT Contoh Terlarang",
                "alasan": "Perusahaan tidak diizinkan mendapatkan PAS.",
            },
        ]
        for item in daftar_hitam:
            _, c = DaftarHitam.objects.get_or_create(
                tipe=item["tipe"],
                nama=item["nama"],
                defaults={"nik": item["nik"], "alasan": item["alasan"], "aktif": True},
            )
            self.stdout.write(
                f"  {'Dibuat' if c else 'Sudah ada (tidak diubah)'} DaftarHitam [{item['tipe']}] {item['nama']}"
            )

        self.stdout.write(self.style.SUCCESS("Seed master data selesai."))
