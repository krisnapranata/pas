#!/usr/bin/env python
"""Generate PDF alur penggunaan aplikasi PAS Bandara (pemohon -> PAS terbit)."""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

BASE_URL = "http://127.0.0.1:8000"

styles = getSampleStyleSheet()
title = ParagraphStyle("title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, spaceAfter=6)
subtitle = ParagraphStyle("subtitle", parent=styles["Normal"], fontSize=10, textColor=colors.grey, alignment=TA_CENTER, spaceAfter=12)
h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#0d6efd"))
h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, spaceBefore=8, spaceAfter=4)
body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, leading=14)
code = ParagraphStyle("code", parent=styles["Normal"], fontName="Courier", fontSize=9, leading=12, textColor=colors.HexColor("#333333"), backColor=colors.HexColor("#f5f5f5"), borderPadding=4)
step = ParagraphStyle("step", parent=styles["Normal"], fontSize=10, leading=14, leftIndent=14, bulletIndent=0)
note = ParagraphStyle("note", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#6c757d"))

def li(txt):
    return Paragraph(txt, body, bulletText="\u2022")

def mk_table(header, rows, widths=None):
    data = [[Paragraph("<b>%s</b>" % c, step) for c in header]] + rows
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
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

doc = SimpleDocTemplate(
    "/home/krisna/BANDARA/PAS/ALUR_APLIKASI_PAS_BANDARA.pdf",
    pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm, leftMargin=1.8*cm, rightMargin=1.8*cm,
    title="Alur Aplikasi PAS Bandara",
)

story = []
story.append(Paragraph("Alur Aplikasi PAS Bandara", title))
story.append(Paragraph("Panduan Penggunaan End-to-End: Registrasi Pemohon &rarr; PAS Terbit", subtitle))
story.append(Paragraph("<i>Dokumen ini memandu klik setiap menu dari awal sampai PAS diterbitkan dengan QR Code.</i>", note))

# ----------------------------------------------------------------
story.append(Paragraph("Ringkasan Alur", h1))
story.append(li("Pengguna memakai 2 akun bergantian: <b>pemohon</b> (submit) dan <b>petugas/admin</b> (verifikasi, screening, bayar, approval, terbitkan)."))
story.append(li("<b>Pemohon</b> = akun <b>pemohon1</b> / pemohon123. <b>Petugas</b> = akun role demo (lihat tabel)."))
story.append(li("Petugas membuka panelnya via menu di sidebar setelah login, sesuai role masing-masing."))
story.append(Spacer(1, 6))

story.append(Paragraph("Akun Demo yang Digunakan", h2))
story.append(mk_table(
    ["Akun (username)", "Role", "Password"],
    [
        ["pemohon1", "Pemohon", "pemohon123"],
        ["admin", "Superadmin", "admin123"],
        ["verifikator1", "Verifikator", "demo123"],
        ["petugas_screening1", "Petugas Screening", "demo123"],
        ["petugas_bayar1", "Petugas Pembayaran", "demo123"],
        ["approver1", "Approver", "demo123"],
    ],
    widths=[5*cm, 6*cm, 3.5*cm],
))
story.append(Spacer(1, 4))
story.append(Paragraph("Link: Login <b>%s/login/</b> &bull; Daftar <b>%s/register/</b> &bull; Admin <b>%s/admin/</b>" % (BASE_URL, BASE_URL, BASE_URL), body))

story.append(PageBreak())

# ================================================================
story.append(Paragraph("ALUR 1 — Registrasi Pemohon (role: Pemohon)", h1))
story.append(Paragraph("Urutan menu yang diklik:", h2))
story.append(mk_table(
    ["#", "Klik", "Aksi / Isian"],
    [
        ["1", "Buka %s/register/" % BASE_URL, "Halaman registrasi"],
        ["2", "Isi form", "Username, nama, email, no. HP, password"],
        ["3", "Klik tombol <b>Daftar</b>", "Akun pemohon dibuat, otomatis login"],
    ],
    widths=[1*cm, 5.5*cm, 8*cm],
))
story.append(Paragraph("Setelah login, kelola data pribadi & perusahaan lewat admin atau hubungi admin.", note))

# ================================================================
story.append(Paragraph("ALUR 2 — Buat Pengajuan PAS (role: Pemohon)", h1))
story.append(mk_table(
    ["#", "Klik", "Aksi / Isian"],
    [
        ["1", "Dashboard", "Tampil setelah login <b>pemohon1</b>"],
        ["2", "Menu <b>Pengajuan PAS</b>", "Daftar pengajuan"],
        ["3", "Klik <b>+ Buat Pengajuan</b>", "Form pengajuan"],
        ["4", "Pilih <b>Perusahaan</b>", "mis. PT Angkasa Logistik"],
        ["5", "Pilih <b>Jenis PAS</b>", "mis. PAS Tahunan"],
        ["6", "Isi <b>Tanggal Mulai</b>, <b>Keperluan</b>, <b>Area Akses</b>", "Tanggal selesai dihitung otomatis"],
        ["7", "Klik <b>Simpan Draft</b>", "Pengajuan status DRAFT + nomor PAS-2026-xxxxxx"],
        ["8", "Upload dokumen persyaratan", "Klik <b>Upload</b> tiap persyaratan"],
        ["9", "Klik <b>Ajukan Pengajuan</b>", "Status jadi SUBMITTED"],
    ],
    widths=[1*cm, 5.5*cm, 8*cm],
))

# ================================================================
story.append(Paragraph("ALUR 3 — Verifikasi Dokumen (role: verifikator1)", h1))
story.append(mk_table(
    ["#", "Klik", "Aksi / Isian"],
    [
        ["1", "Login <b>verifikator1</b>", "Akun role VERIFIKATOR"],
        ["2", "Menu <b>Pengajuan PAS</b>", "Daftar semua pengajuan"],
        ["3", "Buka pengajuan SUBMITTED", "Klik <b>Detail</b>"],
        ["4", "Menu verifikasi dokumen", "Atau %s/pas/verifikasi/&lt;id&gt;/" % BASE_URL],
        ["5", "Pilih status tiap dokumen", "VALID / INVALID / REVISI"],
        ["6", "Klik <b>Simpan Verifikasi</b>", "Jika semua VALID -> ADMIN_APPROVED"],
    ],
    widths=[1*cm, 5.5*cm, 8*cm],
))

story.append(PageBreak())

# ================================================================
story.append(Paragraph("ALUR 4 — Screening: Jadwal, Booking, Hasil (role: pemohon & petugas_screening1)", h1))
story.append(Paragraph("<b>4a.</b> Pemohon memilih jadwal & booking:", h2))
story.append(mk_table(
    ["#", "Klik", "Aksi / Isian"],
    [
        ["1", "Login <b>pemohon1</b>", "Pengajuan sudah ADMIN_APPROVED"],
        ["2", "Menu <b>Jadwal Screening</b>", "Lihat jadwal kuota"],
        ["3", "Klik <b>Booking</b> pada jadwal", "Dapat nomor booking SCR-2026-xxxxxx + antrian"],
    ],
    widths=[1*cm, 5.5*cm, 8*cm],
))
story.append(Paragraph("<b>4b.</b> Petugas screening memproses peserta:", h2))
story.append(mk_table(
    ["#", "Klik", "Aksi / Isian"],
    [
        ["1", "Login <b>petugas_screening1</b>", "Akun role PETUGAS_SCREENING"],
        ["2", "Menu <b>Jadwal Screening</b>", "Jadwal + tombol <b>Peserta</b>"],
        ["3", "Klik <b>Peserta</b>", "Daftar booking per jadwal"],
        ["4", "Klik <b>Check-in</b>", "Status booking -> CHECKED_IN"],
        ["5", "Klik <b>Input Hasil</b>", "Pilih Lulus / Tidak Lulus + catatan"],
        ["6", "Simpan", "Pengajuan -> SCREENING_PASSED (atau FAILED)"],
    ],
    widths=[1*cm, 5.5*cm, 8*cm],
))

# ================================================================
story.append(Paragraph("ALUR 5 — Pembayaran: Invoice, Bayar, Verifikasi (role: pemohon & petugas_bayar1)", h1))
story.append(Paragraph("<b>5a.</b> Pemohon membuat invoice & membayar:", h2))
story.append(mk_table(
    ["#", "Klik", "Aksi / Isian"],
    [
        ["1", "Login <b>pemohon1</b>", "Pengajuan status SCREENING_PASSED"],
        ["2", "Menu <b>Pembayaran</b>", "Daftar invoice"],
        ["3", "Pada pengajuan, <b>Buat Invoice</b>", "Invoice INV-2026-xxxxxx dibuat"],
        ["4", "Klik <b>Bayar</b>", "Pilih metode (QRIS / VA / Transfer Manual / Cash)"],
        ["5", "Klik <b>Buat Transaksi</b>", "Muncul nomor VA / QR / link"],
        ["6", "(jika manual) Upload bukti bayar", "Klik <b>Upload Bukti</b>"],
    ],
    widths=[1*cm, 5.5*cm, 8*cm],
))
story.append(Paragraph("<b>5b.</b> Petugas memverifikasi pembayaran manual:", h2))
story.append(mk_table(
    ["#", "Klik", "Aksi / Isian"],
    [
        ["1", "Login <b>petugas_bayar1</b>", "Akun role PETUGAS_PEMBAYARAN"],
        ["2", "Menu <b>Pembayaran</b>", "Dashboard rekonsiliasi transaksi"],
        ["3", "Klik <b>Verifikasi</b> pada transaksi manual", "Lihat bukti transfer"],
        ["4", "Klik <b>Valid / Lunas</b>", "Transaksi & invoice -> PAID, pengajuan -> PAYMENT_PAID"],
    ],
    widths=[1*cm, 5.5*cm, 8*cm],
))

story.append(PageBreak())

# ================================================================
story.append(Paragraph("ALUR 6 — Approval Berjenjang (role: approver1 & lainnya)", h1))
story.append(Paragraph("Workflow default: Admin PAS &rarr; Verifikator &rarr; Security/AVSEC &rarr; Pejabat Berwenang.", h2))
story.append(mk_table(
    ["#", "Klik", "Aksi / Isian"],
    [
        ["1", "Login <b>approver1</b>", "Akun role APPROVER (bisa pakai role lain sesuai level)"],
        ["2", "Menu <b>Approval</b>", "Daftar pengajuan PAYMENT_PAID"],
        ["3", "Klik <b>Kirim Approval</b>", "Membuat rantai approval per level"],
        ["4", "Klik <b>Detail</b>", "Lihat alur approval"],
        ["5", "Klik <b>Proses</b> tiap level", "Pilih <b>Setujui</b> / <b>Tolak</b> + catatan"],
        ["6", "Approve sampai level terakhir", "Pengajuan -> APPROVED"],
    ],
    widths=[1*cm, 5.5*cm, 8*cm],
))

# ================================================================
story.append(Paragraph("ALUR 7 — Terbitkan PAS + QR Code (role: admin/approver)", h1))
story.append(mk_table(
    ["#", "Klik", "Aksi / Isian"],
    [
        ["1", "Login <b>admin</b>", "Akun superuser"],
        ["2", "Menu <b>Pengajuan PAS</b>", "Buka pengajuan status APPROVED"],
        ["3", "Klik <b>Terbitkan PAS</b>", "PASCard dibuat: PAS-2026-000001 + QR token"],
        ["4", "Cek menu <b>PAS Terbit</b>", "Daftar PAS terbit"],
        ["5", "Menu <b>PAS Saya</b> (pemohon)", "Lihat & cetak kartu PAS"],
        ["6", "Klik <b>Cetak / Lihat</b>", "Kartu + QR Code siap print"],
        ["7", "Scan QR", "Arahkan ke %s/pas/verify/&lt;token&gt;/ -> PAS VALID" % BASE_URL],
    ],
    widths=[1*cm, 5.5*cm, 8*cm],
))

story.append(Spacer(1, 10))
story.append(Paragraph("<b>Catatan:</b> Untuk PAS Kendaraan / Visitor, jenis & persyaratan bisa berbeda; alur tetap sama menyesuaikan <i>butuh_screening</i> dan <i>butuh_approval</i> dari jenis PAS.", note))

doc.build(story)
print("PDF berhasil dibuat: /home/krisna/BANDARA/PAS/ALUR_APLIKASI_PAS_BANDARA.pdf")
