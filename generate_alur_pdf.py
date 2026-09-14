#!/usr/bin/env python
"""Generate PDF alur lengkap aplikasi PAS Bandara: Pemohon -> PAS Terbit."""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)

BASE_URL = "http://127.0.0.1:8000"
OUTPUT = "/home/krisna/BANDARA/PAS/ALUR_PEMOHON_SAMPAI_PAS_TERBIT.pdf"

BLUE = colors.HexColor("#0d6efd")
GREEN = colors.HexColor("#198754")
GREY = colors.HexColor("#6c757d")

styles = getSampleStyleSheet()
title = ParagraphStyle("title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, spaceAfter=6)
subtitle = ParagraphStyle("subtitle", parent=styles["Normal"], fontSize=10, textColor=GREY, alignment=TA_CENTER, spaceAfter=12)
h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, spaceBefore=14, spaceAfter=6, textColor=BLUE)
h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, spaceBefore=8, spaceAfter=4)
body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, leading=14)
step = ParagraphStyle("step", parent=styles["Normal"], fontSize=9, leading=13)
note = ParagraphStyle("note", parent=styles["Normal"], fontSize=9, leading=12, textColor=GREY)


def li(txt):
    return Paragraph(txt, body, bulletText="\u2022")


def mk_table(header, rows, widths=None, header_bg=BLUE):
    data = [[Paragraph("<b>%s</b>" % c, step) for c in header]] + rows
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def status_badge(status, label):
    return Paragraph(f'<font color="#0d6efd"><b>{status}</b></font> &nbsp;{label}', step)


doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    leftMargin=1.8 * cm, rightMargin=1.8 * cm,
    title="Alur PAS Bandara: Pemohon sampai PAS Terbit",
)

story = []
story.append(Paragraph("Alur Aplikasi PAS Bandara", title))
story.append(Paragraph("Dari Pengajuan Pemohon &rarr; Verifikasi Komersil &rarr; Persetujuan Operasi &rarr; Pembayaran &rarr; PAS Terbit", subtitle))
story.append(Paragraph("<i>Dokumen ini memandu alur lengkap pengajuan layanan PAS (Passenger Assistance Service) bandara, dari pemohon mengajukan sampai PAS diterbitkan oleh Operasi.</i>", note))

# ----------------------------------------------------------------
story.append(Paragraph("Ringkasan Alur Utama", h1))
story.append(Paragraph("Status pengajuan berjalan berurutan sebagai berikut (lihat juga timeline di halaman detail pengajuan):", body))
story.append(Spacer(1, 4))

flow = [
    ["DRAFT", "Pemohon membuat draft pengajuan & upload dokumen pendamping"],
    ["DIAJUKAN", "Pemohon mengajukan; masuk antrian verifikasi Komersil"],
    ["VERIFIKASI_KOMERSIL", "Komersil memeriksa kelengkapan dokumen pendamping"],
    ["DISETUJUI_KOMERSIL", "Dokumen dinyatakan lengkap; diteruskan ke Operasi"],
    ["MENUNGGU_OPERASI", "Operasi meninjau & memutuskan setuju/tolak"],
    ["MENUNGGU_PEMBAYARAN", "Operasi setuju; invoice dibuat, pemohon membayar"],
    ["DIBAYAR", "Pembayaran diverifikasi lunas"],
    ["PAS_TERBIT", "PAS diterbitkan oleh Operasi (dapat diambil pemohon)"],
]
story.append(mk_table(
    ["Status", "Keterangan"],
    [[status_badge(s, ""), Paragraph(k, step)] for s, k in flow],
    widths=[6 * cm, 9 * cm],
))

story.append(Spacer(1, 6))
story.append(Paragraph("Catatan: ada cabang status selain alur utama:", note))
story.append(li("REVISI_PEMOHON &mdash; Komersil minta pemohon memperbaiki dokumen; kembali ke DIAJUKAN setelah direvisi."))
story.append(li("DITOLAK_OPERASI &mdash; Operasi menolak (misal terdaftar di daftar hitam); pengajuan berhenti."))
story.append(li("ACKNOWLEDGED_AOCH &mdash; AOCH mengakui pengajuan setelah dibayar, sebelum PAS diterbitkan (opsional)."))

