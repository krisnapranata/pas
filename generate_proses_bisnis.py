#!/usr/bin/env python
"""Generator deck "Alur Proses Bisnis PAS Bandara".

Sumber kebenaran isi deck ini adalah KODE aplikasi, bukan dokumen lama.
Setiap aturan di bawah sudah diverifikasi ke file terkait:

  pas/views.py, pas/models.py, pas/services.py, pas/forms.py, pas/urls.py
  pembayaran/views.py, pembayaran/models.py, notifikasi/services.py
  dashboard/views.py, accounts/models.py

Jalankan:
    ./venv/bin/python generate_proses_bisnis.py

Output:
    proses_bisnis.pptx  (deck utama)
    proses_bisnis.ppt   (dikonversi dari pptx)
    proses_bisnis.pdf   (dikonversi dari pptx)
"""

from __future__ import annotations

import os
import subprocess
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PPTX = os.path.join(BASE_DIR, "proses_bisnis.pptx")

# ---------------------------------------------------------------- design tokens
FONT = "Calibri"

BLUE = RGBColor(0x0F, 0x62, 0xFE)
RED = RGBColor(0xDA, 0x1E, 0x28)
GREEN = RGBColor(0x24, 0xA1, 0x48)
PURPLE = RGBColor(0x8A, 0x3F, 0xFC)
TEAL = RGBColor(0x00, 0x9D, 0x9A)
INK = RGBColor(0x16, 0x16, 0x16)
GREY = RGBColor(0x52, 0x52, 0x52)
MUTED = RGBColor(0x6C, 0x75, 0x7D)
RULE = RGBColor(0xE0, 0xE0, 0xE0)
SOFT = RGBColor(0xF4, 0xF4, 0xF4)
BORDER = RGBColor(0xC6, 0xC6, 0xC6)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

SW, SH = Inches(13.3333), Inches(7.5)
ML = 0.55  # margin kiri konten
CW = 12.23  # lebar konten
FOOTER_Y = 7.08

AKTOR = {
    "PEMOHON": BLUE,
    "KOMERSIL": GREEN,
    "OPERASI": PURPLE,
    "AOCH": TEAL,
    "AVSEC": RED,
    "ADMINISTRATOR": INK,
}

FOOTER_TEXT = "Alur Proses Bisnis PAS Bandara — diselaraskan dengan implementasi kode"


# ---------------------------------------------------------------- primitives
def _solid(shape, color: RGBColor) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def _noline(shape) -> None:
    shape.line.fill.background()


def _write(tf, paras, *, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE,
           margins=(0.06, 0.06, 0.03, 0.03), gap=None):
    """paras: list of (text, size, bold, color) atau list-of-list-of-run."""
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = Inches(margins[0])
    tf.margin_right = Inches(margins[1])
    tf.margin_top = Inches(margins[2])
    tf.margin_bottom = Inches(margins[3])
    while len(tf.paragraphs) > len(paras):
        tf._txBody.remove(tf.paragraphs[-1]._p)
    for i, spec in enumerate(paras):
        p = tf.paragraphs[i] if i < len(tf.paragraphs) else tf.add_paragraph()
        p.alignment = align
        runs = spec if isinstance(spec, list) else [spec]
        for r in runs:
            text, size, bold, color = r
            run = p.add_run()
            run.text = text
            run.font.name = FONT
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.color.rgb = color
    if gap:
        for i, p in enumerate(tf.paragraphs):
            if i < len(tf.paragraphs) - 1:
                p.space_after = Pt(gap)
    return tf


def textbox(slide, x, y, w, h, paras, **kw):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if isinstance(paras, _BulletList):
        kw.setdefault("gap", paras.gap)
        paras = list(paras)
    _write(tb.text_frame, paras, **kw)
    return tb


def shape(slide, kind, x, y, w, h, fill=None, line=None, paras=None, **kw):
    s = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    s.shadow.inherit = False
    if fill is None:
        s.fill.background()
        _noline(s)
    elif fill == "none":
        _solid(s, WHITE)
        s.fill.background()
        _noline(s)
    else:
        _solid(s, fill)
    if line is not None:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
        s.line.color.rgb = line
        s.line.width = Pt(0.75)
    if paras:
        if isinstance(paras, _BulletList):
            kw.setdefault("gap", paras.gap)
            paras = list(paras)
        _write(s.text_frame, paras, **kw)
    else:
        s.text_frame.word_wrap = True
    return s


def rect(slide, x, y, w, h, fill, line=None):
    return shape(slide, MSO_SHAPE.RECTANGLE, x, y, w, h, fill, line)


def rrect(slide, x, y, w, h, fill, paras, line=None, adj=0.09, **kw):
    s = shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill, line, paras, **kw)
    try:
        s.adjustments[0] = adj
    except (IndexError, ValueError):
        pass
    return s


def step(slide, x, y, w, h, fill, title, sub=None, tsize=12, ssize=9):
    paras = [(title, tsize, True, WHITE)]
    if sub:
        paras.append((sub, ssize, False, WHITE))
    return rrect(slide, x, y, w, h, fill, paras, align=PP_ALIGN.CENTER)


def arrow_r(slide, x, y, w, h, color=MUTED):
    return shape(slide, MSO_SHAPE.RIGHT_ARROW, x, y, w, h, color)


def arrow_d(slide, x, y, w, h, color=MUTED):
    return shape(slide, MSO_SHAPE.DOWN_ARROW, x, y, w, h, color)


def chevron(slide, x, y, w, h, fill):
    return shape(slide, MSO_SHAPE.CHEVRON, x, y, w, h, fill)


def hop(slide, x1, y1, x2, y2, color=MUTED):
    """Lomp antar kolom: turun, mendatar, lalu turun lagi.

    Digambar dari shape biasa (bukan konektor) supaya kepala panahnya
    selalu terlihat di PowerPoint, WPS, maupun LibreOffice.
    """
    lw = 0.022
    ymid = y1 + (y2 - y1) / 2
    rect(slide, x1 - lw / 2, y1, lw, ymid - y1, color)
    rect(slide, min(x1, x2), ymid - lw / 2, abs(x2 - x1), lw, color)
    rect(slide, x2 - lw / 2, ymid, lw, (y2 - 0.11) - ymid, color)
    head = shape(slide, MSO_SHAPE.ISOSCELES_TRIANGLE,
                 x2 - 0.075, y2 - 0.13, 0.15, 0.13, color)
    head.rotation = 180
    return head


def diamond(slide, x, y, w, h, fill, text, tsize=10):
    lines = text if isinstance(text, (list, tuple)) else [text]
    paras = [(t, tsize, True, WHITE) for t in lines]
    return shape(slide, MSO_SHAPE.DIAMOND, x, y, w, h, fill=fill, paras=paras,
                 align=PP_ALIGN.CENTER, margins=(0.14, 0.14, 0.02, 0.02))


