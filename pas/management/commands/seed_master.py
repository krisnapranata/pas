from django.core.management.base import BaseCommand

from pas.models import AreaAkses, JenisPAS, Persyaratan


class Command(BaseCommand):
    help = "Seed master data PAS Bandara (JenisPAS, Persyaratan, AreaAkses)"

    def handle(self, *args, **options):
        area = {
            "LANDSIDE": ("Area Landside", "Area umum/landside bandara"),
            "AIRSIDE": ("Area Airside", "Area terbatas airside (apron, runway)"),
            "TERMINAL": ("Area Terminal", "Area terminal penumpang"),
            "KARGO": ("Area Kargo", "Area kargo / gudang"),
        }
        for kode, (nama, desk) in area.items():
            AreaAkses.objects.get_or_create(kode=kode, defaults={"nama": nama, "deskripsi": desk})

        jenis = [
            ("PAS Harian", "HARIAN", "Akses harian", 1, 15000, True, True),
            ("PAS Sementara", "SEMENTARA", "PAS sementara", 7, 50000, True, True),
            ("PAS Bulanan", "BULANAN", "Akses bulanan", 30, 150000, True, True),
            ("PAS Tahunan", "TAHUNAN", "Akses tahunan", 365, 1000000, True, True),
            ("PAS Orang", "ORANG", "PAS untuk personal", 30, 100000, True, True),
            ("PAS Kendaraan", "KENDARAAN", "PAS untuk kendaraan operasional", 365, 2000000, True, True),
            ("PAS Visitor", "VISITOR", "PAS pengunjung", 1, 25000, False, False),
        ]
        persyaratan_map = {
            "TAHUNAN": [
                ("KTP", "Kartu Tanda Penduduk", "jpg,png,pdf", 2),
                ("FOTO", "Pas Foto terbaru", "jpg,png", 2),
                ("SURAT_PERMOHONAN", "Surat Permohonan", "pdf", 5),
                ("SURAT_PENUGASAN", "Surat Penugasan", "pdf", 5),
                ("SURAT_PERNYATAAN", "Surat Pernyataan", "pdf", 5),
            ],
            "KENDARAAN": [
                ("STNK", "STNK Kendaraan", "jpg,png,pdf", 2),
                ("FOTO_KENDARAAN", "Foto Kendaraan", "jpg,png", 2),
                ("SURAT_PERMOHONAN", "Surat Permohonan", "pdf", 5),
                ("DOKUMEN_PERUSAHAAN", "Dokumen Perusahaan", "pdf", 5),
            ],
        }

        for nama, kode, desk, masa, biaya, screening, approval in jenis:
            jp, created = JenisPAS.objects.get_or_create(
                kode=kode,
                defaults={
                    "nama": nama,
                    "deskripsi": desk,
                    "masa_berlaku_hari": masa,
                    "biaya": biaya,
                    "butuh_screening": screening,
                    "butuh_approval": approval,
                },
            )
            if created:
                self.stdout.write(f"  JenisPAS {kode} dibuat")
            for idx, (pnama, pdesk, fmt, msize) in enumerate(persyaratan_map.get(kode, []), 1):
                Persyaratan.objects.get_or_create(
                    jenis_pas=jp,
                    kode=pnama,
                    defaults={
                        "nama": pnama,
                        "deskripsi": pdesk,
                        "format_file": fmt,
                        "max_size": msize,
                        "urutan": idx,
                    },
                )

        self.stdout.write(self.style.SUCCESS("Seed master data selesai."))
