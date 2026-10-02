import base64
import io
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from pas.models import DaftarHitam, DokumenPendamping, Layanan, Pengajuan, SerahTerimaPAS
from pembayaran.models import Invoice


_MEDIA_SEMENTARA = tempfile.mkdtemp(prefix="pas-test-media-")


def _png_bytes():
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buf, format="PNG")
    return buf.getvalue()


def _fokus_field(html):
    """Ambil daftar kolom yang disorot dari blok json_script fokus-field."""
    import json
    import re

    m = re.search(r'id="fokus-field" type="application/json">([^<]*)</script>', html)
    return json.loads(m.group(1)) if m else []


def _form_payload(layanan, **extra):
    data = {
        "layanan": str(layanan.pk),
        "tanggal_pelaksanaan": "2026-10-05",
        "waktu_kedatangan": "09:00",
        "nomor_penerbangan": "GA100",
        "asal_penerbangan": "CGK",
        "jumlah_tamu": "1",
        "jumlah_pendamping": "1",
        "keterangan": "",
        "pic_nama": "Andi PIC",
        "pic_jabatan": "Manajer",
        "pic_nomor_identitas": "3175000000000099",
        "pic_no_hp": "08111111111",
        "pic_email": "andi@example.com",
        "pendamping_nama_1": "Rina Pendamping",
        "pendamping_nik_1": "3175000000000088",
    }
    data.update(extra)
    return data