def panel(slide, x, y, w, h, title, paras, fill=SOFT, tsize=12, bsize=9.5,
          title_color=INK, para_color=GREY, gap=None):
    """Panel penjelasan dengan judul dan daftar paragraf."""
    rect(slide, x, y, w, h, fill, RULE)
    textbox(slide, x + 0.18, y + 0.12, w - 0.36, 0.32,
            [(title, tsize, True, title_color)], anchor=MSO_ANCHOR.TOP)
    textbox(slide, x + 0.18, y + 0.48, w - 0.36, h - 0.60, paras,
            anchor=MSO_ANCHOR.TOP, margins=(0, 0, 0, 0), gap=gap)


def bullets(items, size=9.5, color=GREY, gap=None):
    """Daftar paragraf bullet; gap (pt) menambah jarak antarbaris."""
    out = []
    for it in items:
        if isinstance(it, tuple):
            head, body = it
            out.append([("• ", size, True, color),
                        (head, size, True, color),
                        (body, size, False, color)])
        else:
            out.append([("• ", size, True, color), (it, size, False, color)])
    return _BulletList(out, gap)


class _BulletList(list):
    """List paragraf bullet yang membawa pengaturan jarak antarbaris."""

    def __init__(self, items, gap):
        super().__init__(items)
        self.gap = gap


# ---------------------------------------------------------------- chrome
def new_deck():
    prs = Presentation()
    prs.slide_width = SW
    prs.slide_height = SH
    return prs


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def chrome(slide, eyebrow, title, page):
    rect(slide, 0, 0, 13.3333, 0.16, BLUE)
    textbox(slide, ML, 0.26, CW, 0.30, [(eyebrow, 11, True, GREY)])
    textbox(slide, ML, 0.53, CW, 0.55, [(title, 22, True, INK)])
    rect(slide, ML, 1.16, CW, 0.02, RULE)
    textbox(slide, ML, FOOTER_Y, 9.5, 0.28, [(FOOTER_TEXT, 9, False, GREY)])
    textbox(slide, 12.20, FOOTER_Y, 0.60, 0.28,
            [(str(page), 9, False, GREY)], align=PP_ALIGN.RIGHT)


# ---------------------------------------------------------------- table helper
def table(slide, x, y, w, h, headers, rows, col_w, head_fill=INK,
          body_size=9, head_size=9.5, row_h=0.30, head_h=0.32):
    shape_rows = len(rows) + 1
    gfx = slide.shapes.add_table(shape_rows, len(headers), Inches(x), Inches(y),
                                 Inches(w), Inches(h))
    tbl = gfx.table
    tbl.first_row = False
    tbl.horz_banding = False
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = Inches(cw)
    tbl.rows[0].height = Inches(head_h)
    for r in range(1, shape_rows):
        tbl.rows[r].height = Inches(row_h)

    def fill_cell(cell, color):
        cell.fill.solid()
        cell.fill.fore_color.rgb = color

    for c, htxt in enumerate(headers):
        cell = tbl.cell(0, c)
        fill_cell(cell, head_fill)
        _write(cell.text_frame, [(htxt, head_size, True, WHITE)],
               anchor=MSO_ANCHOR.MIDDLE, margins=(0.08, 0.06, 0.02, 0.02))

    for r, row in enumerate(rows, start=1):
        bg = WHITE if r % 2 else SOFT
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            fill_cell(cell, bg)
            if isinstance(val, tuple):
                txt, color, bold = val
            else:
                txt, color, bold = val, GREY, False
            _write(cell.text_frame, [(txt, body_size, bold, color)],
                   anchor=MSO_ANCHOR.MIDDLE, margins=(0.08, 0.06, 0.02, 0.02))
    return tbl


# ================================================================ SLIDE 1
def slide_cover(prs):
    s = blank(prs)
    rect(s, 0, 0, 13.3333, 7.5, INK)
    rect(s, 0, 0, 13.3333, 0.22, BLUE)
    textbox(s, 0.90, 1.62, 11.5, 1.05, [("ALUR PROSES BISNIS", 40, True, WHITE)])
    textbox(s, 0.90, 2.62, 11.5, 0.60,
            [("PAS Bandara — Passenger Assistance Service", 26, False, BORDER)])
    rect(s, 0.90, 3.52, 2.60, 0.06, BLUE)
    textbox(s, 0.90, 3.82, 11.5, 1.60, [
        ("Pengajuan (tanpa login)  →  Pembayaran & Verifikasi  →  Penerbitan PAS Visitor",
         15, False, WHITE),
        ("→  Nomor PAS & Serah Terima Fisik (AOCH)  →  Pengembalian PAS  →  Selesai",
         15, False, WHITE),
        ("", 6, False, WHITE),
        ("Diselaraskan dengan implementasi kode aplikasi (status, aturan, dan pembagian peran aktual)",
         11, False, BORDER),
    ], anchor=MSO_ANCHOR.TOP)
    textbox(s, 0.90, 6.34, 11.5, 0.50,
            [("Aktor: Pemohon (PIC)  •  Komersil  •  Operasi  •  AOCH  •  Avsec  •  Administrator",
              11.5, False, BORDER)])
    return s


# ================================================================ SLIDE 2
def slide_aktor(prs):
    s = blank(prs)
    chrome(s, "PROSES BISNIS — KONTEKS", "Aktor & Peran dalam Alur", 2)
    rows = [
        ("PEMOHON", AKTOR["PEMOHON"], 1.50,
         "Mengajukan lewat form publik tanpa harus login: mengisi PIC penanggung jawab, memilih "
         "layanan, mengisi data pendamping beserta dokumen identitas, lalu membayar dan mengunggah "
         "bukti bayar. Lacik status tanpa akun memakai nomor request, NIK, NPWP, atau nomor HP."),
        ("KOMERSIL", AKTOR["KOMERSIL"], 2.38,
         "Mengelola master layanan & tarif; memvalidasi bukti pembayaran dengan tiga keputusan "
         "(Valid / Lunas, Tidak Valid, Koreksi); meneruskan pengajuan yang lunas ke Operasi."),
        ("OPERASI", AKTOR["OPERASI"], 3.26,
         "Mengelola daftar hitam (blacklist) NIK & nama perusahaan; mengecek ulang seluruh NIK "
         "sebelum menerbitkan PAS Visitor; menerbitkan PAS; menandai pelaksanaan & penyelesaian."),
        ("AOCH", AKTOR["AOCH"], 4.14,
         "Memasukkan nomor PAS Visitor per pendamping; mencatat SERAH TERIMA fisik PAS berupa foto "
         "orang penerima + tanda tangan elektronik + tanggal & jam; mencatat pengembalian; menandai "
         "pengajuan selesai setelah kartu dikembalikan."),
        ("AVSEC", AKTOR["AVSEC"], 5.02,
         "Hanya memverifikasi dan membaca: dashboard ringkasan PAS (aktif / kedaluwarsa) serta menu "
         "Verifikasi PAS. Tidak mengubah status pengajuan dan tidak mencatat serah terima."),
        ("ADMINISTRATOR", AKTOR["ADMINISTRATOR"], 5.90,
         "Akses penuh ke seluruh modul — is_staff melewati semua pemeriksaan peran — ditambah "
         "Statistik, Laporan, ekspor CSV, dan Django admin."),
    ]
    for nama, color, y, desc in rows:
        chevron(s, ML, y + 0.14, 0.30, 0.52, color)
        rrect(s, 0.95, y, 2.50, 0.80, color, [(nama, 13, True, WHITE)],
              align=PP_ALIGN.CENTER)
        textbox(s, 3.65, y, 9.15, 0.80, [(desc, 10.5, False, INK)])
    return s


