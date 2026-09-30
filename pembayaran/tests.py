import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from pas.models import Layanan, Pengajuan

from .models import Invoice, PaymentMethod, PaymentTransaction, PembayaranManual
from .views import get_or_create_invoice


class JenisPembayaranTests(TestCase):
    def setUp(self):
        self.komersil = User.objects.create_user(
            username="komersil1", password="x12345", role=User.Role.KOMERSIL
        )
        self.operasi = User.objects.create_user(
            username="operasi1", password="x12345", role=User.Role.OPERASI
        )
        self.qris = PaymentMethod.objects.create(
            code="QRIS", name="QRIS", type="QRIS"
        )
        self.va = PaymentMethod.objects.create(
            code="BCA_VA", name="BCA Virtual Account",
            type="VIRTUAL_ACCOUNT",
        )
        self.list_url = reverse("pembayaran:jenis_list")

    def test_komersil_menambah_jenis_pembayaran(self):
        self.client.force_login(self.komersil)
        resp = self.client.post(
            reverse("pembayaran:jenis_buat"),
            {
                "code": "DANA2",
                "name": "DANA",
                "type": "E_WALLET",
                "provider": "DANA",
                "sort_order": "9",
                "active": "on",
                "bank": "",
                "norek": "",
                "nama": "",
            },
        )
        self.assertEqual(resp.status_code, 302)
        obj = PaymentMethod.objects.get(code="DANA2")
        self.assertTrue(obj.active)
        self.assertEqual(obj.name, "DANA")

    def test_komersil_edit_dan_nonaktifkan(self):
        self.client.force_login(self.komersil)
        resp = self.client.post(
            reverse("pembayaran:jenis_edit", args=[self.va.pk]),
            {
                "code": "BCA_VA",
                "name": "BCA VA",
                "type": "VIRTUAL_ACCOUNT",
                "provider": "BCA",
                "sort_order": "2",
                "active": "on",
                "bank": "BCA",
                "norek": "1234567890",
                "nama": "PT Bandara",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.va.refresh_from_db()
        self.assertEqual(self.va.name, "BCA VA")
        self.assertEqual(self.va.configuration["norek"], "1234567890")

        resp = self.client.post(reverse("pembayaran:jenis_status", args=[self.va.pk]))
        self.assertEqual(resp.status_code, 302)
        self.va.refresh_from_db()
        self.assertFalse(self.va.active)

    def test_operasi_tidak_boleh_mengelola_jenis_pembayaran(self):
        self.client.force_login(self.operasi)
        resp = self.client.post(
            reverse("pembayaran:jenis_status", args=[self.qris.pk])
        )
        self.assertEqual(resp.status_code, 302)
        self.qris.refresh_from_db()
        self.assertTrue(self.qris.active)



class MetodeNonaktifDiHalamanBayarTests(TestCase):
    def setUp(self):
        self.pemohon = User.objects.create_user(
            username="pemohon1", password="x12345", role=User.Role.PEMOHON
        )
        self.layanan = Layanan.objects.create(
            kode_layanan="T1",
            nama_layanan="Layanan Tes",
            lokasi=Layanan.Lokasi.ARRIVAL,
            jenis_tarif=Layanan.JenisTarif.FIXED,
            harga=100000,
            maksimal_pendamping=5,
        )
        self.pengajuan = Pengajuan.objects.create(
            layanan=self.layanan,
            pemohon=self.pemohon,
            status=Pengajuan.Status.MENUNGGU_PEMBAYARAN,
            tanggal_pelaksanaan="2026-10-05",
            jumlah_tamu=1,
            jumlah_pendamping=1,
            pemohon_nama="Budi",
            pic_nama="Budi",
            pic_no_hp="0811",
        )
        self.pengajuan.simpan_snapshot_tarif()
        self.pengajuan.save()
        self.invoice = get_or_create_invoice(self.pengajuan)
        self.aktif = PaymentMethod.objects.create(
            code="QRIS", name="QRIS", type="QRIS"
        )
        self.nonaktif = PaymentMethod.objects.create(
            code="TUNAI", name="Tunai",
            type="CASH", active=False,
        )
        self.url = reverse("pembayaran:bayar", args=[self.invoice.pk])

    def test_jenis_nonaktif_dinonaktifkan_di_menu_pemohon(self):
        self.client.force_login(self.pemohon)
        resp = self.client.get(self.url)
        self.assertContains(resp, "Tunai")
        self.assertContains(resp, "disabled")
        self.assertContains(resp, "Tidak tersedia")

    def test_jenis_yang_sudah_dipakai_transaksi_tidak_bisa_dihapus(self):
        PaymentTransaction.objects.create(
            invoice=self.invoice,
            payment_method=self.aktif,
            provider="QRIS",
            amount=self.invoice.total,
        )
        self.client.force_login(User.objects.create_user(
            username="komersil1", password="x12345", role=User.Role.KOMERSIL
        ))
        resp = self.client.post(reverse("pembayaran:jenis_hapus", args=[self.aktif.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(PaymentMethod.objects.filter(pk=self.aktif.pk).exists())

    def test_jenis_belum_dipakai_bisa_dihapus(self):
        self.client.force_login(User.objects.create_user(
            username="komersil1", password="x12345", role=User.Role.KOMERSIL
        ))
        resp = self.client.post(reverse("pembayaran:jenis_hapus", args=[self.nonaktif.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(PaymentMethod.objects.filter(pk=self.nonaktif.pk).exists())

    def test_jenis_nonaktif_tidak_bisa_dipakai(self):
        self.client.force_login(self.pemohon)
        resp = self.client.post(
            reverse("pembayaran:buat_transaksi", args=[self.invoice.pk]),
            {"method": self.nonaktif.pk},
        )
        self.assertEqual(resp.status_code, 404)


class AlurBuatTransaksiKeUploadTests(TestCase):
    """Buat Transaksi harus mendaratkan pemohon di menu Upload Bukti,
    termasuk saat tab ditutup dan ia kembali lagi."""

    def setUp(self):
        self.pemohon = User.objects.create_user(
            username="pemohon1", password="x12345", role=User.Role.PEMOHON
        )
        self.layanan = Layanan.objects.create(
            kode_layanan="T2",
            nama_layanan="Layanan Tes 2",
            lokasi=Layanan.Lokasi.ARRIVAL,
            jenis_tarif=Layanan.JenisTarif.FIXED,
            harga=100000,
            maksimal_pendamping=5,
        )
        self.pengajuan = Pengajuan.objects.create(
            layanan=self.layanan,
            pemohon=self.pemohon,
            status=Pengajuan.Status.MENUNGGU_PEMBAYARAN,
            tanggal_pelaksanaan="2026-10-05",
            jumlah_tamu=1,
            jumlah_pendamping=1,
            pemohon_nama="Budi",
            pic_nama="Budi",
            pic_no_hp="0811",
        )
        self.pengajuan.simpan_snapshot_tarif()
        self.pengajuan.save()
        self.invoice = get_or_create_invoice(self.pengajuan)
        self.qris = PaymentMethod.objects.create(
            code="QRIS", name="QRIS", type="QRIS"
        )
        self.manual = PaymentMethod.objects.create(
            code="TRANSFER", name="Transfer Manual", type="MANUAL_TRANSFER",
            configuration={"bank": "BCA", "norek": "123", "nama": "PT X"},
        )
        self.bayar_url = reverse("pembayaran:bayar", args=[self.invoice.pk])
        self.client.force_login(self.pemohon)

    def test_buat_transaksi_semua_jenis_langsung_ke_upload_bukti(self):
        for metode in (self.qris, self.manual):
            with self.subTest(metode=metode.code):
                resp = self.client.post(
                    reverse("pembayaran:buat_transaksi", args=[self.invoice.pk]),
                    {"method": metode.pk},
                )
                self.assertEqual(resp.status_code, 302)
                transaksi = PaymentTransaction.objects.filter(
                    invoice=self.invoice
                ).order_by("-created_at").first()
                self.assertEqual(
                    resp.url,
                    reverse("pembayaran:upload_bukti", args=[transaksi.pk]),
                )
                # tab ditutup -> kembali ke halaman bayar -> diarahkan ke upload
                resp = self.client.get(self.bayar_url)
                self.assertEqual(
                    resp.status_code, 302
                )
                self.assertEqual(
                    resp.url,
                    reverse("pembayaran:upload_bukti", args=[transaksi.pk]),
                )

    def test_pilih_metode_lain_tetap_masuk_halaman_bayar(self):
        self.client.post(
            reverse("pembayaran:buat_transaksi", args=[self.invoice.pk]),
            {"method": self.qris.pk},
        )
        resp = self.client.get(self.bayar_url + "?pilih_lain=1")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Pilih Metode Pembayaran")

    def test_invoice_saya_menampilkan_tombol_upload_bukti(self):
        self.client.post(
            reverse("pembayaran:buat_transaksi", args=[self.invoice.pk]),
            {"method": self.qris.pk},
        )
        transaksi = PaymentTransaction.objects.filter(
            invoice=self.invoice
        ).order_by("-created_at").first()
        resp = self.client.get(reverse("pembayaran:invoice_saya"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, reverse("pembayaran:upload_bukti", args=[transaksi.pk]))
        self.assertContains(resp, "Upload Bukti")

    def test_setelah_bukti_diunggah_tidak_dipaksa_ke_upload(self):
        transaksi = PaymentTransaction.objects.create(
            invoice=self.invoice,
            payment_method=self.manual,
            provider="manual",
            amount=self.invoice.total,
            status=PaymentTransaction.Status.PENDING,
        )
        with self.settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="pas-test-bukti-")):
            self.client.post(
                reverse("pembayaran:upload_bukti", args=[transaksi.pk]),
                {"bukti": SimpleUploadedFile("bukti.jpg", b"\xff\xd8\xff", content_type="image/jpeg")},
            )
        self.invoice.refresh_from_db()
        self.assertIsNone(self.invoice.transaksi_menunggu_bukti)
        # tidak dipaksa ke upload, dan tidak disuruh membuat transaksi kedua
        resp = self.client.get(self.bayar_url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url, reverse("pembayaran:detail_transaksi", args=[transaksi.pk])
        )


class CariBuktiDariHalamanMukaTests(TestCase):
    """Pemohon membuka lagi situs di tab baru (tanpa tahu URL) tetap bisa
    sampai ke halaman pembayaran / upload bukti."""

    def setUp(self):
        self.pemohon = User.objects.create_user(
            username="pemohon1", password="x12345", role=User.Role.PEMOHON
        )
        self.layanan = Layanan.objects.create(
            kode_layanan="T3",
            nama_layanan="Layanan Tes 3",
            lokasi=Layanan.Lokasi.ARRIVAL,
            jenis_tarif=Layanan.JenisTarif.FIXED,
            harga=50000,
            maksimal_pendamping=5,
        )
        self.pengajuan = Pengajuan.objects.create(
            layanan=self.layanan,
            pemohon=self.pemohon,
            status=Pengajuan.Status.MENUNGGU_PEMBAYARAN,
            tanggal_pelaksanaan="2026-10-06",
            jumlah_tamu=1,
            jumlah_pendamping=1,
            pemohon_nama="Budi",
            pic_nama="Budi",
            pic_no_hp="0811",
        )
        self.pengajuan.simpan_snapshot_tarif()
        self.pengajuan.save()
        self.invoice = get_or_create_invoice(self.pengajuan)
        self.manual = PaymentMethod.objects.create(
            code="TRANSFER", name="Transfer Manual", type="MANUAL_TRANSFER",
        )
        self.url = reverse("pembayaran:cari_bukti")

    def test_form_upload_bukti_tampil_di_halaman_muka(self):
        resp = self.client.get(reverse("accounts:home"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.url)
        self.assertContains(resp, "Upload Bukti Bayar")

    def test_kontak_salah_ditolak(self):
        resp = self.client.post(
            self.url,
            {"nomor_pengajuan": self.pengajuan.nomor_pengajuan, "kontak": "salah"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "tidak cocok")
        self.assertNotIn(self.pengajuan.pk, self.client.session.get("lacak_pengajuan", []))

    def test_sudah_buat_transaksi_langsung_ke_upload_bukti(self):
        transaksi = PaymentTransaction.objects.create(
            invoice=self.invoice,
            payment_method=self.manual,
            provider="manual",
            amount=self.invoice.total,
            status=PaymentTransaction.Status.PENDING,
        )
        resp = self.client.post(
            self.url,
            {
                "nomor_pengajuan": self.pengajuan.nomor_pengajuan,
                "kontak": self.pemohon.username,
            },
        )
        self.assertEqual(
            resp.status_code, 302
        )
        self.assertEqual(
            resp.url, reverse("pembayaran:upload_bukti", args=[transaksi.pk])
        )

    def test_belum_buat_transaksi_diarahkan_ke_halaman_bayar(self):
        resp = self.client.post(
            self.url,
            {
                "nomor_pengajuan": self.pengajuan.nomor_pengajuan,
                "kontak": self.pemohon.username,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url, reverse("pembayaran:bayar", args=[self.invoice.pk])
        )

    def test_lacak_detail_menampilkan_tombol_upload_bukti(self):
        transaksi = PaymentTransaction.objects.create(
            invoice=self.invoice,
            payment_method=self.manual,
            provider="manual",
            amount=self.invoice.total,
            status=PaymentTransaction.Status.PENDING,
        )
        session = self.client.session
        session["lacak_pengajuan"] = [self.pengajuan.pk]
        session.save()
        resp = self.client.get(
            reverse("pas:lacak_detail", args=[self.pengajuan.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Upload Bukti Bayar")
        self.assertContains(resp, reverse("pembayaran:upload_bukti", args=[transaksi.pk]))


class StatusBuktiDanDashboardTests(TestCase):
    """Status pengajuan dan dashboard pembayaran harus jelas:
    siapa yang mengunggah, sampai di tahap mana, dan mana yang perlu diverifikasi."""

    def setUp(self):
        self.pemohon = User.objects.create_user(
            username="pemohon1", password="x12345", role=User.Role.PEMOHON,
            first_name="Budi", last_name="Santoso", instansi="PT Maju",
        )
        self.komersil = User.objects.create_user(
            username="komersil1", password="x12345", role=User.Role.KOMERSIL
        )
        self.layanan = Layanan.objects.create(
            kode_layanan="T4",
            nama_layanan="Layanan Tes 4",
            lokasi=Layanan.Lokasi.ARRIVAL,
            jenis_tarif=Layanan.JenisTarif.FIXED,
            harga=75000,
            maksimal_pendamping=5,
        )
        self.pengajuan = Pengajuan.objects.create(
            layanan=self.layanan,
            pemohon=self.pemohon,
            status=Pengajuan.Status.MENUNGGU_PEMBAYARAN,
            tanggal_pelaksanaan="2026-10-07",
            jumlah_tamu=1,
            jumlah_pendamping=1,
            pemohon_nama="Budi Santoso",
            pemohon_no_hp="081234567890",
            pemohon_email="budi@email.com",
            pic_nama="Budi",
            pic_no_hp="0811",
        )
        self.pengajuan.simpan_snapshot_tarif()
        self.pengajuan.nomor_pengajuan = self.pengajuan._generate_nomor()
        self.pengajuan.save()
        self.invoice = get_or_create_invoice(self.pengajuan)
        self.manual = PaymentMethod.objects.create(
            code="TRANSFER", name="Transfer Manual", type="MANUAL_TRANSFER",
        )

    def _buat_transaksi(self, dengan_bukti=True):
        transaksi = PaymentTransaction.objects.create(
            invoice=self.invoice,
            payment_method=self.manual,
            provider="manual",
            amount=self.invoice.total,
            status=PaymentTransaction.Status.PENDING,
        )
        if dengan_bukti:
            with self.settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="pas-test-bukti-")):
                PembayaranManual.objects.create(
                    transaksi=transaksi,
                    bukti=SimpleUploadedFile(
                        "bukti.jpg", b"\xff\xd8\xff", content_type="image/jpeg"
                    ),
                    catatan="sudah transfer",
                )
        return transaksi

    def test_detail_pengajuan_menunggu_verifikasi_bayar(self):
        self._buat_transaksi()
        self.client.force_login(self.pemohon)
        resp = self.client.get(
            reverse("pas:detail_pengajuan", args=[self.pengajuan.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bukti Bayar Sudah Diunggah")
        self.assertContains(resp, "menunggu verifikasi petugas Komersil")
        self.assertNotContains(resp, "Menunggu Pembayaran")

    def test_detail_pengajuan_belum_upload_tetap_menunggu_pembayaran(self):
        self._buat_transaksi(dengan_bukti=False)
        self.client.force_login(self.pemohon)
        resp = self.client.get(
            reverse("pas:detail_pengajuan", args=[self.pengajuan.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Menunggu Pembayaran")
        self.assertNotContains(resp, "Menunggu Verifikasi Bayar")

    def test_dashboard_pembayaran_menampilkan_identitas_pemohon(self):
        transaksi = self._buat_transaksi()
        self.client.force_login(self.komersil)
        resp = self.client.get(reverse("pembayaran:dashboard_pembayaran"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.pengajuan.nomor_pengajuan)
        self.assertContains(resp, "Budi Santoso")
        self.assertContains(resp, "PT Maju")
        self.assertContains(resp, "Lihat Bukti")
        self.assertContains(resp, "Verifikasi Bukti")
        self.assertContains(
            resp, reverse("pembayaran:verifikasi_manual", args=[transaksi.pk])
        )

    def test_dashboard_pembayaran_menandai_yang_belum_upload(self):
        self._buat_transaksi(dengan_bukti=False)
        self.client.force_login(self.komersil)
        resp = self.client.get(reverse("pembayaran:dashboard_pembayaran"))
        self.assertContains(resp, "Belum unggah bukti")
        self.assertContains(resp, "Menunggu verifikasi bukti")

    def test_halaman_verifikasi_menampilkan_detail_pengajuan(self):
        transaksi = self._buat_transaksi()
        self.client.force_login(self.komersil)
        resp = self.client.get(
            reverse("pembayaran:verifikasi_manual", args=[transaksi.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.pengajuan.nomor_pengajuan)
        self.assertContains(resp, "Budi Santoso")
        self.assertContains(resp, "081234567890")
        self.assertContains(resp, reverse("pas:detail_pengajuan", args=[self.pengajuan.pk]))

    def test_bayar_setelah_bukti_terunggah_mengarahkan_ke_detail(self):
        transaksi = self._buat_transaksi()
        self.client.force_login(self.pemohon)
        resp = self.client.get(reverse("pembayaran:bayar", args=[self.invoice.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url, reverse("pembayaran:detail_transaksi", args=[transaksi.pk])
        )

    def test_detail_transaksi_menyatakan_menunggu_verifikasi(self):
        self._buat_transaksi()
        self.client.force_login(self.pemohon)
        transaksi = PaymentTransaction.objects.get(invoice=self.invoice)
        resp = self.client.get(
            reverse("pembayaran:detail_transaksi", args=[transaksi.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "menunggu verifikasi petugas Komersil")

    def test_cari_bukti_setelah_terunggah_mengarahkan_ke_detail(self):
        transaksi = self._buat_transaksi()
        resp = self.client.post(
            reverse("pembayaran:cari_bukti"),
            {
                "nomor_pengajuan": self.pengajuan.nomor_pengajuan,
                "kontak": self.pemohon.username,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url, reverse("pembayaran:detail_transaksi", args=[transaksi.pk])
        )


class StatusBuktiTerunggahTests(TestCase):
    """Unggah bukti harus mengubah status pengajuan menjadi
    "Bukti Bayar Sudah Diunggah" di semua daftar."""

    def setUp(self):
        self.pemohon = User.objects.create_user(
            username="pemohon1", password="x12345", role=User.Role.PEMOHON
        )
        self.komersil = User.objects.create_user(
            username="komersil1", password="x12345", role=User.Role.KOMERSIL
        )
        self.layanan = Layanan.objects.create(
            kode_layanan="T5",
            nama_layanan="Layanan Tes 5",
            lokasi=Layanan.Lokasi.ARRIVAL,
            jenis_tarif=Layanan.JenisTarif.FIXED,
            harga=90000,
            maksimal_pendamping=5,
        )
        self.pengajuan = Pengajuan.objects.create(
            layanan=self.layanan,
            pemohon=self.pemohon,
            status=Pengajuan.Status.MENUNGGU_PEMBAYARAN,
            tanggal_pelaksanaan="2026-10-08",
            jumlah_tamu=1,
            jumlah_pendamping=1,
            pemohon_nama="Budi",
            pic_nama="Budi",
            pic_no_hp="0811",
        )
        self.pengajuan.simpan_snapshot_tarif()
        self.pengajuan.nomor_pengajuan = self.pengajuan._generate_nomor()
        self.pengajuan.save()
        self.invoice = get_or_create_invoice(self.pengajuan)
        self.manual = PaymentMethod.objects.create(
            code="TRANSFER", name="Transfer Manual", type="MANUAL_TRANSFER",
        )
        self.transaksi = PaymentTransaction.objects.create(
            invoice=self.invoice,
            payment_method=self.manual,
            provider="manual",
            amount=self.invoice.total,
            status=PaymentTransaction.Status.PENDING,
        )
        self.upload_url = reverse(
            "pembayaran:upload_bukti", args=[self.transaksi.pk]
        )
        self.client.force_login(self.pemohon)

    def _unggah(self):
        with self.settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="pas-test-bukti-")):
            return self.client.post(
                self.upload_url,
                {"bukti": SimpleUploadedFile("bukti.jpg", b"\xff\xd8\xff", content_type="image/jpeg")},
            )

    def test_status_pengajuan_berubah_setelah_bukti_diunggah(self):
        self._unggah()
        self.pengajuan.refresh_from_db()
        self.assertEqual(self.pengajuan.status, Pengajuan.Status.BUKTI_TERUNGGAH)
        self.assertEqual(self.pengajuan.riwayat_status.last().status, "BUKTI_TERUNGGAH")

    def test_status_baru_tampil_di_daftar_pengajuan(self):
        self._unggah()
        self.client.force_login(self.pemohon)
        resp = self.client.get(reverse("pas:daftar_pengajuan"))
        self.assertContains(resp, "Bukti Bayar Sudah Diunggah")

    def test_status_baru_tampil_di_detail_dan_lacak(self):
        self._unggah()
        resp = self.client.get(
            reverse("pas:detail_pengajuan", args=[self.pengajuan.pk])
        )
        self.assertContains(resp, "Bukti Bayar Sudah Diunggah")
        session = self.client.session
        session["lacak_pengajuan"] = [self.pengajuan.pk]
        session.save()
        resp = self.client.get(reverse("pas:lacak_detail", args=[self.pengajuan.pk]))
        self.assertContains(resp, "Bukti Bayar Sudah Diunggah")

    def test_status_baru_masuk_hitungan_dashboard(self):
        self._unggah()
        self.client.force_login(self.komersil)
        resp = self.client.get(reverse("dashboard:home"))
        # kartu Komersil "Payment Proof Pending" dihitung dari transaksi
        self.assertEqual(resp.context["menunggu_verifikasi_bayar"], 1)
        self.client.force_login(self.pemohon)
        resp = self.client.get(reverse("dashboard:home"))
        self.assertEqual(resp.context["bukti_terunggah"], 1)
        self.assertEqual(resp.context["menunggu_pembayaran"], 0)

    def test_verifikasi_tidak_valid_mengembalikan_status(self):
        self._unggah()
        self.client.force_login(self.komersil)
        self.client.post(
            reverse("pembayaran:verifikasi_manual", args=[self.transaksi.pk]),
            {"keputusan": "INVALID"},
        )
        self.pengajuan.refresh_from_db()
        self.assertEqual(self.pengajuan.status, Pengajuan.Status.MENUNGGU_PEMBAYARAN)

    def test_verifikasi_valid_menjadi_sudah_dibayar(self):
        self._unggah()
        self.client.force_login(self.komersil)
        self.client.post(
            reverse("pembayaran:verifikasi_manual", args=[self.transaksi.pk]),
            {"keputusan": "VALID"},
        )
        self.pengajuan.refresh_from_db()
        self.assertEqual(self.pengajuan.status, Pengajuan.Status.DIBAYAR)

    def test_menu_bayar_masih_bisa_dibuka_setelah_status_baru(self):
        self._unggah()
        self.client.force_login(self.pemohon)
        resp = self.client.get(reverse("pembayaran:bayar", args=[self.invoice.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url,
            reverse("pembayaran:detail_transaksi", args=[self.transaksi.pk]),
        )
        resp = self.client.get(
            reverse("pembayaran:buat_invoice", args=[self.pengajuan.pk])
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url, reverse("pembayaran:bayar", args=[self.invoice.pk])
        )
