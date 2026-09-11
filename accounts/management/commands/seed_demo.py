from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from pas.models import Layanan, Pengajuan
from pembayaran.models import Invoice


class Command(BaseCommand):
    help = "Seed data demo (user role, contoh alur layanan)"

    def handle(self, *args, **options):
        # Superuser / Administrator
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin", email="admin@bandara.local", password="admin123"
            )
            self.stdout.write("  superuser admin dibuat")

        users = {
            "pemohon1": ("PEMOHON", "pemohon123", "Budi", "Santoso"),
            "komersil1": ("KOMERSIL", "demo123", "Dewi", "Komersil"),
            "operasi1": ("OPERASI", "demo123", "Rudi", "Operasi"),
            "aoch1": ("AOCH", "demo123", "Sari", "AOCH"),
        }
        user_objs = {}
        for uname, (role, pw, first, last) in users.items():
            u, created = User.objects.get_or_create(
                username=uname,
                defaults={
                    "role": role,
                    "first_name": first,
                    "last_name": last,
                    "email": f"{uname}@bandara.local",
                },
            )
            if created:
                u.set_password(pw)
                u.save()
            user_objs[uname] = u
            self.stdout.write(f"  user {uname} ({role})")

        pemohon = user_objs["pemohon1"]
        layanan_greet = Layanan.objects.get(kode_layanan="GREET")
        layanan_group = Layanan.objects.get(kode_layanan="GREET_GROUP")

        # Pengajuan 1: MENUNGGU_PEMBAYARAN (sudah disetujui operasi, invoice aktif)
        p1, _ = Pengajuan.objects.get_or_create(
            pemohon=pemohon,
            layanan=layanan_group,
            status=Pengajuan.Status.MENUNGGU_PEMBAYARAN,
            defaults={
                "tanggal_pelaksanaan": timezone.now().date() + timezone.timedelta(days=5),
                "tujuan": "PT Angkasa Logistik",
                "jumlah_tamu": 10,
                "jumlah_pendamping": 8,
                "keterangan": "Penyambutan tamu VIP",
                "pic_nama": "Budi Santoso",
                "pic_jabatan": "Manajer Operasional",
                "pic_no_hp": "081234567890",
            },
        )
        p1.simpan_snapshot_tarif()
        p1.nomor_pengajuan = p1.nomor_pengajuan or p1._generate_nomor()
        p1.save()

        # Pengajuan 2: DIAJUKAN (menunggu verifikasi komersil)
        p2, _ = Pengajuan.objects.get_or_create(
            pemohon=pemohon,
            layanan=layanan_greet,
            status=Pengajuan.Status.DIAJUKAN,
            defaults={
                "tanggal_pelaksanaan": timezone.now().date() + timezone.timedelta(days=7),
                "jumlah_tamu": 3,
                "jumlah_pendamping": 2,
                "keterangan": "Greet service kedatangan",
            },
        )
        p2.simpan_snapshot_tarif()
        p2.nomor_pengajuan = p2.nomor_pengajuan or p2._generate_nomor()
        p2.save()

        # Invoice untuk p1 (belum dibayar)
        inv, created = Invoice.objects.get_or_create(pengajuan=p1)
        if created:
            inv.subtotal = p1.total
            inv.hitung_total()
            inv.status = Invoice.Status.UNPAID
            inv.nomor_invoice = inv._generate_nomor()
            inv.save()

        self.stdout.write(self.style.SUCCESS("\n=== DATA DEMO SIAP ==="))
        creds = [
            ("admin (Administrator)", "admin / admin123"),
            ("pemohon1 (Pemohon)", "pemohon1 / pemohon123"),
            ("komersil1 (Komersil)", "komersil1 / demo123"),
            ("operasi1 (Operasi)", "operasi1 / demo123"),
            ("aoch1 (AOCH)", "aoch1 / demo123"),
        ]
        for label, cre in creds:
            self.stdout.write(f"  {label:<28} {cre}")
        self.stdout.write(self.style.SUCCESS("\nLink:"))
        self.stdout.write("  Register : http://127.0.0.1:8000/register/")
        self.stdout.write("  Login    : http://127.0.0.1:8000/login/")
        self.stdout.write("  Admin    : http://127.0.0.1:8000/admin/")