# ================================================================ SLIDE 3
def slide_ringkasan(prs):
    s = blank(prs)
    chrome(s, "ALUR UTAMA", "Ringkasan Alur: Pengajuan → Pembayaran → PAS → Serah Terima", 3)

    col = {"A": 2.25, "B": 5.30, "C": 8.05, "D": 10.45}
    cw = {"A": 2.80, "B": 2.50, "C": 2.15, "D": 2.30}
    for key, nama in (("A", "PENGAJUAN"), ("B", "PEMBAYARAN & VERIFIKASI"),
                      ("C", "PENERBITAN"), ("D", "SERAH TERIMA")):
        textbox(s, col[key], 1.24, cw[key], 0.28, [(nama, 9, True, GREY)])

    LY, LH = [1.60, 2.60, 3.60, 4.60, 5.60], 0.72
    lanes = [
        ("PEMOHON", AKTOR["PEMOHON"], [
            ("A", "Buka Form Pengajuan", "publik — tanpa login"),
            ("B", "Bayar & Unggah Bukti", "transfer manual / tunai"),
        ], None),
        ("KOMERSIL", AKTOR["KOMERSIL"], [
            ("B", "Validasi Bukti Bayar", "Valid / Tidak Valid / Koreksi"),
        ], "B"),
        ("OPERASI", AKTOR["OPERASI"], [
            ("C", "Terbitkan PAS Visitor", "cek ulang blacklist"),
        ], "C"),
        ("AOCH", AKTOR["AOCH"], [
            ("C", "Nomor PAS per pendamping", "1 nomor = 1 pendamping"),
            ("D", "Serah Terima → Kembalikan", "foto + TTD + tanggal & jam"),
        ], None),
        ("AVSEC", AKTOR["AVSEC"], [
            ("D", "Cek Status PAS", "aktif / kedaluwarsa"),
        ], None),
    ]
    for i, (nama, color, boxes, next_key) in enumerate(lanes):
        y = LY[i]
        rrect(s, ML, y, 1.55, LH, color, [(nama, 10, True, WHITE)],
              align=PP_ALIGN.CENTER)
        rect(s, 2.15, y, 10.65, LH, SOFT, RULE)
        prev_end = None
        for key, t, sub in boxes:
            bx, by, bw, bh = col[key], y + 0.07, cw[key], 0.58
            step(s, bx, by, bw, bh, color, t, sub, tsize=9.5, ssize=7.5)
            if prev_end is not None:
                arrow_r(s, prev_end + 0.06, by + 0.17, 0.18, 0.24)
            prev_end = bx + bw
        if next_key:
            ex = col[boxes[-1][0]] + cw[boxes[-1][0]]
            tx = col[next_key] + cw[next_key] / 2
            if abs(ex - tx) < 0.05:
                arrow_d(s, tx - 0.11, y + LH + 0.02, 0.22, 0.26)
            else:
                hop(s, ex, y + LH, tx, LY[i + 1] + 0.07)
    textbox(s, 10.45, 6.42, 2.35, 0.55,
            [("Verifikasi Avsec adalah pengecekan silang, bukan tahap alur — "
              "dapat dilakukan kapan saja.", 8.5, False, MUTED)],
            anchor=MSO_ANCHOR.TOP)
    return s


# ================================================================ SLIDE 4
def slide_fase1(prs):
    s = blank(prs)
    chrome(s, "FASE 1 — PENGAJUAN",
           "Pemohon: Batasan Area, Form Publik & Pengecekan Daftar Hitam", 4)

    boxes = [
        (BLUE, "Halaman Batasan Area", "wajib tampil sebelum form"),
        (MUTED, "Form Pengajuan Publik", "tanpa login, tanpa daftar akun"),
        (BLUE, "Isi Data Pengajuan", "PIC + layanan + pendamping"),
        (BLUE, "Kirim Pengajuan", "sistem cek NIK PIC & pendamping"),
        (GREEN, "Lolos → Invoice", "status MENUNGGU_PEMBAYARAN"),
    ]
    y = 1.46
    for i, (color, t, sub) in enumerate(boxes):
        step(s, 0.90, y, 3.45, 0.78, color, t, sub, tsize=12, ssize=9)
        if i < len(boxes) - 1:
            arrow_d(s, 2.51, y + 0.80, 0.24, 0.28)
        y += 1.08

    x, w = 4.75, 8.05
    panel(s, x, 1.46, w, 1.66, "Batasan area — 2 tahap, wajib dibaca pemohon", bullets([
        ("Tahap 1 (wajib, tiap kunjungan baru): ", "halaman batasan area tampil lebih dulu; pemohon "
         "menekan tombol lanjut baru form pengajuan terbuka (pas/views.py:363-369)."),
        ("DEPARTURE: ", "Check-in Counter (domestik & internasional), Security Check (Avsec), "
         "Boarding Lounge."),
        ("ARRIVAL: ", "Baggage Claim, Arrival Hall sampai Meeting Point."),
        ("5 aturan yang ditampilkan: ", "sekali pakai & wajib dikembalikan ke AOCH; diambil di "
         "AOCH On Duty (Solution Room); tidak boleh dipinjam/dialihkan dipakai esok hari; setiap "
         "pendamping wajib NIK + dokumen identitas; NIK daftar hitam ditolak saat kirim."),
    ], size=9))

    panel(s, x, 3.28, w, 1.86, "Isi form pengajuan", bullets([
        ("PIC penanggung jawab: ", "nama, NIK, NPWP, no HP wajib; e-mail opsional. Tidak ada lagi "
         "input tujuan/instansi terpisah."),
        ("Layanan: ", "radio button yang menampilkan nama + harga, dikelompokkan Departure / Arrival. "
         "Tanggal pelaksanaan tidak boleh di masa lalu (min = hari ini)."),
        ("Pendamping: ", "jumlah mengikuti batas layanan (min 1, maks 5 atau 10). Setiap pendamping: "
         "nama, NIK, dan unggah identitas (jpg, jpeg, png, gif, webp, atau pdf)."),
        ("Tarif: ", "disalin sebagai snapshot ke pengajuan saat dibuat — perubahan tarif "
         "berikutnya tidak mengubah pengajuan yang sudah ada."),
    ], size=9))

    panel(s, x, 5.30, w, 1.68, "Pengecekan daftar hitam saat kirim", bullets([
        ("Dicocokkan pada data POST mentah ", "agar NIK yang kena tetap terdeteksi walau berkas "
         "identitas belum lengkap. NIK dinormalisasi (buang spasi/titik/garis); nama dibandingkan "
         "case-insensitive."),
        ("Jika ada yang kena: ", "pengajuan TIDAK PERNAH DIBUAT — form dikembalikan dengan kolom "
         "yang bermerah, berkas identitas yang sudah diunggah tetap tersimpan, dan audit log "
         "TOLAK_BLACKLIST_NIK tercatat. Tidak ada invoice dan tidak ada tagihan."),
    ], size=9), fill=RGBColor(0xFF, 0xF2, 0xF3), title_color=RED)
    return s