story.append(Spacer(1, 6))
story.append(Paragraph("Aktor & Akun Demo", h2))
story.append(mk_table(
    ["Role", "Akun (username)", "Password", "Peran dalam alur"],
    [
        ["PEMOHON", "pemohon1", "pemohon123", "Registrasi, buat & ajukan pengajuan, bayar"],
        ["KOMERSIL", "komersil1", "demo123", "Verifikasi dokumen & verifikasi pembayaran"],
        ["OPERASI", "operasi1", "demo123", "Setujui/tolak pengajuan, terbitkan PAS"],
        ["AOCH", "aoch1", "demo123", "Mengakui (acknowledge) pengajuan setelah dibayar"],
        ["ADMINISTRATOR", "admin", "admin123", "Kelola master & akses penuh"],
    ],
    widths=[3.2 * cm, 3 * cm, 3 * cm, 5.8 * cm],
))
story.append(Spacer(1, 4))
story.append(Paragraph("Link: Login <b>%s/login/</b> &bull; Daftar <b>%s/register/</b> &bull; Admin <b>%s/admin/</b>" % (BASE_URL, BASE_URL, BASE_URL), body))

story.append(PageBreak())

# ================================================================
story.append(Paragraph("TAHAP 1 — Registrasi & Aktivasi Akun (Pemohon)", h1))
story.append(mk_table(
    ["#", "Klik / Aksi", "Hasil"],
    [
        ["1", "Buka <b>%s/register/</b>" % BASE_URL, "Form pendaftaran pemohon"],
        ["2", "Isi username, nama, email, no. HP, password", "Data akun baru"],
        ["3", "Klik <b>Daftar</b>", "Akun dibuat; status inaktif sampai email dikonfirmasi"],
        ["4", "Buka link konfirmasi di email", "Akun aktif (email_verified) & bisa login"],
        ["5", "Login di <b>%s/login/</b>" % BASE_URL, "Masuk ke dashboard pemohon"],
    ],
    widths=[1 * cm, 8 * cm, 6 * cm],
))

# ================================================================
story.append(Paragraph("TAHAP 2 — Buat & Ajukan Pengajuan (Pemohon)", h1))
story.append(mk_table(
    ["#", "Klik / Aksi", "Hasil"],
    [
        ["1", "Dashboard &rarr; menu <b>Pengajuan PAS</b>", "Daftar pengajuan milik pemohon"],
        ["2", "Klik <b>+ Buat Pengajuan</b>", "Form pengajuan baru"],
        ["3", "Pilih <b>Layanan</b>", "mis. Greet Service / Greet Group Service"],
        ["4", "Isi tanggal pelaksanaan, tujuan, jumlah tamu/pendamping, data PIC", "Detail pengajuan"],
        ["5", "Isi <b>nama + upload dokumen identitas tiap pendamping</b>", "Dokumen pendamping tersimpan"],
        ["6", "Klik <b>Simpan</b>", "Draft tersimpan + nomor <b>REQ-YYYYMMDD-xxxx</b>"],
        ["7", "Periksa, klik <b>Ajukan Pengajuan</b>", "Status &rarr; <b>DIAJUKAN</b>; notifikasi ke Komersil"],
    ],
    widths=[1 * cm, 8 * cm, 6 * cm],
))
story.append(Paragraph("Jika jumlah dokumen pendamping belum lengkap, sistem menahan pengajuan sampai dilengkapi.", note))

# ================================================================
story.append(Paragraph("TAHAP 3 — Verifikasi Dokumen (Komersil)", h1))
story.append(mk_table(
    ["#", "Klik / Aksi", "Hasil"],
    [
        ["1", "Login <b>komersil1</b> &rarr; menu <b>Verifikasi</b>", "Daftar pengajuan DIAJUKAN"],
        ["2", "Buka pengajuan (Detail)", "Lihat data + dokumen tiap pendamping"],
        ["3", "Tentukan status tiap dokumen (VALID / INVALID)", "Hasil verifikasi per pendamping"],
        ["4", "Klik <b>Setujui</b>", "Status &rarr; DISETUJUI_KOMERSIL lalu MENUNGGU_OPERASI"],
        ["5", "(opsional) Klik <b>Revisi</b> + catatan", "Status &rarr; REVISI_PEMOHON; pemohon memperbaiki & mengajukan ulang"],
    ],
    widths=[1 * cm, 8 * cm, 6 * cm],
))

story.append(PageBreak())

