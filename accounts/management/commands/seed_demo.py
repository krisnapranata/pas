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
            "avsec1": ("AVSEC", "demo123", "Agus", "Avsec"),
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

        def contoh(layanan, keterangan, **defaults):
            """Contoh pengajuan — dicocokkan lewat `keterangan` agar seed tidak
            menduplikasi data saat status sudah berubah oleh pengujian/manual."""
            ada = Pengajuan.objects.filter(
                pemohon=pemohon, keterangan=keterangan
            ).first()
            if ada:
                return ada, False
            obj = Pengajuan.objects.create(
                pemohon=pemohon, layanan=layanan, keterangan=keterangan, **defaults
            )
            return obj, True

        # Pengajuan 1: MENUNGGU_PEMBAYARAN (sudah disetujui operasi, invoice aktif)
        p1, _ = contoh(
            layanan_group,
            "Penyambutan tamu VIP",
            status=Pengajuan.Status.MENUNGGU_PEMBAYARAN,
            tanggal_pelaksanaan=timezone.localdate() + timezone.timedelta(days=5),
            tujuan="PT Angkasa Logistik",
            jumlah_tamu=10,
            jumlah_pendamping=8,
            pic_nama="Budi Santoso",
            pic_jabatan="Manajer Operasional",
            pic_no_hp="081234567890",
        )
        p1.simpan_snapshot_tarif()
        p1.nomor_pengajuan = p1.nomor_pengajuan or p1._generate_nomor()
        p1.save()

        # Pengajuan 2: DIBAYAR (menunggu diteruskan Komersil ke Operasi)
        p2, _ = contoh(
            layanan_greet,
            "Greet service kedatangan",
            status=Pengajuan.Status.DIBAYAR,
            tanggal_pelaksanaan=timezone.localdate() + timezone.timedelta(days=7),
            jumlah_tamu=3,
            jumlah_pendamping=2,
            pic_nama="Budi Santoso",
            pic_no_hp="081234567890",
            pemohon_nama="Budi Santoso",
            pemohon_no_hp="081234567890",
        )
        p2.simpan_snapshot_tarif()
        p2.nomor_pengajuan = p2.nomor_pengajuan or p2._generate_nomor()
        p2.save()

        # Pengajuan 3: PAS terbit hari ini (untuk panel masa berlaku & AOCH)
        p3, _ = contoh(
            layanan_greet,
            "PAS visitor hari ini",
            status=Pengajuan.Status.PAS_TERBIT,
            tanggal_pelaksanaan=timezone.localdate(),
            jumlah_tamu=2,
            jumlah_pendamping=2,
            pic_nama="Budi Santoso",
            pic_no_hp="081234567890",
            pemohon_nama="Budi Santoso",
            pemohon_no_hp="081234567890",
            tanggal_berlaku_pas=timezone.localdate(),
        )
        p3.simpan_snapshot_tarif()
        p3.nomor_pengajuan = p3.nomor_pengajuan or p3._generate_nomor()
        p3.tanggal_berlaku_pas = p3.tanggal_berlaku_pas or timezone.localdate()
        p3.save()

        # Invoice untuk p1 (belum dibayar)
        inv, created = Invoice.objects.get_or_create(pengajuan=p1)
        if created:
            inv.subtotal = p1.total
            inv.hitung_total()
            inv.status = Invoice.Status.UNPAID
            inv.nomor_invoice = inv._generate_nomor()
            inv.save()

        # Invoice p2 sudah lunas (siap diteruskan ke Operasi)
        inv2, created2 = Invoice.objects.get_or_create(pengajuan=p2)
        if created2:
            inv2.subtotal = p2.total
            inv2.hitung_total()
            inv2.status = Invoice.Status.PAID
            inv2.nomor_invoice = inv2._generate_nomor()
            inv2.save()

        self.stdout.write(self.style.SUCCESS("\n=== DATA DEMO SIAP ==="))
        creds = [
            ("admin (Administrator)", "admin / admin123"),
            ("pemohon1 (Pemohon)", "pemohon1 / pemohon123"),
            ("komersil1 (Komersil)", "komersil1 / demo123"),
            ("operasi1 (Operasi)", "operasi1 / demo123"),
            ("aoch1 (AOCH)", "aoch1 / demo123"),
            ("avsec1 (Avsec)", "avsec1 / demo123"),
        ]
        for label, cre in creds:
            self.stdout.write(f"  {label:<28} {cre}")
        self.stdout.write(self.style.SUCCESS("\nLink:"))
        self.stdout.write("  Register : http://127.0.0.1:8000/register/")
        self.stdout.write("  Login    : http://127.0.0.1:8000/login/")
        self.stdout.write("  Admin    : http://127.0.0.1:8000/admin/")