# ================================================================ SLIDE 5
def slide_fase2(prs):
    s = blank(prs)
    chrome(s, "FASE 2 — PEMBAYARAN & VERIFIKASI",
           "Pemohon Bayar → Komersil Validasi Bukti", 5)

    boxes = [
        (BLUE, "Pilih Metode Bayar", "QRIS, Virtual Account, E-Wallet, Transfer Manual, Tunai"),
        (BLUE, "Unggah Bukti Bayar", "status BUKTI_TERUNGGAH"),
        (GREEN, "Komersil Validasi Bukti", "tiga keputusan tersedia"),
    ]
    y = 1.46
    for i, (color, t, sub) in enumerate(boxes):
        step(s, 0.90, y, 3.45, 0.78, color, t, sub, tsize=12, ssize=8.5)
        if i < len(boxes) - 1:
            arrow_d(s, 2.51, y + 0.80, 0.24, 0.28)
        y += 1.08

    x, w = 4.75, 8.05
    panel(s, x, 1.46, w, 1.62, "Tiga keputusan validasi Komersil", bullets([
        ("Valid / Lunas: ", "transaksi PAID, invoice PAID, pengajuan langsung menjadi "
         "MENUNGGU_OPERASI. Tidak lewat status DIBAYAR."),
        ("Tidak Valid: ", "transaksi FAILED dan pengajuan kembali ke MENUNGGU_PEMBAYARAN; pemohon "
         "diberi notifikasi untuk mengunggah bukti yang benar."),
        ("Koreksi (bukan lunas): ", "validasi dibatalkan — transaksi kembali PENDING, paid_at "
         "dikosongkan, invoice UNPAID, pengajuan kembali BUKTI_TERUNGGAH dan wajib divalidasi ulang."),
    ], size=9))

    table(s, x, 3.24, w, 1.38,
          ["KEPUTUSAN", "PAYMENTTRANSACTION", "INVOICE", "PENGAJUAN"],
          [
              [("Valid / Lunas", GREEN, True), "PAID", "PAID",
               ("→ MENUNGGU OPERASI", GREEN, True)],
              [("Tidak Valid", RED, True), "FAILED", "tidak berubah",
               ("→ MENUNGGU PEMBAYARAN", RED, True)],
              [("Koreksi", PURPLE, True), "PENDING", "UNPAID",
               ("→ BUKTI TERUNGGAH", PURPLE, True)],
          ],
          col_w=[1.85, 2.10, 1.50, 2.60], row_h=0.36)

    panel(s, x, 4.86, w, 2.12, "Catatan penting tentang pembayaran", bullets([
        ("Status DIBAYAR hanya diisi oleh webhook penyedia ", "(callback pembayaran otomatis), bukan "
         "oleh validasi manual Komersil. Tombol “Lanjut ke Operasi” milik Komersil karena itu hanya "
         "berfungsi pada deployment yang memakai webhook."),
        ("Invoice: ", "dibuat otomatis saat pengajuan lolos cek blacklist; jatuh tempo +24 jam; "
         "nomor berpola INV-YYYY-XXXXXX."),
        ("Pemohon tanpa akun: ", "akses pembayaran dijaga penanda session “lacak” — maksimal 20 "
         "pengajuan terakhir per browser. Cari invoice memakai nomor pengajuan + kontak "
         "(e-mail / no HP)."),
        ("Belum ada UI persetujuan refund ", "— pengajuan refund sudah tercatat tetapi belum ada "
         "halaman persetujuan."),
    ], size=9))
    return s


# ================================================================ SLIDE 6
def slide_fase3(prs):
    s = blank(prs)
    chrome(s, "FASE 3 — PENERBITAN PAS",
           "Operasi: Cek Ulang Blacklist & Terbitkan PAS Visitor", 6)

    # alur utama di kiri
    flow = [
        (PURPLE, "Pengajuan Masuk ke Operasi", "status MENUNGGU_OPERASI"),
        (PURPLE, "Cek Ulang Blacklist", "NIK pendamping + NIK PIC + nama/instansi"),
        (PURPLE, "Terbitkan PAS Visitor", "status PAS_TERBIT"),
        (TEAL, "Informasi ke AOCH", "notifikasi: siap diserahkan"),
    ]
    y = 1.46
    for i, (color, t, sub) in enumerate(flow):
        step(s, 0.90, y, 3.30, 0.78, color, t, sub, tsize=11.5, ssize=8)
        if i < len(flow) - 1:
            arrow_d(s, 2.43, y + 0.80, 0.24, 0.24)
        y += 1.04

    # cabang penolakan dari langkah "Cek Ulang Blacklist"
    arrow_r(s, 4.24, 2.83, 0.44, 0.24)
    textbox(s, 4.24, 2.56, 0.90, 0.24, [("tidak lolos", 8, True, RED)])
    step(s, 5.68, 2.52, 2.55, 0.78, RED, "Ditolak Operasi", "DITOLAK_OPERASI",
         tsize=11.5, ssize=8)

    # panel blacklist di bawah cabang
    panel(s, 5.68, 3.44, 2.55, 1.66, "Blacklist — 4 titik", bullets([
        "Kirim form publik — dicek dari POST mentah; pengajuan tidak dibuat.",
        "Submit pengajuan draft — dicek dari database; pengajuan tidak dikirim.",
        "Halaman Operasi — peringatan; tombol Terbitkan PAS dinonaktifkan.",
        "Saat menerbitkan — inilah gerbang yang ditegakkan: DITOLAK_OPERASI.",
    ], size=8), fill=RGBColor(0xFF, 0xF2, 0xF3), title_color=RED, tsize=10)

    # kolom kanan
    x, w = 8.55, 4.23
    panel(s, x, 1.46, w, 1.86, "Penolakan manual Operasi", bullets([
        ("Alasan penolakan WAJIB diisi ", "— tanpa alasan, permintaan ditolak."),
        ("Tidak ada syarat status ", "— Operasi dapat menolak dari status pengajuan mana pun, "
         "bukan hanya Menunggu Operasi."),
        ("Pemohon menerima notifikasi ", "“Pengajuan ditolak Operasi” beserta alasannya, dan "
         "alasan itu tersimpan di riwayat status."),
    ], size=9))

    panel(s, x, 3.48, w, 1.52, "Tanggal berlaku PAS", bullets([
        ("tanggal_berlaku_pas disalin dari tanggal_pelaksanaan, ", "bukan dari hari PAS "
         "diterbitkan."),
        ("PAS dapat diterbitkan dari tiga status: ", "Menunggu Operasi, Sudah Dibayar, dan "
         "Acknowledged AOCH."),
    ], size=9))

    panel(s, x, 5.16, w, 1.82, "Setelah PAS terbit", bullets([
        ("Status pengajuan menjadi PAS_TERBIT ", "dan riwayat status mencatat pelaku "
         "perubahannya."),
        ("Empat pihak diberi notifikasi: ", "AOCH (siap diserahkan), Pemohon, Komersil, dan "
         "Operasi."),
        ("AOCH baru bisa menyimpan nomor PAS ", "pada tahap ini — sebelumnya tombolnya "
         "dinonaktifkan."),
    ], size=9))
    return s