@override_settings(MEDIA_ROOT=_MEDIA_SEMENTARA)
class PengajuanBaruTests(TestCase):
    def setUp(self):
        self.layanan = Layanan.objects.create(
            kode_layanan="TEST",
            nama_layanan="Greet Test",
            lokasi=Layanan.Lokasi.ARRIVAL,
            jenis_tarif=Layanan.JenisTarif.FIXED,
            harga=1000000,
            maksimal_pendamping=5,
        )
        self.url = reverse("pas:buat_pengajuan")

    def _setuju_batasan(self):
        resp = self.client.post(self.url, {"aksi": "paham-batasan"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("?langkah=form", resp["Location"])

    def test_pemberitahuan_batasan_area_muncul_sebelum_form(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "pas/batasan_area.html")
        self.assertContains(resp, "Batasan Area PAS Visitor")
        self.assertContains(resp, "Departure")
        self.assertContains(resp, "Arrival")

    def test_form_muncul_setelah_paham_batasan(self):
        self._setuju_batasan()
        resp = self.client.get(self.url + "?langkah=form")
        self.assertTemplateUsed(resp, "pas/buat_pengajuan.html")
        self.assertContains(resp, "PIC Penanggung Jawab Langsung")
        self.assertContains(resp, "layanan-option")
        self.assertNotContains(resp, "Tujuan/Instansi")

    def test_layanan_ditampilkan_dengan_harga(self):
        self._setuju_batasan()
        resp = self.client.get(self.url + "?langkah=form")
        self.assertContains(resp, "Rp 1.000.000")

    def test_batasan_area_selalu_muncul_tiap_kunjungan_baru(self):
        resp = self.client.get(self.url)
        self.assertTemplateUsed(resp, "pas/batasan_area.html")
        self._setuju_batasan()
        resp = self.client.get(self.url)
        self.assertTemplateUsed(resp, "pas/batasan_area.html")

    def test_submit_lolos_langsung_ke_pembayaran(self):
        self._setuju_batasan()
        payload = _form_payload(self.layanan)
        payload["pendamping_file_1"] = SimpleUploadedFile(
            "ktp.jpg", _png_bytes(), content_type="image/jpeg"
        )
        resp = self.client.post(self.url, payload, follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/pembayaran/", resp["Location"])

        pengajuan = Pengajuan.objects.get()
        self.assertEqual(pengajuan.status, Pengajuan.Status.MENUNGGU_PEMBAYARAN)
        self.assertEqual(pengajuan.pemohon_nama, "Andi PIC")
        self.assertTrue(Invoice.objects.filter(pengajuan=pengajuan).exists())
        pd = pengajuan.pendamping.get()
        self.assertEqual(pd.nik, "3175000000000088")
        self.assertEqual(pd.nama, "Rina Pendamping")

    def test_nik_blacklist_ditolak_dan_tidak_disimpan(self):
        DaftarHitam.objects.create(
            tipe=DaftarHitam.Tipe.ORANG,
            nik="3175000000000088",
            nama="Rina Pendamping",
            alasan="Blacklist avsec",
        )
        self._setuju_batasan()
        payload = _form_payload(self.layanan)
        payload["pendamping_file_1"] = SimpleUploadedFile(
            "ktp.jpg", _png_bytes(), content_type="image/jpeg"
        )
        resp = self.client.post(self.url, payload)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "terdaftar dalam daftar hitam")
        self.assertEqual(Pengajuan.objects.count(), 0)

    def test_data_form_tetap_ada_saat_nik_blacklist(self):
        DaftarHitam.objects.create(
            tipe=DaftarHitam.Tipe.ORANG,
            nik="3175000000000088",
            nama="Rina Pendamping",
            alasan="Blacklist avsec",
        )
        self._setuju_batasan()
        payload = _form_payload(self.layanan)
        payload["pendamping_file_1"] = SimpleUploadedFile(
            "ktp.jpg", _png_bytes(), content_type="image/jpeg"
        )
        resp = self.client.post(self.url, payload)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # Isian form tidak hilang — cukup NIK yang diperbaiki
        self.assertContains(resp, 'value="Andi PIC"')
        self.assertContains(resp, '"Rina Pendamping"')
        self.assertContains(resp, '"3175000000000088"')
        self.assertContains(resp, "ktp.jpg")
        self.assertContains(resp, "masih tersimpan")
        self.assertEqual(_fokus_field(html), ["pendamping_nik_1"])
        self.assertContains(resp, "NIK Pendamping 1")

        # Kirim ulang tanpa mengunggah berkas (browser tidak mengirim ulang)
        payload["pendamping_nik_1"] = "3175000000000099"
        payload.pop("pendamping_file_1")
        resp = self.client.post(self.url, payload)
        self.assertEqual(resp.status_code, 302)
        pengajuan = Pengajuan.objects.get()
        pd = pengajuan.pendamping.get()
        self.assertEqual(pd.nik, "3175000000000099")
        self.assertTrue(pd.file)

    def test_nik_pic_hitam_ditandai_kolom_pic(self):
        DaftarHitam.objects.create(
            tipe=DaftarHitam.Tipe.ORANG,
            nik="3175000000000099",
            nama="PIC Hitam",
            alasan="Blacklist avsec",
        )
        self._setuju_batasan()
        payload = _form_payload(self.layanan)
        resp = self.client.post(self.url, payload)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertContains(resp, "NIK PIC")
        self.assertEqual(_fokus_field(html), ["pic_nomor_identitas"])
        self.assertContains(resp, "ditandai merah")

    def test_nik_diperiksa_sebelum_berkas_lengkap(self):
        """NIK pendamping tetap dicek walau dokumennya belum diunggah."""
        DaftarHitam.objects.create(
            tipe=DaftarHitam.Tipe.ORANG,
            nik="3175000000000088",
            nama="Rina Pendamping",
            alasan="Blacklist avsec",
        )
        self._setuju_batasan()
        payload = _form_payload(self.layanan)  # tanpa unggahan dokumen
        resp = self.client.post(self.url, payload)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertContains(resp, "NIK Pendamping 1")
        self.assertEqual(_fokus_field(html), ["pendamping_nik_1"])

    def test_kesalahan_form_biasa_juga_ditandai_dan_difokuskan(self):
        self._setuju_batasan()
        payload = _form_payload(self.layanan)
        payload.pop("layanan")
        resp = self.client.post(self.url, payload)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertContains(resp, "Pengajuan tidak dapat dikirim")
        self.assertEqual(_fokus_field(html), ["layanan"])
        self.assertEqual(Pengajuan.objects.count(), 0)

    def test_nik_wajib_diisi(self):
        self._setuju_batasan()
        payload = _form_payload(self.layanan, pendamping_nik_1="")
        payload["pendamping_file_1"] = SimpleUploadedFile(
            "ktp.jpg", _png_bytes(), content_type="image/jpeg"
        )
        resp = self.client.post(self.url, payload)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "NIK / nomor identitas wajib diisi")
        self.assertEqual(Pengajuan.objects.count(), 0)


@override_settings(MEDIA_ROOT=_MEDIA_SEMENTARA)
class EditPengajuanTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pemohon9", password="x", role="PEMOHON"
        )
        self.client.force_login(self.user)
        self.layanan = Layanan.objects.create(
            kode_layanan="E1", nama_layanan="Layanan Edit", lokasi="ARRIVAL", harga=1000
        )
        self.pengajuan = Pengajuan.objects.create(
            layanan=self.layanan,
            status=Pengajuan.Status.DRAFT,
            pemohon=self.user,
            tanggal_pelaksanaan="2026-10-05",
            jumlah_pendamping=1,
            pemohon_nama="Andi",
            pic_nama="Andi",
            pic_no_hp="0811",
            pic_nomor_identitas="3175000000000099",
        )
        DokumenPendamping.objects.create(
            pengajuan=self.pengajuan,
            urutan=1,
            nama="Rina",
            nik="3175000000000088",
            file="pengajuan/pendamping/x.jpg",
        )

    def test_isian_edit_tetap_ada_saati_nik_blacklist(self):
        DaftarHitam.objects.create(
            tipe=DaftarHitam.Tipe.ORANG,
            nik="3175000000000088",
            nama="Rina",
            alasan="Blacklist avsec",
        )
        payload = _form_payload(self.layanan, pendamping_nama_1="Rina Baru")
        payload["pendamping_file_1"] = SimpleUploadedFile(
            "ktp.jpg", _png_bytes(), content_type="image/jpeg"
        )
        resp = self.client.post(
            reverse("pas:edit_pengajuan", args=[self.pengajuan.pk]), payload
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "terdaftar dalam daftar hitam")
        self.assertContains(resp, '"Rina Baru"')
        self.assertContains(resp, '"3175000000000088"')
        self.assertContains(resp, "ktp.jpg")
        self.pengajuan.refresh_from_db()
        self.assertEqual(self.pengajuan.status, Pengajuan.Status.DRAFT)


class KomersilLayananTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="kom1", password="x", role="KOMERSIL"
        )
        self.client.force_login(self.user)

    def test_list_layanan_hanya_komersil(self):
        resp = self.client.get(reverse("pas:layanan_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "pas/layanan_list.html")

    def test_buat_layanan(self):
        resp = self.client.post(
            reverse("pas:layanan_buat"),
            {
                "kode_layanan": "BARU1",
                "nama_layanan": "Layanan Baru",
                "lokasi": "DEPARTURE",
                "deskripsi": "",
                "minimal_pendamping": "1",
                "maksimal_pendamping": "5",
                "jenis_tarif": "FIXED",
                "harga": "1200000",
                "satuan": "Per pengajuan",
                "aktif": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        layanan = Layanan.objects.get(kode_layanan="BARU1")
        self.assertEqual(layanan.lokasi, "DEPARTURE")
        self.assertEqual(layanan.harga, 1200000)

    def test_edit_dan_hapus_layanan(self):
        layanan = Layanan.objects.create(
            kode_layanan="DEL", nama_layanan="Hapus Saya", harga=1000
        )
        resp = self.client.post(
            reverse("pas:layanan_edit", args=[layanan.pk]),
            {
                "kode_layanan": "DEL",
                "nama_layanan": "Sudah Diubah",
                "lokasi": "ARRIVAL",
                "deskripsi": "",
                "minimal_pendamping": "0",
                "maksimal_pendamping": "0",
                "jenis_tarif": "FIXED",
                "harga": "1500",
                "satuan": "",
                "aktif": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        layanan.refresh_from_db()
        self.assertEqual(layanan.nama_layanan, "Sudah Diubah")

        resp = self.client.post(reverse("pas:layanan_hapus", args=[layanan.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Layanan.objects.filter(pk=layanan.pk).exists())

    def test_verifikasi_list_menampilkan_antrian_bayar(self):
        resp = self.client.get(reverse("pas:verifikasi_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "pas/verifikasi_list.html")


class OperasiDaftarHitamTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ops1", password="x", role="OPERASI"
        )
        self.client.force_login(self.user)

    def test_crud_daftar_hitam(self):
        resp = self.client.get(reverse("pas:hitam_list"))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(
            reverse("pas:hitam_buat"),
            {
                "tipe": "ORANG",
                "nik": "3175.0000.0000.0123",
                "nama": "Seseorang",
                "alasan": "Uji coba",
                "aktif": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        entri = DaftarHitam.objects.get(nama="Seseorang")
        self.assertEqual(entri.nik, "3175000000000123")

        resp = self.client.post(reverse("pas:hitam_hapus", args=[entri.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(DaftarHitam.objects.filter(pk=entri.pk).exists())

    def test_terbitkan_pas_diblokir_jika_nik_hitam(self):
        layanan = Layanan.objects.create(
            kode_layanan="X1", nama_layanan="L", harga=1000, lokasi="ARRIVAL"
        )
        pengajuan = Pengajuan.objects.create(
            layanan=layanan,
            status=Pengajuan.Status.MENUNGGU_OPERASI,
            tanggal_pelaksanaan="2026-10-05",
            jumlah_pendamping=1,
            pemohon_nama="Andi",
            pemohon_no_hp="0811",
            pic_nama="Andi",
            pic_no_hp="0811",
        )
        DokumenPendamping.objects.create(
            pengajuan=pengajuan,
            urutan=1,
            nama="Rina",
            nik="3175000000000088",
            file="pengajuan/pendamping/x.jpg",
        )
        DaftarHitam.objects.create(
            tipe=DaftarHitam.Tipe.ORANG,
            nik="3175000000000088",
            nama="Rina",
            alasan="Dilarang",
        )

        resp = self.client.get(reverse("pas:operasi_proses", args=[pengajuan.pk]))
        self.assertContains(resp, "masuk daftar hitam")

        resp = self.client.post(reverse("pas:terbitkan_pas", args=[pengajuan.pk]))
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.status, Pengajuan.Status.DITOLAK_OPERASI)

    def test_terbitkan_pas_lolos_menetapkan_masa_berlaku(self):
        layanan = Layanan.objects.create(
            kode_layanan="X2", nama_layanan="L2", harga=1000, lokasi="ARRIVAL"
        )
        pengajuan = Pengajuan.objects.create(
            layanan=layanan,
            status=Pengajuan.Status.MENUNGGU_OPERASI,
            tanggal_pelaksanaan="2026-10-05",
            jumlah_pendamping=1,
            pemohon_nama="Andi",
            pic_nama="Andi",
            pic_no_hp="0811",
        )
        DokumenPendamping.objects.create(
            pengajuan=pengajuan,
            urutan=1,
            nama="Rina",
            nik="3175000000000088",
            file="pengajuan/pendamping/x.jpg",
        )
        self.client.post(reverse("pas:terbitkan_pas", args=[pengajuan.pk]))
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.status, Pengajuan.Status.PAS_TERBIT)
        self.assertIsNotNone(pengajuan.tanggal_berlaku_pas)
        self.assertIn(pengajuan.status_masa_berlaku, ("AKTIF", "TERJADWAL"))
        self.assertIsNotNone(pengajuan.masa_berlaku_habis)


class KomersilTeruskanOperasiTests(TestCase):
    def setUp(self):
        self.kom = User.objects.create_user(
            username="kom2", password="x", role="KOMERSIL"
        )
        self.ops = User.objects.create_user(
            username="ops2", password="x", role="OPERASI"
        )
        self.layanan = Layanan.objects.create(
            kode_layanan="Y1", nama_layanan="LY", harga=1000, lokasi="ARRIVAL"
        )
        self.pengajuan = Pengajuan.objects.create(
            layanan=self.layanan,
            status=Pengajuan.Status.DIBAYAR,
            tanggal_pelaksanaan="2026-10-05",
            jumlah_pendamping=1,
            pemohon_nama="Andi",
            pic_nama="Andi",
            pic_no_hp="0811",
            total=1000,
        )

    def _buat_invoice_lunas(self):
        from pembayaran.views import get_or_create_invoice

        invoice = get_or_create_invoice(self.pengajuan)
        invoice.status = Invoice.Status.PAID
        invoice.save(update_fields=["status", "updated_at"])
        return invoice

    def test_tidak_bisa_diteruskan_sebelum_lunas(self):
        self.client.force_login(self.kom)
        resp = self.client.post(
            reverse("pas:lanjutkan_operasi", args=[self.pengajuan.pk])
        )
        self.pengajuan.refresh_from_db()
        self.assertEqual(self.pengajuan.status, Pengajuan.Status.DIBAYAR)

    def test_diteruskan_ke_operasi_setelah_lunas(self):
        self._buat_invoice_lunas()
        self.client.force_login(self.kom)
        resp = self.client.post(
            reverse("pas:lanjutkan_operasi", args=[self.pengajuan.pk])
        )
        self.assertEqual(resp.status_code, 302)
        self.pengajuan.refresh_from_db()
        self.assertEqual(self.pengajuan.status, Pengajuan.Status.MENUNGGU_OPERASI)


@override_settings(MEDIA_ROOT=_MEDIA_SEMENTARA)
class AochProsesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="aoch1", password="x", role="AOCH"
        )
        self.client.force_login(self.user)
        self.layanan = Layanan.objects.create(
            kode_layanan="Z1", nama_layanan="LZ", harga=1000, lokasi="ARRIVAL"
        )
        self.pengajuan = Pengajuan.objects.create(
            layanan=self.layanan,
            status=Pengajuan.Status.PAS_TERBIT,
            tanggal_pelaksanaan="2026-10-05",
            jumlah_pendamping=1,
            pemohon_nama="Andi",
            pic_nama="Andi",
            pic_no_hp="0811",
            pic_nomor_identitas="3175000000000099",
            tanggal_berlaku_pas="2026-10-05",
        )
        self.pd = DokumenPendamping.objects.create(
            pengajuan=self.pengajuan,
            urutan=1,
            nama="Rina",
            nik="3175000000000088",
            file="pengajuan/pendamping/x.jpg",
        )

    def test_simpan_nomor_pas(self):
        self.client.post(
            reverse("pas:aoch_proses", args=[self.pengajuan.pk]),
            {"aksi": "simpan_nomor", f"nomor_pas_{self.pd.pk}": "PAS-001"},
        )
        self.pd.refresh_from_db()
        self.assertEqual(self.pd.nomor_pas, "PAS-001")

    def test_aoch_tidak_bisa_catat_serah_terima(self):
        ttd = "data:image/png;base64," + base64.b64encode(_png_bytes()).decode()
        self.client.post(
            reverse("pas:aoch_proses", args=[self.pengajuan.pk]),
            {
                "aksi": "serahkan",
                "penerima_nama": "Andi PIC",
                "foto": SimpleUploadedFile("foto.jpg", _png_bytes()),
                "ttd_data": ttd,
            },
        )
        self.assertFalse(SerahTerimaPAS.objects.filter(pengajuan=self.pengajuan).exists())

    def test_avsec_tidak_bisa_akses_nomor_pas(self):
        avsec = User.objects.create_user(
            username="avsec-x", password="x", role="AVSEC"
        )
        self.client.force_login(avsec)
        self.client.post(
            reverse("pas:aoch_proses", args=[self.pengajuan.pk]),
            {"aksi": "simpan_nomor", f"nomor_pas_{self.pd.pk}": "PAS-999"},
        )
        self.pd.refresh_from_db()
        self.assertEqual(self.pd.nomor_pas, "")


@override_settings(MEDIA_ROOT=_MEDIA_SEMENTARA)
class AvsecSerahTerimaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="avsec1", password="x", role="AVSEC"
        )
        self.client.force_login(self.user)
        self.layanan = Layanan.objects.create(
            kode_layanan="Z2", nama_layanan="LZ2", harga=1000, lokasi="DEPARTURE"
        )
        self.pengajuan = Pengajuan.objects.create(
            layanan=self.layanan,
            status=Pengajuan.Status.PAS_TERBIT,
            tanggal_pelaksanaan="2026-10-05",
            jumlah_pendamping=1,
            pemohon_nama="Andi",
            pic_nama="Andi",
            pic_no_hp="0811",
            pic_nomor_identitas="3175000000000099",
            tanggal_berlaku_pas="2026-10-05",
        )
        self.pd = DokumenPendamping.objects.create(
            pengajuan=self.pengajuan,
            urutan=1,
            nama="Rina",
            nik="3175000000000088",
            nomor_pas="PAS-001",
            file="pengajuan/pendamping/x.jpg",
        )

    def test_tidak_bisa_serahkan_sebelum_nomor_pas(self):
        self.pd.nomor_pas = ""
        self.pd.save(update_fields=["nomor_pas"])
        ttd = "data:image/png;base64," + base64.b64encode(_png_bytes()).decode()
        self.client.post(
            reverse("pas:avsec_serah_terima", args=[self.pengajuan.pk]),
            {
                "aksi": "serahkan",
                "penerima_nama": "Andi PIC",
                "foto": SimpleUploadedFile("foto.jpg", _png_bytes()),
                "ttd_data": ttd,
            },
        )
        serah = SerahTerimaPAS.objects.get(pengajuan=self.pengajuan)
        self.assertEqual(serah.status, SerahTerimaPAS.Status.BELUM)
        self.assertFalse(serah.foto_penyerahan)
        self.assertEqual(self.pengajuan.status, Pengajuan.Status.PAS_TERBIT)

    def test_serahkan_pas_dengan_foto_dan_ttd(self):
        ttd = "data:image/png;base64," + base64.b64encode(_png_bytes()).decode()
        self.client.post(
            reverse("pas:avsec_serah_terima", args=[self.pengajuan.pk]),
            {
                "aksi": "serahkan",
                "penerima_nama": "Andi PIC",
                "penerima_nik": "3175000000000099",
                "foto": SimpleUploadedFile("foto.jpg", _png_bytes()),
                "ttd_data": ttd,
                "catatan": "",
            },
        )
        self.pengajuan.refresh_from_db()
        serah = self.pengajuan.serah_terima
        self.assertEqual(serah.status, serah.Status.DITERIMA)
        self.assertIsNotNone(serah.tanggal_penyerahan)
        self.assertTrue(serah.foto_penyerahan)
        self.assertTrue(serah.ttd_elektronik)
        self.assertEqual(serah.petugas, self.user)
        self.assertEqual(self.pengajuan.status, Pengajuan.Status.DILAKSANAKAN)

    def test_pengembalian_dan_selesai(self):
        ttd = "data:image/png;base64," + base64.b64encode(_png_bytes()).decode()
        self.client.post(
            reverse("pas:avsec_serah_terima", args=[self.pengajuan.pk]),
            {
                "aksi": "serahkan",
                "penerima_nama": "Andi PIC",
                "foto": SimpleUploadedFile("foto.jpg", _png_bytes()),
                "ttd_data": ttd,
            },
        )
        self.client.post(
            reverse("pas:avsec_serah_terima", args=[self.pengajuan.pk]),
            {
                "aksi": "kembalikan",
                "foto": SimpleUploadedFile("foto-kembali.jpg", _png_bytes()),
                "ttd_data": ttd,
            },
        )
        self.pengajuan.refresh_from_db()
        self.assertEqual(
            self.pengajuan.serah_terima.status,
            self.pengajuan.serah_terima.Status.DIKEMBALIKAN,
        )
        self.assertIsNotNone(self.pengajuan.serah_terima.tanggal_pengembalian)
        self.assertTrue(self.pengajuan.serah_terima.foto_pengembalian)
        self.assertTrue(self.pengajuan.serah_terima.ttd_pengembalian)

        self.client.post(
            reverse("pas:avsec_serah_terima", args=[self.pengajuan.pk]),
            {"aksi": "selesai"},
        )
        self.pengajuan.refresh_from_db()
        self.assertEqual(self.pengajuan.status, Pengajuan.Status.SELESAI)

    def test_aoch_tidak_bisa_akses_halaman_avsec(self):
        aoch = User.objects.create_user(username="aoch-y", password="x", role="AOCH")
        self.client.force_login(aoch)
        resp = self.client.get(
            reverse("pas:avsec_serah_terima", args=[self.pengajuan.pk])
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(SerahTerimaPAS.objects.filter(pengajuan=self.pengajuan).exists())


class VerifikasiPasTests(TestCase):
    def setUp(self):
        self.layanan = Layanan.objects.create(
            kode_layanan="V1", nama_layanan="LV", harga=1000, lokasi="ARRIVAL"
        )

    def test_nomor_request_aktif(self):
        from django.utils import timezone

        pengajuan = Pengajuan.objects.create(
            layanan=self.layanan,
            nomor_pengajuan="REQ-20261001-0001",
            status=Pengajuan.Status.PAS_TERBIT,
            tanggal_pelaksanaan="2026-10-01",
            jumlah_pendamping=1,
            pemohon_nama="Andi",
            pic_nama="Andi",
        )
        pengajuan.tanggal_berlaku_pas = timezone.localdate()
        pengajuan.save(update_fields=["tanggal_berlaku_pas", "updated_at"])

        resp = self.client.post(
            reverse("pas:verifikasi_pas"), {"nomor": "REQ-20261001-0001"}
        )
        self.assertContains(resp, "AKTIF")

    def test_nomor_pas_dan_kedaluwarsa(self):
        from django.utils import timezone

        pengajuan = Pengajuan.objects.create(
            layanan=self.layanan,
            nomor_pengajuan="REQ-20261001-0002",
            status=Pengajuan.Status.PAS_TERBIT,
            tanggal_pelaksanaan="2026-10-01",
            jumlah_pendamping=1,
            pemohon_nama="Andi",
            pic_nama="Andi",
        )
        DokumenPendamping.objects.create(
            pengajuan=pengajuan,
            urutan=1,
            nama="Rina",
            nik="3175000000000088",
            nomor_pas="PAS-EXPIRED-1",
            file="pengajuan/pendamping/x.jpg",
        )
        from datetime import timedelta

        pengajuan.tanggal_berlaku_pas = timezone.localdate() - timedelta(days=3)
        pengajuan.save(update_fields=["tanggal_berlaku_pas", "updated_at"])

        resp = self.client.post(
            reverse("pas:verifikasi_pas"), {"nomor": "PAS-EXPIRED-1"}
        )
        self.assertContains(resp, "SUDAH KEDALUWARSA")

    def test_nomor_tidak_ditemukan(self):
        resp = self.client.post(reverse("pas:verifikasi_pas"), {"nomor": "TIDAK-ADA"})
        self.assertContains(resp, "tidak ditemukan")


@override_settings(MEDIA_ROOT=_MEDIA_SEMENTARA)
class AlurLengkapSampaiSelesaiTests(TestCase):
    """Tombol di tahap akhir harus benar-benar memajukan status:
    Komersil -> Operasi -> Terbitkan PAS -> AOCH nomor -> Avsec serah/kembali -> Selesai."""

    def setUp(self):
        self.kom = User.objects.create_user(username="kom3", password="x", role="KOMERSIL")
        self.ops = User.objects.create_user(username="ops3", password="x", role="OPERASI")
        self.aoch = User.objects.create_user(username="aoch3", password="x", role="AOCH")
        self.avsec = User.objects.create_user(username="avsec3", password="x", role="AVSEC")
        self.layanan = Layanan.objects.create(
            kode_layanan="W1", nama_layanan="LW", harga=1000, lokasi="ARRIVAL"
        )
        self.pengajuan = Pengajuan.objects.create(
            layanan=self.layanan,
            status=Pengajuan.Status.DIBAYAR,
            tanggal_pelaksanaan="2026-10-05",
            jumlah_pendamping=1,
            pemohon_nama="Andi",
            pic_nama="Andi",
            pic_no_hp="0811",
            pic_nomor_identitas="3175000000000077",
            total=1000,
        )
        self.pd = DokumenPendamping.objects.create(
            pengajuan=self.pengajuan,
            urutan=1,
            nama="Rina",
            nik="3175000000000066",
            file="pengajuan/pendamping/x.jpg",
        )

    def _invoice_lunas(self):
        from pembayaran.views import get_or_create_invoice

        invoice = get_or_create_invoice(self.pengajuan)
        invoice.status = Invoice.Status.PAID
        invoice.save(update_fields=["status", "updated_at"])

    def test_halaman_operasi_punya_tombol_terbitkan(self):
        """Regresi: pengajuan berstatus Sudah Dibayar harus tetap punya aksi."""
        self.client.force_login(self.ops)
        resp = self.client.get(reverse("pas:operasi_proses", args=[self.pengajuan.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Terbitkan PAS")

    def test_aoch_belum_bisa_simpan_nomor_sebelum_pas_terbit(self):
        self.client.force_login(self.aoch)
        self.client.post(
            reverse("pas:aoch_proses", args=[self.pengajuan.pk]),
            {"aksi": "simpan_nomor", f"nomor_pas_{self.pd.pk}": "PAS-001"},
        )
        self.pd.refresh_from_db()
        self.assertEqual(self.pd.nomor_pas, "")

    def test_alur_lengkap_sampai_selesai(self):
        # 1. Komersil meneruskan pengajuan yang sudah lunas
        self._invoice_lunas()
        self.client.force_login(self.kom)
        self.client.post(reverse("pas:lanjutkan_operasi", args=[self.pengajuan.pk]))
        self.pengajuan.refresh_from_db()
        self.assertEqual(self.pengajuan.status, Pengajuan.Status.MENUNGGU_OPERASI)

        # 2. Operasi: halaman punya tombol, ditekan -> PAS terbit
        self.client.force_login(self.ops)
        resp = self.client.get(reverse("pas:operasi_proses", args=[self.pengajuan.pk]))
        self.assertContains(resp, "Terbitkan PAS")
        self.client.post(reverse("pas:terbitkan_pas", args=[self.pengajuan.pk]))
        self.pengajuan.refresh_from_db()
        self.assertEqual(self.pengajuan.status, Pengajuan.Status.PAS_TERBIT)
        self.assertIsNotNone(self.pengajuan.tanggal_berlaku_pas)

        # 3. AOCH menginput nomor PAS
        self.client.force_login(self.aoch)
        self.client.post(
            reverse("pas:aoch_proses", args=[self.pengajuan.pk]),
            {"aksi": "simpan_nomor", f"nomor_pas_{self.pd.pk}": "PAS-001"},
        )
        self.pd.refresh_from_db()
        self.assertEqual(self.pd.nomor_pas, "PAS-001")

        # 4. Avsec mencatat penyerahan (foto + TTD)
        ttd = "data:image/png;base64," + base64.b64encode(_png_bytes()).decode()
        self.client.force_login(self.avsec)
        self.client.post(
            reverse("pas:avsec_serah_terima", args=[self.pengajuan.pk]),
            {
                "aksi": "serahkan",
                "penerima_nama": "Andi PIC",
                "foto": SimpleUploadedFile("foto.png", _png_bytes(), content_type="image/png"),
                "ttd_data": ttd,
            },
        )
        self.pengajuan.refresh_from_db()
        self.assertEqual(self.pengajuan.status, Pengajuan.Status.DILAKSANAKAN)
        serah = SerahTerimaPAS.objects.get(pengajuan=self.pengajuan)
        self.assertEqual(serah.status, SerahTerimaPAS.Status.DITERIMA)

        # 5. Pengembalian fisik
        self.client.post(
            reverse("pas:avsec_serah_terima", args=[self.pengajuan.pk]),
            {
                "aksi": "kembalikan",
                "foto": SimpleUploadedFile("foto-kembali.png", _png_bytes(), content_type="image/png"),
                "ttd_data": ttd,
            },
        )
        serah.refresh_from_db()
        self.assertEqual(serah.status, SerahTerimaPAS.Status.DIKEMBALIKAN)

        # 6. Selesai
        self.client.post(
            reverse("pas:avsec_serah_terima", args=[self.pengajuan.pk]),
            {"aksi": "selesai"},
        )
        self.pengajuan.refresh_from_db()
        self.assertEqual(self.pengajuan.status, Pengajuan.Status.SELESAI)