# ================================================================
story.append(Paragraph("TAHAP 4 — Persetujuan Operasi (Operasi)", h1))
story.append(mk_table(
    ["#", "Klik / Aksi", "Hasil"],
    [
        ["1", "Login <b>operasi1</b> &rarr; menu <b>Operasi</b>", "Daftar pengajuan MENUNGGU_OPERASI"],
        ["2", "Buka pengajuan & tinjau data", "Detail pengajuan & dokumen"],
        ["3", "Klik <b>Setujui</b>", "Status &rarr; MENUNGGU_PEMBAYARAN; invoice dibuat otomatis"],
        ["4", "(jika menolak) Klik <b>Tolak</b> + alasan", "Status &rarr; DITOLAK_OPERASI (termasuk jika kena daftar hitam)"],
    ],
    widths=[1 * cm, 8 * cm, 6 * cm],
))

# ================================================================
story.append(Paragraph("TAHAP 5 — Pembayaran (Pemohon)", h1))
story.append(mk_table(
    ["#", "Klik / Aksi", "Hasil"],
    [
        ["1", "Login <b>pemohon1</b> &rarr; menu <b>Pembayaran</b>", "Daftar invoice pengajuan"],
        ["2", "Buka invoice pengajuan", "Lihat total tagihan & jatuh tempo"],
        ["3", "Pilih <b>metode pembayaran</b>", "QRIS / Virtual Account / Transfer Manual / Cash"],
        ["4", "Klik <b>Buat Transaksi</b>", "Transaksi dibuat (nomor VA / QR / menunggu bukti)"],
        ["5", "Jika manual/cash: klik <b>Upload Bukti</b>", "Bukti bayar diunggah, status PENDING"],
    ],
    widths=[1 * cm, 8 * cm, 6 * cm],
))

# ================================================================
story.append(Paragraph("TAHAP 6 — Verifikasi Pembayaran (Komersil / Admin)", h1))
story.append(mk_table(
    ["#", "Klik / Aksi", "Hasil"],
    [
        ["1", "Login <b>komersil1</b> &rarr; menu <b>Pembayaran</b>", "Daftar bukti menunggu verifikasi"],
        ["2", "Buka transaksi, periksa bukti", "Detail bukti & nominal"],
        ["3", "Klik <b>Valid / Lunas</b>", "Transaksi PAID, invoice PAID, pengajuan &rarr; DIBAYAR"],
        ["4", "(jika tidak valid) Klik <b>Invalid</b>", "Transaksi gagal; pemohon upload ulang"],
    ],
    widths=[1 * cm, 8 * cm, 6 * cm],
))

story.append(PageBreak())

# ================================================================
story.append(Paragraph("TAHAP 7 — Acknowledge AOCH (opsional)", h1))
story.append(mk_table(
    ["#", "Klik / Aksi", "Hasil"],
    [
        ["1", "Login <b>aoch1</b> &rarr; menu <b>AOCH</b>", "Daftar pengajuan DIBAYAR"],
        ["2", "Klik <b>Acknowledge</b> pada pengajuan", "Status &rarr; ACKNOWLEDGED_AOCH; notifikasi ke Operasi"],
    ],
    widths=[1 * cm, 8 * cm, 6 * cm],
))

# ================================================================
story.append(Paragraph("TAHAP 8 — Terbitkan PAS (Operasi)", h1))
story.append(mk_table(
    ["#", "Klik / Aksi", "Hasil"],
    [
        ["1", "Login <b>operasi1</b> &rarr; menu <b>Operasi</b>", "Daftar pengajuan DIBAYAR / ACKNOWLEDGED_AOCH"],
        ["2", "Buka pengajuan", "Detail siap terbit"],
        ["3", "Klik <b>Terbitkan PAS</b>", "Status &rarr; <b>PAS_TERBIT</b>; pemohon dinotifikasi"],
        ["4", "Pemohon mengambil PAS di Operasi", "Layanan siap dilaksanakan"],
    ],
    widths=[1 * cm, 8 * cm, 6 * cm],
))

story.append(Spacer(1, 8))
story.append(Paragraph("Setelah PAS terbit (penutup alur):", h2))
story.append(li("Operasi menandai <b>DILAKSANAKAN</b> saat layanan diberikan, lalu <b>SELESAI</b>."))
story.append(li("Pemohon dapat melihat riwayat status & notifikasi di dashboard."))

story.append(Spacer(1, 10))
story.append(Paragraph("Alur status inti: DRAFT &rarr; DIAJUKAN &rarr; VERIFIKASI_KOMERSIL &rarr; DISETUJUI_KOMERSIL &rarr; MENUNGGU_OPERASI &rarr; MENUNGGU_PEMBAYARAN &rarr; DIBAYAR &rarr; PAS_TERBIT.", note))

doc.build(story)
print("PDF berhasil dibuat:", OUTPUT)