# ================================================================ SLIDE 7
def slide_fase4(prs):
    s = blank(prs)
    chrome(s, "FASE 4 — SERAH TERIMA", "AOCH: Nomor PAS Visitor, Penyerahan & Pengembalian", 7)

    boxes = [
        (TEAL, "Input Nomor PAS", "1 nomor untuk setiap pendamping"),
        (MUTED, "Tanggal Pelaksanaan Tercapai", "tombol terbuka otomatis"),
        (TEAL, "Catat Penyerahan", "foto + TTD + tanggal & jam"),
        (TEAL, "Catat Pengembalian", "foto + TTD pengembalian"),
        (INK, "Tandai Selesai", "pengajuan → SELESAI"),
    ]
    y = 1.42
    for i, (color, t, sub) in enumerate(boxes):
        step(s, 0.90, y, 3.45, 0.72, color, t, sub, tsize=11.5, ssize=8.5)
        if i < len(boxes) - 1:
            arrow_d(s, 2.51, y + 0.74, 0.24, 0.26)
        y += 1.00

    x, w = 4.75, 8.05
    status_boxes = [
        ("BELUM", MUTED, "Catat Penyerahan", "menunggu kartu keluar"),
        ("DITERIMA", TEAL, "Catat Pengembalian", "kartu di luar; boleh Perbarui Penyerahan"),
        ("DIKEMBALIKAN", INK, "Tandai Selesai", "siklus kartu selesai; tidak ada tombol serah lagi"),
    ]
    yy = 1.42
    for nama, color, aksi, ket in status_boxes:
        rrect(s, x, yy, 2.15, 0.62, color, [(nama, 11, True, WHITE)],
              align=PP_ALIGN.CENTER)
        arrow_r(s, x + 2.22, yy + 0.19, 0.22, 0.24)
        textbox(s, x + 2.52, yy, 5.53, 0.62,
                [[(aksi, 10.5, True, INK), ("  —  " + ket, 9.5, False, GREY)]])
        yy += 0.74

    panel(s, x, 3.66, w, 1.46, "Isian yang dicatat", bullets([
        ("Penyerahan: ", "nama penerima (wajib), NIK, jabatan, dan “ditugaskan/wakil” (opsional). "
         "Nama penerima boleh berbeda dari PIC apabila benar-benar diwakilkan."),
        ("Dokumentasi: ", "foto orang penerima (kamera langsung atau unggah berkas) dan tanda tangan "
         "elektronik digambar di layar — keduanya wajib pada serah terima maupun pengembalian."),
        ("Waktu: ", "tanggal penyerahan dicatat sekali saat penyerahan pertama; tanggal pengembalian "
         "diperbarui setiap kali dicatat."),
        ("Catatan: ", "opsional, langsung disimpan ke catatan serah terima."),
    ], size=9))

    panel(s, x, 5.28, w, 1.70, "Dampak ke status pengajuan", bullets([
        ("Saat diserahkan: ", "jika status masih PAS_TERBIT, otomatis berubah menjadi "
         "DILAKSANAKAN. Bila statusnya sudah lain (mis. ACKNOWLEDGED AOCH), catatan serah terima "
         "tetap tersimpan tetapi status pengajuan tidak berubah."),
        ("Saat dikembalikan: ", "status pengajuan BELUM berubah — baru berubah menjadi SELESAI "
         "ketika AOCH menekan “Tandai Selesai”."),
        ("Konsekuensi tampilan: ", "begitu kartu tercatat DIKEMBALIKAN, masa berlaku PAS langsung "
         "tampil SELESAI meskipun pengajuan belum Selesai."),
    ], size=9))
    return s


# ================================================================ SLIDE 8
def slide_aturan_serah(prs):
    s = blank(prs)
    chrome(s, "FASE 4 — SERAH TERIMA", "Syarat & Dampak Setiap Aksi AOCH (diperiksa server-side)", 8)
    table(s, ML, 1.42, CW, 3.50,
          ["AKSI", "SYARAT WAJIB (diperiksa berurutan)", "AKSI BERHASIL"],
          [
              [("Simpan Nomor PAS", TEAL, True),
               "Status pengajuan: PAS_TERBIT, ACKNOWLEDGED_AOCH, SIAP_DILAKSANAKAN, atau "
               "DILAKSANAKAN.\n"
               "Semua pendamping harus punya nomor.\n"
               "Nomor tidak boleh bentrok dengan pendamping lain yang masih aktif.",
               "Nomor tersimpan per pendamping.\nStatus pengajuan tidak berubah."],
              [("Catat Penyerahan", TEAL, True),
               "Hari ini ≥ tanggal pelaksanaan (tombol terkunci sebelum tanggal itu).\n"
               "Semua pendamping sudah punya nomor PAS.\n"
               "Foto orang penerima — lewat kamera atau unggah berkas.\n"
               "Tanda tangan elektronik dibuat.\n"
               "Nama penerima terisi.",
               "Serah terima = DITERIMA.\n"
               "Notifikasi “PAS diserahkan” ke pemohon.\n"
               "Status PAS_TERBIT → DILAKSANAKAN."],
              [("Catat Pengembalian", TEAL, True),
               "Serah terima sedang berstatus DITERIMA.\n"
               "Foto pengembalian.\n"
               "Tanda tangan pengembalian.\n"
               "Tidak ada batas tanggal — boleh kapan saja.",
               "Serah terima = DIKEMBALIKAN.\n"
               "Notifikasi “PAS dikembalikan” ke pemohon.\n"
               "Masa berlaku PAS langsung tampil SELESAI."],
              [("Tandai Selesai", INK, True),
               "Serah terima sudah DIKEMBALIKAN.\n"
               "Tidak ada syarat atas status pengajuan.",
               "Pengajuan = SELESAI.\nNotifikasi “Layanan selesai”."],
          ],
          col_w=[1.95, 5.60, 4.68], row_h=0.80)

    panel(s, ML, 5.14, 6.00, 1.60, "Syarat non-teknis", bullets([
        "Penyerahan cukup diwakilkan oleh PIC pemohon atau orang yang ditugaskan.",
        "PAS Visitor berlaku satu hari kalender sejak tanggal Berlaku PAS.",
        "Setelah dikembalikan, nomor PAS boleh dipakai pengajuan lain.",
    ], size=9))

    panel(s, 6.78, 5.14, 6.00, 1.60, "Perilaku tombol yang mungkin membingungkan", bullets([
        "Tombol Catat Penyerahan terkunci sebelum tanggal pelaksanaan — alasannya ditampilkan "
        "tepat di bawah tombol.",
        "Begitu kartu berstatus DIKEMBALIKAN, tidak ada lagi tombol penyerahan; satu-satunya "
        "sisa tindakan adalah Tandai Selesai.",
        "Klik tanpa tanda tangan atau foto akan ditolak dengan pesan yang menyebutkan bagian "
        "mana yang kurang.",
    ], size=9), fill=SOFT)
    return s


