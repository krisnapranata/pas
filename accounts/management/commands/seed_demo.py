from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from pas.models import AreaAkses, JenisPAS, PASCard, PengajuanPAS
from perusahaan.models import Perusahaan
from screening.models import ScreeningBooking, ScreeningSchedule
from pembayaran.models import Invoice, PaymentMethod, PaymentTransaction


class Command(BaseCommand):
    help = "Seed data demo lengkap (user role, perusahaan, contoh alur)"

    def handle(self, *args, **options):
        # ---------- Superuser ----------
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin", email="admin@bandara.local", password="admin123"
            )
            self.stdout.write("  superuser admin dibuat")

        # ---------- User role demo ----------
        users = {
            "pemohon1": ("PEMOHON", "pemohon123", "Budi", "Santoso", False),
            "verifikator1": ("VERIFIKATOR", "demo123", "Dewi", "Verifikator", True),
            "petugas_screening1": ("PETUGAS_SCREENING", "demo123", "Rudi", "Screening", True),
            "petugas_bayar1": ("PETUGAS_PEMBAYARAN", "demo123", "Sari", "Keuangan", True),
            "approver1": ("APPROVER", "demo123", "Andi", "Pejabat", True),
            "security1": ("SECURITY", "demo123", "Joko", "AVSEC", True),
            "management1": ("MANAGEMENT", "demo123", "Maya", "Manajemen", True),
        }
        user_objs = {}
        for uname, (role, pw, first, last, staff) in users.items():
            u, created = User.objects.get_or_create(
                username=uname,
                defaults={
                    "role": role,
                    "first_name": first,
                    "last_name": last,
                    "is_staff": staff,
                    "email": f"{uname}@bandara.local",
                },
            )
            if created:
                u.set_password(pw)
                u.save()
            user_objs[uname] = u
            self.stdout.write(f"  user {uname} ({role})")

        # ---------- Perusahaan ----------
        perusahaan_data = [
            ("PT Angkasa Logistik", "1234567890123", "01.234.567.8-901.000", "Budi Santoso", True),
            ("PT Garuda Cargo Nusantara", "2345678901234", "02.345.678.9-012.000", "Siti Aminah", True),
            ("CV Mitra Bandara", "3456789012345", "03.456.789.0-123.000", "Hendra Wijaya", True),
        ]
        perusahaan = {}
        for nama, nib, npwp, pic, aktif in perusahaan_data:
            p, _ = Perusahaan.objects.get_or_create(
                nama=nama,
                defaults={"nib": nib, "npwp": npwp, "pic": pic, "status_aktif": aktif},
            )
            perusahaan[nama] = p
            self.stdout.write(f"  perusahaan {nama}")

        # ---------- Referensi master ----------
        jenis_tahunan = JenisPAS.objects.get(kode="TAHUNAN")
        jenis_bulanan = JenisPAS.objects.get(kode="BULANAN")
        area = list(AreaAkses.objects.filter(status_aktif=True))

        pemohon = user_objs["pemohon1"]
        now = timezone.now()

        # ---------- Pengajuan 1: PAS_ISSUED + PASCard + QR ----------
        p1, _ = PengajuanPAS.objects.get_or_create(
            pemohon=pemohon,
            jenis_pas=jenis_tahunan,
            status=PengajuanPAS.Status.PAS_ISSUED,
            defaults={
                "perusahaan": perusahaan["PT Angkasa Logistik"],
                "tanggal_mulai": now.date(),
                "keperluan": "Akses operasional area airside",
            },
        )
        p1.nomor_pengajuan = p1.nomor_pengajuan or p1._generate_nomor()
        p1.save()

        if not hasattr(p1, "pas_card"):
            card = PASCard.objects.create(
                pengajuan=p1,
                jenis_pas=jenis_tahunan,
                tanggal_berlaku=now.date(),
                issued_by=user_objs["approver1"],
            )
            card.tanggal_expired = card.tanggal_berlaku + timedelta(days=jenis_tahunan.masa_berlaku_hari)
            card.save(update_fields=["tanggal_expired"])
            self.stdout.write(f"  PASCard {card.nomor_pas} + QR")

        # ---------- Pengajuan 2: SUBMITTED (menunggu verifikasi) ----------
        p2, _ = PengajuanPAS.objects.get_or_create(
            pemohon=pemohon,
            jenis_pas=jenis_bulanan,
            status=PengajuanPAS.Status.SUBMITTED,
            defaults={
                "perusahaan": perusahaan["CV Mitra Bandara"],
                "keperluan": "Kunjungan rutin bulanan",
            },
        )
        p2.nomor_pengajuan = p2.nomor_pengajuan or p2._generate_nomor()
        p2.save()

        # ---------- Pengajuan 3: DRAFT ----------
        p3, _ = PengajuanPAS.objects.get_or_create(
            pemohon=pemohon,
            jenis_pas=jenis_bulanan,
            status=PengajuanPAS.Status.DRAFT,
            defaults={
                "perusahaan": perusahaan["PT Garuda Cargo Nusantara"],
                "keperluan": "Draft pengajuan karyawan baru",
            },
        )
        p3.nomor_pengajuan = p3.nomor_pengajuan or p3._generate_nomor()
        p3.save()

        # ---------- Jadwal screening + booking ----------
        jadwal, _ = ScreeningSchedule.objects.get_or_create(
            tanggal=now.date() + timedelta(days=3),
            defaults={
                "jam_mulai": "08:00",
                "jam_selesai": "10:00",
                "lokasi": "Gedung Screening - Gate 1",
                "kuota": 20,
                "status": "OPEN",
            },
        )
        if not ScreeningBooking.objects.filter(pengajuan=p1).exists():
            booking = ScreeningBooking.objects.create(pengajuan=p1, jadwal=jadwal)
            booking.nomor_booking = booking._generate_nomor()
            booking.save(update_fields=["nomor_booking"])
            self.stdout.write(f"  booking {booking.nomor_booking} di jadwal {jadwal}")

        # ---------- Invoice: 1 PAID + 1 UNPAID ----------
        inv_paid, created = Invoice.objects.get_or_create(pengajuan=p1)
        if created:
            inv_paid.subtotal = jenis_tahunan.biaya
            inv_paid.biaya_admin = 2500
            inv_paid.discount = 0
            inv_paid.tax = 0
            inv_paid.hitung_total()
            inv_paid.status = Invoice.Status.PAID
            inv_paid.nomor_invoice = inv_paid._generate_nomor()
            inv_paid.save()
        method = PaymentMethod.objects.get(code="QRIS")
        PaymentTransaction.objects.get_or_create(
            invoice=inv_paid,
            payment_method=method,
            defaults={
                "amount": inv_paid.total,
                "status": PaymentTransaction.Status.PAID,
                "merchant_reference": f"{inv_paid.nomor_invoice}-DEMO",
                "paid_at": now,
            },
        )
        inv_unpaid, _ = Invoice.objects.get_or_create(pengajuan=p2)
        inv_unpaid.subtotal = jenis_bulanan.biaya
        inv_unpaid.biaya_admin = 0
        inv_unpaid.hitung_total()
        inv_unpaid.status = Invoice.Status.UNPAID
        inv_unpaid.nomor_invoice = inv_unpaid.nomor_invoice or inv_unpaid._generate_nomor()
        inv_unpaid.save()

        # ---------- Ringkasan ----------
        self.stdout.write(self.style.SUCCESS("\n=== DATA DEMO SIAP ==="))
        creds = [
            ("admin (Superadmin)", "admin / admin123"),
            ("pemohon1 (Pemohon)", "pemohon1 / pemohon123"),
            *[(uname.split("1")[0].replace("_", " ").title() + f" ({info[0]})", f"{uname} / {info[1]}") for uname, info in users.items() if uname != "pemohon1"],
        ]
        for label, cre in creds:
            self.stdout.write(f"  {label:<35} {cre}")
        self.stdout.write(self.style.SUCCESS("\nLink:"))
        self.stdout.write("  Daftar pemohon : http://127.0.0.1:8000/register/")
        self.stdout.write("  Login          : http://127.0.0.1:8000/login/")
        self.stdout.write("  Admin          : http://127.0.0.1:8000/admin/")