# ================================================================ SLIDE 9
def slide_nomor_masa(prs):
    s = blank(prs)
    chrome(s, "ATURAN PENTING", "Nomor PAS Visitor & Masa Berlaku", 9)

    panel(s, ML, 1.42, 6.00, 2.30, "Aturan nomor PAS Visitor", bullets([
        ("Satu nomor = satu pendamping, ", "bukan satu pengajuan. Nomor menempel pada baris "
         "data pendamping."),
        ("Nomor dianggap masih terpakai ", "bila pengajuan lamanya belum selesai: belum "
         "SELESAI, belum DIBATALKAN, dan kartunya belum dicatat DIKEMBALIKAN."),
        ("Nomor boleh dipakai lagi ", "apabila pengajuan lama sudah SELESAI atau DIBATALKAN, atau "
         "kartunya sudah dicatat DIKEMBALIKAN."),
        ("Pencocokan tidak membedakan huruf besar/kecil ", "dan membandingkan hanya digit NIK."),
        ("Tidak ada constraint unik di database ", "— aturan ini hanya ditegakkan di halaman "
         "AOCH. Verifikasi PAS menerapkan penyaringan yang sama saat membaca nomor."),
    ], size=9), fill=RGBColor(0xFF, 0xF2, 0xF3), title_color=RED)

    panel(s, 6.78, 1.42, 6.00, 2.30, "Masa berlaku PAS Visitor", bullets([
        ("Berlaku tepat satu hari kalender: ", "pada tanggal_berlaku_pas, habis pada "
         "tanggal_berlaku_pas + 1 hari."),
        ("tanggal_berlaku_pas diisi saat PAS diterbitkan ", "dan nilainya disalin dari "
         "tanggal_pelaksanaan pengajuan."),
        ("Perhitungan memakai zona waktu Asia/Jakarta ", "(WIB)."),
        ("Tidak ada status “kedaluwarsa” di database. ", "Status kedaluwarsa dihitung ulang dari "
         "kalender setiap kali halaman dibuka — tidak ada yang bisa “meng-expire” PAS secara manual."),
        ("Fisik PAS: ", "kartu bisa terlambat dikembalikan; yang kedaluwarsa adalah hak "
         "penggunaannya, bukan status pengajuan."),
    ], size=9))

    table(s, ML, 3.94, CW, 2.22,
          ["STATUS MASA BERLAKU", "KONDISI (diperiksa berurutan, yang pertama cocok menang)"],
          [
              [("SELESAI", INK, True), "Pengajuan sudah berstatus Selesai."],
              [("SELESAI", INK, True), "Atau kartu fisik sudah dicatat DIKEMBALIKAN — meskipun "
               "pengajuan belum Selesai."],
              [("BELUM", MUTED, True), "PAS belum diterbitkan (tanggal Berlaku PAS masih kosong)."],
              [("TERJADWAL", BLUE, True), "PAS terbit untuk tanggal yang belum datang."],
              [("AKTIF", GREEN, True), "Hari ini sama dengan tanggal Berlaku PAS."],
              [("KEDALUWARSA", RED, True), "Hari ini sudah melewati tanggal Berlaku PAS."],
          ],
          col_w=[2.55, 9.68], row_h=0.32)
    return s


# ================================================================ SLIDE 10
def slide_verifikasi(prs):
    s = blank(prs)
    chrome(s, "VERIFIKASI — AVSEC", "Cek Status PAS Visitor: Aktif atau Kedaluwarsa", 10)

    boxes = [
        (BLUE, "Menu Verifikasi PAS", "terbuka untuk publik — tanpa login"),
        (BLUE, "Masukkan Satu Nomor", "nomor request REQ-… atau nomor PAS"),
        (MUTED, "Sistem Mencocokkan", "nomor request dulu, lalu nomor PAS"),
        (GREEN, "Tampil Status PAS", "AKTIF / TERJADWAL / KEDALUWARSA / SELESAI"),
    ]
    y = 1.42
    for i, (color, t, sub) in enumerate(boxes):
        step(s, 0.90, y, 3.45, 0.76, color, t, sub, tsize=11.5, ssize=8.5)
        if i < len(boxes) - 1:
            arrow_d(s, 2.51, y + 0.78, 0.24, 0.26)
        y += 1.04

    x, w = 4.75, 8.05
    panel(s, x, 1.42, w, 1.82, "Yang ditampilkan", bullets([
        ("Banner status berwarna: ", "hijau AKTIF, merah SUDAH KEDALUWARSA, biru TERJADWAL, "
         "merah PAS SELESAI — KEMBALI, abu BELUM DITERBITKAN."),
        ("Nomor request & layanan: ", "nomor pengajuan, nama layanan, lokasi, dan status pengajuan."),
        ("Pemohon / PIC dan tanggal pelaksanaan, ", "serta tanggal Berlaku PAS dan tanggal masa "
         "berlakunya habis."),
        ("Status serah terima: ", "diserahkan ke siapa dan jam berapa, dikembalikan jam berapa."),
        ("Atas nama: ", "seluruh pendamping beserta NIK, dengan lencana nomor PAS bila sudah "
         "ditetapkan."),
        ("Setiap pencarian dicatat di audit log ", "(VERIFIKASI_PAS) — sukses maupun tidak."),
    ], size=9))

    panel(s, x, 3.40, w, 1.24, "Kalimat yang ditampilkan untuk PAS kedaluwarsa", [
        ("“PAS visitor ini sudah lewat masa berlaku dan tidak sah untuk digunakan kembali "
         "(termasuk esok hari).”", 11, True, RED),
    ], fill=RGBColor(0xFF, 0xF2, 0xF3), title_color=RED)

    panel(s, x, 4.80, w, 2.18, "Tujuan & batasan", bullets([
        ("Mencegah penyalahgunaan: ", "PAS Visitor berlaku satu hari sehingga tidak bisa "
         "dipakai lagi pada hari berikutnya."),
        ("Pencarian bersifat publik ", "— siapa pun yang memegang nomor REQ-… atau PAS-… dapat "
         "melihat statusnya. Ini disengaja untuk petugas Avsec di lapangan."),
        ("Nomor PAS yang dipakai ulang ", "otomatis tidak lagi menemukan pengajuan lama "
         "(sudah disaring SELESAI/DIBATALKAN/DIKEMBALIKAN), sehingga hasil verifikasi selalu "
         "merujuk pada pemakaian yang sedang berlaku."),
        ("Tidak ada pembatasan percobaan ", "— pencarian berulang atas nomor yang tidak dikenal "
         "tetap diperbolehkan; hanya tercatat di audit log."),
    ], size=9))
    return s


# ================================================================ SLIDE 11
def slide_notifikasi(prs):
    s = blank(prs)
    chrome(s, "PENUNJANG", "Notifikasi & Ringkasan Masa Berlaku", 11)
    table(s, ML, 1.42, CW, 4.28,
          ["PERISTIWA", "PENERIMA", "JUDUL NOTIFIKASI (persis seperti di aplikasi)"],
          [
              ["Pengajuan lolos cek identitas & invoice terbit", "Pemohon",
               ("Pengajuan diterima", BLUE, True)],
              ["Pemohon mengunggah bukti bayar", "Komersil", ("Bukti pembayaran diunggah", GREEN, True)],
              ["", "Pemohon", ("Bukti pembayaran diterima", GREEN, True)],
              ["Bukti bayar dinilai tidak valid", "Pemohon", ("Bukti pembayaran ditolak", RED, True)],
              ["Bukti bayar dinilai lunas", "Operasi", ("Siap terbitkan PAS", PURPLE, True)],
              ["", "Pemohon", ("Pembayaran diterima", GREEN, True)],
              ["Komersil meneruskan pengajuan ke Operasi", "Operasi",
               ("Siap terbitkan PAS", PURPLE, True)],
              ["Operasi menerbitkan PAS Visitor", "AOCH",
               ("PAS diterbitkan — siap diserahkan", TEAL, True)],
              ["", "Pemohon / Komersil / Operasi", ("PAS diterbitkan", BLUE, True)],
              ["PAS ditolak karena daftar hitam", "Pemohon", ("PAS tidak diterbitkan", RED, True)],
              ["Operasi menolak pengajuan manual", "Pemohon", ("Pengajuan ditolak Operasi", RED, True)],
              ["AOCH mencatat penyerahan PAS", "Pemohon", ("PAS diserahkan", TEAL, True)],
              ["AOCH mencatat pengembalian PAS", "Pemohon", ("PAS dikembalikan", TEAL, True)],
              ["Pengajuan ditandai selesai", "Pemohon", ("Layanan selesai", INK, True)],
          ],
          col_w=[4.70, 3.20, 4.33], row_h=0.26, body_size=8.5)

    panel(s, ML, 5.78, 6.00, 1.20, "Cara notifikasi dikirim", bullets([
        "In-app (lonceng notifikasi) bila pemohon punya akun; bila tidak, hanya e-mail.",
        "E-mail memakai subjek berawalan [EPermit]; kegagalan kirim tidak menghentikan alur.",
        "Notifikasi juga ditampilkan di menu Dashboard tiap peran: Commercial, Operation, dan AOCH.",
    ], size=8.5))

    panel(s, 6.78, 5.78, 6.00, 1.20, "Ringkasan PAS di dashboard petugas", bullets([
        "Tiga penghitung: sudah diserahkan / sedang berjalan / masa berlaku habis.",
        "Lencana “Berlaku 1 hari” dengan tanggal hari ini.",
        "AVSEC hanya mendapat ringkasan ini — tidak ada menu tulis.",
    ], size=8.5))
    return s


# ================================================================ SLIDE 12
def slide_status(prs):
    s = blank(prs)
    chrome(s, "ALUR STATUS", "Peta Status Pengajuan yang Benar-Benar Dipakai Kode", 12)

    chain = [
        ("DRAFT", BLUE), ("MENUNGGU_PEMBAYARAN", BLUE), ("BUKTI_TERUNGGAH", BLUE),
        ("MENUNGGU_OPERASI", PURPLE), ("PAS_TERBIT", PURPLE), ("DILAKSANAKAN", TEAL),
        ("SELESAI", INK),
    ]
    x = ML
    widths = [1.28, 2.02, 1.86, 1.92, 1.42, 1.86, 1.32]
    for (nama, color), w in zip(chain, widths):
        rrect(s, x, 1.48, w, 0.58, color, [(nama, 9.5, True, WHITE)],
              align=PP_ALIGN.CENTER, adj=0.12)
        x += w
        if x < 12.7:
            arrow_r(s, x - 0.02, 1.68, 0.16, 0.20)
            x += 0.16

    textbox(s, ML, 2.10, CW, 0.28,
            [[("Catatan: ", 9.5, True, RED),
              ("pengajuan yang lolos cek blacklist TIDAK PERNAH dibuat, sehingga tidak ada "
               "status “ditolak saat kirim”. Penolakan hanya terjadi di sisi Operasi.",
               9.5, False, GREY)]])

    table(s, ML, 2.52, CW, 2.94,
          ["PERPINTAHAN STATUS", "PELAKU", "KONDISI"],
          [
              ["DRAFT → MENUNGGU PEMBAYARAN", "Pemohon",
               "Form valid, seluruh pendamping & dokumen lengkap, tidak ada NIK/nama di daftar hitam."],
              ["MENUNGGU PEMBAYARAN → BUKTI TERUNGGAH", "Pemohon",
               "Bukti bayar diunggah saat status masih Menunggu Pembayaran."],
              ["BUKTI TERUNGGAH → MENUNGGU PEMBAYARAN", "Komersil",
               "Bukti dinilai tidak valid — pemohon diminta mengunggah ulang."],
              ["BUKTI TERUNGGAH → MENUNGGU OPERASI", "Komersil",
               "Bukti dinilai valid/lunas — lompat langsung, tanpa status “Sudah Dibayar”."],
              ["MENUNGGU OPERASI → BUKTI TERUNGGAH", "Komersil",
               "Validasi dibatalkan untuk koreksi — wajib divalidasi ulang."],
              ["* → SUDAH DIBAYAR", "Webhook penyedia",
               "Callback pembayaran otomatis. Tidak pernah diisi validasi manual."],
              ["MENUNGGU OPERASI / DIBAYAR / ACKNOWLEDGED AOCH → PAS TERBIT", "Operasi",
               "Tidak ada NIK atau nama di daftar hitam."],
              ["* → DITOLAK OPERASI", "Operasi",
               "Ada NIK di daftar hitam saat penerbitan, atau penolakan manual dengan alasan wajib."],
              ["PAS TERBIT → DILAKSANAKAN", "AOCH",
               "Syarat: serah terima dicatat (foto + TTD + tanggal & jam)."],
              ["ACKNOWLEDGED AOCH / SIAP DILAKSANAKAN → DILAKSANAKAN", "Operasi",
               "Penandaan manual; berlaku bila status bukan PAS Terbit."],
              ["DILAKSANAKAN → SELESAI", "Operasi",
               "Penandaan manual dari status Dilaksanakan."],
              ["* → SELESAI", "AOCH",
               "Syarat: kartu sudah DIKEMBALIKAN. Tidak ada syarat atas status pengajuan."],
          ],
          col_w=[4.55, 1.75, 5.93], row_h=0.22, body_size=8)

    panel(s, ML, 5.78, CW, 1.20, "Status yang ada di model tetapi tidak pernah dipakai kode", bullets([
        ("Tujuh status berikut ", "— DIAJUKAN, VERIFIKASI_KOMERSIL, DISETUJUI_KOMERSIL, "
         "DISETUJUI_OPERASI, REVISI_PEMOHON, SIAP_DILAKSANAKAN, DIBATALKAN — tidak pernah di-set "
         "oleh kode mana pun, hanya dibaca sebagai pembanding."),
        ("Konsekuensi: ", "langkah “Komersil meminta revisi pemohon” yang pernah ada di denah alur "
         "lama TIDAK ada di sistem sekarang. Pemohon yang memasang dokumen, Komersil yang "
         "memverifikasi, Operasi yang menerbitkan PAS; yang menolak hanya Operasi."),
    ], size=8.5), fill=SOFT)
    return s


# ================================================================ SLIDE 13
def slide_hak_akses(prs):
    s = blank(prs)
    chrome(s, "PEMBAGIAN TUGAS", "Hak Akses per Peran (seperti dijalankan kode)", 13)
    table(s, ML, 1.42, CW, 4.02,
          ["PERAN", "MENU & KEWENANGAN"],
          [
              [("PEMOHON", BLUE, True),
               "Form pengajuan publik (tanpa login) • mengunggah bukti bayar • melacak pengajuan "
               "sendiri bila punya akun • melihat daftar pengajuannya sendiri"],
              [("KOMERSIL", GREEN, True),
               "Verifikasi pengajuan & dokumen pendamping • melanjutkan ke Operasi • mengelola master "
               "layanan, tarif, dan jenis pembayaran • validasi bukti bayar (Valid / Tidak Valid / "
               "Koreksi) • membuat akun tim satu role"],
              [("OPERASI", PURPLE, True),
               "Daftar Operasi • menolak pengajuan dengan alasan wajib • menerbitkan PAS Visitor "
               "• menandai dilaksanakan & selesai • mengelola daftar hitam (tambah / edit / hapus)"],
              [("AOCH", TEAL, True),
               "Daftar AOCH • memasukkan nomor PAS per pendamping • mencatat serah terima fisik PAS "
               "(foto + tanda tangan elektronik) • mencatat pengembalian • menandai pengajuan selesai"],
              [("AVSEC", RED, True),
               "Hanya membaca: dashboard ringkasan masa berlaku PAS dan menu Verifikasi PAS. "
               "Tidak bisa mengubah status pengajuan, tidak bisa mencatat serah terima."],
              [("ADMINISTRATOR", INK, True),
               "Akses penuh — is_staff melewati semua pemeriksaan peran, termasuk modul AOCH. "
               "Ditambah Statistik, Laporan, ekspor CSV, dan Django admin."],
          ],
          col_w=[2.30, 9.93], row_h=0.62)

    panel(s, ML, 5.62, CW, 1.10, "Catatan", [
        [("Pemeriksaan peran memakai pola “role cocok ATAU is_staff”, sehingga satu akun "
          "administrator dapat menjalankan seluruh modul. Menu navigasi ditampilkan sesuai peran, "
          "tetapi pemeriksaan sesungguhnya tetap dilakukan di sisi server pada setiap tampilan "
          "dan setiap aksi POST.", 9.5, False, GREY),
         ],
    ], fill=SOFT)
    return s


# ================================================================ SLIDE 14
def slide_penutup(prs):
    s = blank(prs)
    rect(s, 0, 0, 13.3333, 7.5, INK)
    rect(s, 0, 0, 13.3333, 0.22, BLUE)
    textbox(s, 0.90, 1.70, 11.5, 0.90, [("RINGKASAN", 30, True, WHITE)])
    rect(s, 0.90, 2.62, 2.60, 0.06, BLUE)
    items = [
        ("Empat aktor bekerja di empat modul berbeda",
         "Pemohon → Komersil → Operasi → AOCH. Avsec hanya memverifikasi di luar alur."),
        ("Blacklist diperiksa dua kali dan ditegakkan di penerbitan PAS",
         "NIK di daftar hitam = pengajuan tidak pernah dibuat."),
        ("Bukti bayar punya tiga keputusan",
         "Valid melompat ke Menunggu Operasi; Tidak Valid mengembalikan; Koreksi membatalkan validasi."),
        ("AOCH memegang satu-satunya catatan serah terima fisik",
         "Foto + tanda tangan elektronik + tanggal & jam, untuk penyerahan maupun pengembalian."),
        ("Nomor PAS boleh dipakai ulang, masa berlaku tidak",
         "Nomor kembali bebas setelah kartu dikembalikan; hak pakai PAS hanya satu hari kalender."),
        ("Status di aplikasi berbeda dari denah alur lama",
         "Tujuh status pada denah lama sudah tidak dipakai sama sekali oleh kode."),
    ]
    y = 3.00
    for judul, isi in items:
        textbox(s, 0.90, y, 11.5, 0.55, [
            [(judul, 12, True, WHITE), ("  " + isi, 11, False, BORDER)],
        ], anchor=MSO_ANCHOR.TOP)
        y += 0.58
    textbox(s, 0.90, 6.55, 11.5, 0.40,
            [("Dokumen ini dihasilkan oleh generate_proses_bisnis.py — ubah skripnya, "
              "bukan file presentasinya, bila alur bisnis berubah.", 10, False, MUTED)])
    return s


# ================================================================ build
BUILDERS = [
    slide_cover,
    slide_aktor,
    slide_ringkasan,
    slide_fase1,
    slide_fase2,
    slide_fase3,
    slide_fase4,
    slide_aturan_serah,
    slide_nomor_masa,
    slide_verifikasi,
    slide_notifikasi,
    slide_status,
    slide_hak_akses,
    slide_penutup,
]


def build_pptx(path=OUT_PPTX):
    prs = new_deck()
    for fn in BUILDERS:
        fn(prs)
    prs.save(path)
    return path


def convert(source, ext, extra=None):
    outdir = os.path.dirname(source)
    cmd = ["soffice", "--headless", "--norestore", "--convert-to",
           ext + (":" + extra if extra else ""), "--outdir", outdir, source]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if res.returncode != 0:
        print(res.stdout, res.stderr, file=sys.stderr)
        raise SystemExit(f"konversi ke {ext} gagal")


def main():
    path = build_pptx()
    n = len(BUILDERS)
    print(f"OK  {path}  ({n} slide)")
    try:
        convert(path, "pdf")
        convert(path, "ppt", "Impress MS PowerPoint 2007 XML")
    except FileNotFoundError:
        print("WARN: soffice tidak ditemukan — .ppt/.pdf tidak dibuat ulang.", file=sys.stderr)
        return
    for ext in ("pdf", "ppt"):
        p = os.path.splitext(path)[0] + "." + ext
        print(("OK  " if os.path.exists(p) else "MISS ") + p)


if __name__ == "__main__":
    main()