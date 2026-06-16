"""Generate realistic SOE corporate-action submission packages (NOTA inputs).

Produces PDFs and DOCX into ../samples/ — fourteen cases spanning the
delegation-of-authority tiers and the full corporate-action spectrum
(disposal, lease, investment, debt issuance, M&A, capex/PSN, write-off,
bank merger, controlling-stake acquisition, rights issue, spin-off, IPO,
dissolution), in Bahasa Indonesia (with English glosses), using real
Indonesian SOE names and plausible figures. Two deliberate defects are
planted for the demo:
  * a "13% vs 130%" arithmetic error in Case A's valuation annex
    (for the financial reconciliation agent),
  * a date/amount mismatch between Case A's submission and its draft board
    note (for the cross-document consistency checker).

Run: backend/.venv/bin/python scripts/generate_samples.py
Requires: reportlab, python-docx (in the backend venv).
"""
from pathlib import Path

from docx import Document
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parents[1] / "samples"
OUT.mkdir(exist_ok=True)

styles = getSampleStyleSheet()
H = ParagraphStyle("H", parent=styles["Heading1"], fontSize=13, spaceAfter=6)
SUB = ParagraphStyle("SUB", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
BODY = ParagraphStyle("BODY", parent=styles["Normal"], fontSize=10, leading=15, spaceAfter=6)
SMALL = ParagraphStyle("SMALL", parent=styles["Normal"], fontSize=8, textColor=colors.grey)


def pdf(name, title, subtitle, blocks):
    doc = SimpleDocTemplate(str(OUT / name), pagesize=A4,
                            topMargin=22 * mm, bottomMargin=18 * mm,
                            leftMargin=22 * mm, rightMargin=22 * mm)
    flow = [Paragraph(title, H), Paragraph(subtitle, SUB), Spacer(1, 8)]
    for b in blocks:
        if isinstance(b, Table):
            flow.append(b)
            flow.append(Spacer(1, 8))
        else:
            flow.append(Paragraph(b, BODY))
    flow.append(Spacer(1, 16))
    flow.append(Paragraph("Dokumen ini bersifat rahasia — Confidential, internal use only.", SMALL))
    doc.build(flow)
    print("  wrote", name)


def money(v):
    return "Rp" + f"{v:,}".replace(",", ".")


def table(rows, widths):
    t = Table(rows, colWidths=[w * mm for w in widths])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f62fe")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f4f4")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


# ── Case A — Asset disposal (board-of-directors tier, high value) ────────────
# PT Perkebunan Nusantara III divests a plantation estate. Valuation annex
# contains the planted 13%-vs-130% arithmetic error.
def case_a():
    pdf(
        "A1_surat_permohonan_divestasi.pdf",
        "SURAT PERMOHONAN PERSETUJUAN DIVESTASI ASET",
        "Request for Approval of Asset Divestment · PT Perkebunan Nusantara III (Persero)",
        [
            "Nomor: 042/PTPN-III/DIV/VI/2026 &nbsp;&nbsp; Tanggal: 3 Juni 2026",
            "Kepada Yth. Danantara Asset Management (DAM) — Direktorat Aset & Manajemen.",
            "<b>Perihal / Subject:</b> Permohonan persetujuan divestasi atas Kebun Sei Meranti "
            "(Hak Guna Usaha seluas 4.250 ha beserta pabrik kelapa sawit) di Kabupaten "
            "Labuhanbatu, Sumatera Utara.",
            "<b>Ringkasan permohonan / Request summary:</b> Perseroan mengajukan persetujuan "
            "untuk melepas aset perkebunan tersebut kepada pihak ketiga melalui mekanisme lelang "
            "terbuka. Nilai appraisal independen atas aset adalah <b>" + money(420_000_000_000) +
            "</b> (empat ratus dua puluh miliar Rupiah).",
            "<b>Dasar / Basis:</b> Nilai buku aset per 31 Desember 2025 sebesar " +
            money(371_000_000_000) + ". Penjualan pada nilai appraisal menghasilkan keuntungan "
            "atas pelepasan aset.",
            "<b>Counterparty:</b> Akan ditentukan melalui proses lelang terbuka (open auction).",
            "<b>Jangka waktu / Timeline:</b> Penyelesaian transaksi ditargetkan dalam 90 hari "
            "kerja setelah persetujuan.",
            "Hormat kami, Direksi PT Perkebunan Nusantara III (Persero).",
        ],
    )
    # Valuation annex — PLANTED ERROR: stated gain % says 130% but the real
    # gain is (420 - 371) / 371 = 13.2%. A reviewer/agent must catch this.
    rows = [
        ["Pos / Item", "Nilai / Value", "Catatan / Note"],
        ["Nilai buku (book value) per 31-12-2025", money(371_000_000_000), "Audited"],
        ["Nilai appraisal independen (2026)", money(420_000_000_000), "KJPP independen"],
        ["Keuntungan atas pelepasan (gain on disposal)", money(49_000_000_000), "appraisal − book"],
        ["Kenaikan terhadap nilai buku (% gain)", "130%", "lihat catatan kaki"],
    ]
    pdf(
        "A2_lampiran_valuasi.pdf",
        "LAMPIRAN VALUASI ASET",
        "Asset Valuation Annex · Kebun Sei Meranti · PTPN III",
        [
            "Ikhtisar valuasi atas aset yang diusulkan untuk divestasi:",
            table(rows, [70, 55, 45]),
            "<b>Catatan kaki / Footnote:</b> persentase kenaikan dihitung terhadap nilai buku. "
            "(Angka pada tabel di atas mengandung kemungkinan kekeliruan perhitungan persentase "
            "dan perlu diverifikasi.)",
        ],
    )
    # Draft board note (DOCX) — PLANTED INCONSISTENCY: different amount (Rp415bn)
    # and a different date vs the submission (Rp420bn, 3 Juni 2026).
    d = Document()
    d.add_heading("NOTA DINAS — Draf untuk Direksi (Board Note Draft)", level=1)
    d.add_paragraph("Hal: Usulan Divestasi Kebun Sei Meranti — PT Perkebunan Nusantara III")
    d.add_paragraph("Tanggal: 5 Juni 2026")
    d.add_paragraph(
        "Direksi diminta menyetujui pelepasan aset perkebunan Kebun Sei Meranti dengan "
        "nilai appraisal sebesar Rp415.000.000.000 (empat ratus lima belas miliar Rupiah) "
        "melalui lelang terbuka."
    )
    d.add_paragraph(
        "[BAGIAN PERTIMBANGAN / JUDGMENT — diisi oleh reviewer manusia]"
    )
    d.add_paragraph(
        "[BAGIAN REKOMENDASI / RECOMMENDATION — diisi oleh reviewer manusia]"
    )
    d.save(OUT / "A3_draf_nota_dinas.docx")
    print("  wrote A3_draf_nota_dinas.docx")


# ── Case B — Asset lease (below-threshold, low-risk, automated) ──────────────
def case_b():
    pdf(
        "B1_surat_permohonan_sewa.pdf",
        "SURAT PERMOHONAN PERSETUJUAN SEWA ASET",
        "Request for Approval of Asset Lease · PT Pelabuhan Indonesia (Persero)",
        [
            "Nomor: 118/PELINDO/SEWA/VI/2026 &nbsp;&nbsp; Tanggal: 4 Juni 2026",
            "<b>Perihal:</b> Permohonan persetujuan sewa atas gudang seluas 1.200 m² di "
            "Terminal Peti Kemas Surabaya untuk jangka waktu 12 bulan.",
            "<b>Nilai sewa / Lease value:</b> " + money(750_000_000) + " per tahun "
            "(tujuh ratus lima puluh juta Rupiah).",
            "<b>Counterparty:</b> PT Logistik Nusantara Jaya.",
            "<b>Ringkasan:</b> Pemanfaatan aset menganggur (idle asset utilization) untuk "
            "menghasilkan pendapatan sewa. Nilai di bawah ambang batas persetujuan dewan.",
            "Hormat kami, Direksi PT Pelabuhan Indonesia (Persero).",
        ],
    )


# ── Case C — Strategic investment (commissioners tier, highest value) ────────
def case_c():
    pdf(
        "C1_surat_permohonan_penyertaan_modal.pdf",
        "SURAT PERMOHONAN PERSETUJUAN PENYERTAAN MODAL",
        "Request for Approval of Equity Investment · PT Aviasi Pariwisata Indonesia (InJourney)",
        [
            "Nomor: 077/INJOURNEY/PMN/VI/2026 &nbsp;&nbsp; Tanggal: 2 Juni 2026",
            "<b>Perihal:</b> Permohonan persetujuan penyertaan modal pada usaha patungan "
            "(joint venture) pengembangan kawasan pariwisata terintegrasi.",
            "<b>Nilai investasi / Investment value:</b> " + money(1_200_000_000_000) +
            " (satu triliun dua ratus miliar Rupiah).",
            "<b>Struktur:</b> Penyertaan 40% ekuitas pada PT Destinasi Wisata Nusantara; "
            "sisanya dimiliki mitra strategis swasta.",
            "<b>Counterparty:</b> Konsorsium investor pariwisata (nama dirahasiakan pada "
            "tahap ini).",
            "<b>Dasar strategis:</b> Selaras dengan mandat pengembangan sektor pariwisata "
            "prioritas. Eksposur regulasi: sektor pariwisata & pertanahan.",
            "Hormat kami, Direksi PT Aviasi Pariwisata Indonesia.",
        ],
    )
    rows = [
        ["Parameter", "Nilai / Value"],
        ["Total nilai proyek (project size)", money(3_000_000_000_000)],
        ["Penyertaan DAM/SOE (equity stake 40%)", money(1_200_000_000_000)],
        ["Proyeksi IRR (projected)", "14,5%"],
        ["Periode / Holding period", "7 tahun"],
    ]
    pdf(
        "C2_tesis_investasi.pdf",
        "RINGKASAN TESIS INVESTASI",
        "Investment Thesis Summary · JV Pariwisata · InJourney",
        ["Parameter utama investasi:", table(rows, [90, 70])],
    )


# ── Case D — Global bond issuance (debt, Dewan Pengawas tier) ────────────────
def case_d():
    pdf(
        "D1_surat_permohonan_obligasi.pdf",
        "SURAT PERMOHONAN PERSETUJUAN PENERBITAN OBLIGASI GLOBAL",
        "Request for Approval of Global Bond Issuance · PT PLN (Persero)",
        [
            "Nomor: 205/PLN/KEU/VI/2026 &nbsp;&nbsp; Tanggal: 6 Juni 2026",
            "<b>Perihal:</b> Permohonan persetujuan penerbitan obligasi global (global notes) "
            "untuk pembiayaan kembali (refinancing) utang jatuh tempo dan belanja modal "
            "jaringan transmisi.",
            "<b>Nilai penerbitan / Issuance size:</b> " + money(4_800_000_000_000) +
            " (setara USD 300 juta).",
            "<b>Tenor:</b> 10 tahun. <b>Kupon indikatif:</b> 5,8% per tahun. "
            "<b>Penjamin emisi:</b> sindikasi bank internasional.",
            "<b>Penggunaan dana / Use of proceeds:</b> 60% refinancing, 40% belanja modal "
            "transmisi & gardu induk.",
            "<b>Dasar:</b> Termasuk kategori penerbitan utang strategis — memerlukan "
            "persetujuan Dewan Pengawas dan koordinasi dengan Kementerian Keuangan.",
            "Hormat kami, Direksi PT PLN (Persero).",
        ],
    )
    rows = [
        ["Parameter", "Nilai / Value"],
        ["Nilai penerbitan (issuance)", money(4_800_000_000_000)],
        ["Tenor", "10 tahun"],
        ["Kupon indikatif (coupon)", "5,8%"],
        ["Rasio refinancing : capex", "60% : 40%"],
    ]
    pdf(
        "D2_term_sheet.pdf",
        "RINGKASAN KETENTUAN (TERM SHEET)",
        "Indicative Term Sheet · Global Notes · PT PLN (Persero)",
        ["Ketentuan utama penerbitan:", table(rows, [90, 70])],
    )


# ── Case E — Controlling-stake acquisition (M&A, Dewan Pengawas tier) ─────────
def case_e():
    pdf(
        "E1_surat_permohonan_akuisisi.pdf",
        "SURAT PERMOHONAN PERSETUJUAN AKUISISI SAHAM PENGENDALI",
        "Request for Approval of Controlling-Stake Acquisition · PT Mineral Industri Indonesia (MIND ID)",
        [
            "Nomor: 061/MINDID/MNA/VI/2026 &nbsp;&nbsp; Tanggal: 5 Juni 2026",
            "<b>Perihal:</b> Permohonan persetujuan akuisisi 51% saham pengendali pada "
            "PT Nikel Sulawesi Lestari guna mengamankan rantai pasok bahan baku baterai (nikel).",
            "<b>Nilai transaksi / Deal value:</b> " + money(4_200_000_000_000) +
            " (empat triliun dua ratus miliar Rupiah).",
            "<b>Struktur:</b> Akuisisi 51% melalui kombinasi kas dan penerbitan saham baru. "
            "Target menjadi entitas anak terkonsolidasi.",
            "<b>Counterparty:</b> Pemegang saham mayoritas eksisting PT Nikel Sulawesi Lestari.",
            "<b>Dasar strategis:</b> Hilirisasi mineral (downstreaming) sesuai mandat. "
            "Lintas-klaster M&A — memerlukan persetujuan Dewan Pengawas; tunduk pada "
            "persetujuan KPPU (merger control).",
            "Hormat kami, Direksi PT Mineral Industri Indonesia (MIND ID).",
        ],
    )


# ── Case F — Refinery capex / National Strategic Project (President tier) ─────
def case_f():
    pdf(
        "F1_surat_permohonan_capex.pdf",
        "SURAT PERMOHONAN PERSETUJUAN BELANJA MODAL (CAPEX)",
        "Request for Approval of Capital Expenditure · PT Pertamina (Persero)",
        [
            "Nomor: 312/PTM/INV/VI/2026 &nbsp;&nbsp; Tanggal: 1 Juni 2026",
            "<b>Perihal:</b> Permohonan persetujuan belanja modal pembangunan dan perluasan "
            "kompleks kilang (refinery development) di Tuban, Jawa Timur.",
            "<b>Nilai proyek / Project value:</b> " + money(32_000_000_000_000) +
            " (tiga puluh dua triliun Rupiah), multi-tahun.",
            "<b>Status:</b> Termasuk Proyek Strategis Nasional (PSN). Berdampak fiskal masif — "
            "memerlukan persetujuan Presiden Republik Indonesia.",
            "<b>Manfaat:</b> Menambah kapasitas pengolahan 100.000 barel/hari; mengurangi "
            "impor BBM dan memperkuat ketahanan energi nasional.",
            "<b>Jangka waktu konstruksi:</b> 48 bulan.",
            "Hormat kami, Direksi PT Pertamina (Persero).",
        ],
    )
    rows = [
        ["Parameter", "Nilai / Value"],
        ["Nilai proyek (project size)", money(32_000_000_000_000)],
        ["Tambahan kapasitas", "100.000 barel/hari"],
        ["Status", "Proyek Strategis Nasional (PSN)"],
        ["Jangka waktu konstruksi", "48 bulan"],
    ]
    pdf(
        "F2_ringkasan_proyek.pdf",
        "RINGKASAN PROYEK",
        "Project Summary · Refinery Development Tuban · PT Pertamina (Persero)",
        ["Parameter utama proyek:", table(rows, [90, 70])],
    )


# ── Case G — Asset write-off (below threshold, CEO tier, automated-leaning) ───
def case_g():
    pdf(
        "G1_surat_permohonan_penghapusan.pdf",
        "SURAT PERMOHONAN PERSETUJUAN PENGHAPUSAN ASET",
        "Request for Approval of Asset Write-off · PT Pelayaran Nasional Indonesia (Pelni)",
        [
            "Nomor: 089/PELNI/HAPUS/VI/2026 &nbsp;&nbsp; Tanggal: 7 Juni 2026",
            "<b>Perihal:</b> Permohonan persetujuan penghapusan (write-off) atas 3 unit kapal "
            "tua yang sudah tidak laik operasi dan habis masa ekonomisnya.",
            "<b>Nilai buku tersisa / Residual book value:</b> " + money(12_000_000_000) +
            " (dua belas miliar Rupiah).",
            "<b>Tindak lanjut:</b> Penghapusan dari neraca diikuti penjualan besi tua (scrap) "
            "melalui lelang. Estimasi nilai scrap " + money(2_500_000_000) + ".",
            "<b>Dasar:</b> Nilai di bawah ambang batas strategis — kewenangan persetujuan CEO "
            "Danantara; tetap dicatat dalam audit trail.",
            "Hormat kami, Direksi PT Pelayaran Nasional Indonesia (Pelni).",
        ],
    )


# ── Case H — Bank merger / consolidation (President tier, systemic) ───────────
def case_h():
    pdf(
        "H1_surat_permohonan_merger.pdf",
        "SURAT PERMOHONAN PERSETUJUAN MERGER (KONSOLIDASI)",
        "Request for Approval of Merger · Konsolidasi Bank Syariah BUMN",
        [
            "Nomor: 003/DANA/MRG/VI/2026 &nbsp;&nbsp; Tanggal: 8 Juni 2026",
            "<b>Perihal:</b> Permohonan persetujuan penggabungan (merger) tiga bank syariah "
            "milik negara — PT Bank BRI Syariah Tbk, PT Bank Syariah Mandiri, dan "
            "PT Bank BNI Syariah — menjadi satu entitas, PT Bank Syariah Indonesia Tbk (BSI).",
            "<b>Nilai aset gabungan / Combined assets:</b> " + money(240_000_000_000_000) +
            " (dua ratus empat puluh triliun Rupiah).",
            "<b>Struktur:</b> Bank Syariah Mandiri sebagai entitas yang menerima penggabungan; "
            "BRI Syariah dan BNI Syariah membubarkan diri tanpa likuidasi.",
            "<b>Dasar strategis:</b> Membentuk bank syariah berskala besar yang kompetitif "
            "secara global. Berdampak sistemik pada sektor keuangan — memerlukan persetujuan "
            "Presiden Republik Indonesia serta koordinasi OJK.",
            "Hormat kami, Komite Konsolidasi Perbankan Syariah BUMN.",
        ],
    )


# ── Case I — Controlling-stake acquisition Freeport (President tier) ──────────
def case_i():
    pdf(
        "I1_surat_permohonan_akuisisi_freeport.pdf",
        "SURAT PERMOHONAN PERSETUJUAN AKUISISI SAHAM PENGENDALI",
        "Request for Approval of Controlling-Stake Acquisition · MIND ID — PT Freeport Indonesia",
        [
            "Nomor: 071/MINDID/MNA/VI/2026 &nbsp;&nbsp; Tanggal: 4 Juni 2026",
            "<b>Perihal:</b> Permohonan persetujuan akuisisi saham untuk meningkatkan "
            "kepemilikan Pemerintah menjadi 51% (pengendali) pada PT Freeport Indonesia.",
            "<b>Nilai transaksi / Deal value:</b> " + money(56_000_000_000_000) +
            " (setara USD 3,85 miliar).",
            "<b>Struktur:</b> Pembelian saham divestasi dari Freeport-McMoRan; mengalihkan "
            "pengendalian tambang Grasberg kepada negara.",
            "<b>Dasar strategis:</b> Penguasaan sumber daya mineral strategis nasional. "
            "Mengubah kepemilikan mayoritas negara — memerlukan persetujuan "
            "Presiden Republik Indonesia.",
            "Hormat kami, Direksi PT Mineral Industri Indonesia (MIND ID).",
        ],
    )


# ── Case J — Rights issue to fund an acquisition (Dewan Pengawas tier) ────────
def case_j():
    pdf(
        "J1_surat_permohonan_rights_issue.pdf",
        "SURAT PERMOHONAN PERSETUJUAN PENERBITAN SAHAM TERBATAS (RIGHTS ISSUE)",
        "Request for Approval of Rights Issue (HMETD) · PT Semen Indonesia (Persero) Tbk",
        [
            "Nomor: 145/SIG/HMETD/VI/2026 &nbsp;&nbsp; Tanggal: 6 Juni 2026",
            "<b>Perihal:</b> Permohonan persetujuan penerbitan saham dengan Hak Memesan Efek "
            "Terlebih Dahulu (rights issue) untuk mendanai akuisisi PT Semen Baturaja Tbk.",
            "<b>Nilai penerbitan / Issuance size:</b> " + money(3_800_000_000_000) +
            " (tiga triliun delapan ratus miliar Rupiah).",
            "<b>Tujuan penggunaan dana:</b> Akuisisi pengendalian PT Semen Baturaja Tbk guna "
            "sinergi rantai pasok dan operasional pada klaster semen.",
            "<b>Dampak:</b> Dilusi terkendali; negara mempertahankan kepemilikan mayoritas. "
            "Aksi pasar modal strategis — memerlukan persetujuan Dewan Pengawas dan OJK.",
            "Hormat kami, Direksi PT Semen Indonesia (Persero) Tbk.",
        ],
    )


# ── Case K — Spin-off of a business unit (Dewan Pengawas tier) ────────────────
def case_k():
    pdf(
        "K1_surat_permohonan_spinoff.pdf",
        "SURAT PERMOHONAN PERSETUJUAN PEMISAHAN UNIT USAHA (SPIN-OFF)",
        "Request for Approval of Business Spin-off · PT Telkom Indonesia (Persero) Tbk",
        [
            "Nomor: 222/TLKM/SPO/VI/2026 &nbsp;&nbsp; Tanggal: 3 Juni 2026",
            "<b>Perihal:</b> Permohonan persetujuan pemisahan (spin-off) lini bisnis pusat data "
            "(data center) menjadi entitas anak tersendiri, PT Sigma Cipta Caraka (Telkomsigma).",
            "<b>Nilai aset yang dipisahkan / Carve-out asset value:</b> " +
            money(4_500_000_000_000) + " (empat triliun lima ratus miliar Rupiah).",
            "<b>Dasar strategis:</b> Membuka nilai bisnis khusus (unlock specialized value), "
            "menarik mitra strategis, dan mempercepat ekspansi infrastruktur pusat data.",
            "<b>Dampak:</b> Restrukturisasi korporasi — memerlukan persetujuan Dewan Pengawas.",
            "Hormat kami, Direksi PT Telkom Indonesia (Persero) Tbk.",
        ],
    )


# ── Case L — IPO on the IDX (President tier, large raise) ─────────────────────
def case_l():
    pdf(
        "L1_surat_permohonan_ipo.pdf",
        "SURAT PERMOHONAN PERSETUJUAN PENAWARAN UMUM PERDANA (IPO)",
        "Request for Approval of Initial Public Offering · PT Pertamina Geothermal Energy Tbk",
        [
            "Nomor: 058/PGE/IPO/VI/2026 &nbsp;&nbsp; Tanggal: 2 Juni 2026",
            "<b>Perihal:</b> Permohonan persetujuan Penawaran Umum Perdana (IPO) saham pada "
            "Bursa Efek Indonesia (IDX) untuk pendanaan ekspansi infrastruktur energi hijau.",
            "<b>Target dana / Proceeds target:</b> " + money(9_000_000_000_000) +
            " (sembilan triliun Rupiah).",
            "<b>Struktur:</b> Pelepasan saham minoritas ke publik; negara/holding tetap "
            "pengendali mayoritas. Pencatatan saham di IDX.",
            "<b>Dasar strategis:</b> Pendanaan pengembangan panas bumi (geothermal) untuk "
            "transisi energi. Aksi pasar modal berskala besar — memerlukan persetujuan "
            "Presiden Republik Indonesia dan OJK.",
            "Hormat kami, Direksi PT Pertamina Geothermal Energy Tbk.",
        ],
    )


# ── Case M — Dissolution / liquidation (Dewan Pengawas tier) ──────────────────
def case_m():
    pdf(
        "M1_surat_permohonan_pembubaran.pdf",
        "SURAT PERMOHONAN PERSETUJUAN PEMBUBARAN (LIKUIDASI)",
        "Request for Approval of Dissolution / Liquidation · PT Merpati Nusantara Airlines (Persero)",
        [
            "Nomor: 011/MNA/LIK/VI/2026 &nbsp;&nbsp; Tanggal: 9 Juni 2026",
            "<b>Perihal:</b> Permohonan persetujuan pembubaran dan likuidasi perseroan yang "
            "telah lama tidak beroperasi (non-performing) guna membersihkan portofolio negara.",
            "<b>Nilai penyelesaian kewajiban / Settlement value:</b> " +
            money(1_200_000_000_000) + " (satu triliun dua ratus miliar Rupiah).",
            "<b>Tindak lanjut:</b> Penunjukan tim likuidasi, penyelesaian kewajiban kepada "
            "kreditur dan eks-karyawan, serta penjualan aset tersisa.",
            "<b>Dasar:</b> Pembubaran entitas BUMN — memerlukan persetujuan Dewan Pengawas "
            "dan koordinasi dengan Kementerian Keuangan.",
            "Hormat kami, Tim Restrukturisasi Portofolio BUMN.",
        ],
    )


# ── Case N — Strategic investment / factory expansion, with full collateral ──
# Mirrors a real layered-review Nota Dinas: a main request letter PLUS three
# mandatory attachments (Feasibility Study, Kajian Hukum, Surat Rekomendasi
# Dekom). Routed to the Investment & Risk committees (SOP-006, Dewan Pengawas).
def case_n():
    # --- N1: the Nota Dinas (primary submission letter) ---
    meta_rows = [
        ["Field", "Keterangan"],
        ["Kepada Yth.", "Kepala Danantara u.p. Managing Director Investment Sektoral"],
        ["Dari", "Direktur Utama PT Krakatau Steel (Persero) Tbk"],
        ["Sifat", "Segera / Rahasia"],
        ["Lampiran", "3 (tiga) Berkas — Feasibility Study, Kajian Hukum, Surat Rekomendasi Dekom"],
        ["Perihal", "Permohonan Persetujuan Rencana Investasi Strategis Ekspansi Pabrik Baja Lapis Unit 2"],
        ["Tanggal", "16 Juni 2026"],
    ]
    fin_rows = [
        ["Indikator finansial / Financial indicator", "Nilai / Value"],
        ["Total kebutuhan dana (total funding)", money(850_000_000_000)],
        ["Kas internal (30%)", money(255_000_000_000)],
        ["Sindikasi Bank Himbara (70%)", money(595_000_000_000)],
        ["Internal Rate of Return (IRR)", "14,5% (di atas WACC 9,5%)"],
        ["Net Present Value (NPV)", "Positif " + money(120_000_000_000)],
        ["Payback Period", "5,8 tahun"],
    ]
    pdf(
        "N1_nota_dinas.pdf",
        "NOTA DINAS — Nomor: ND-0412/KS/VI/2026",
        "PT Krakatau Steel (Persero) Tbk → Danantara · Segera / Rahasia · 16 Juni 2026",
        [
            table(meta_rows, [42, 128]),
            "<b>I. LATAR BELAKANG DAN DASAR HUKUM.</b> Dasar internal: Anggaran Dasar "
            "Perseroan Pasal 12 (kewenangan Direksi dan batas nilai transaksi yang "
            "memerlukan persetujuan Pemegang Saham) dan RKAP Tahun Buku 2026. Dasar "
            "eksternal: Peraturan Pemerintah tentang pengalihan hak Pemegang Saham Negara "
            "kepada Danantara. Kondisi eksisting: utilisasi pabrik telah mencapai 95% "
            "sementara permintaan pasar domestik dan regional diproyeksikan tumbuh 12% "
            "per tahun hingga 2030.",
            "<b>II. MAKSUD DAN TUJUAN.</b> Memohon persetujuan tertulis atas rencana "
            "investasi pembangunan lini produksi baru (Pabrik Baja Lapis Unit 2) dengan "
            "total nilai investasi " + money(850_000_000_000) + ". Tujuan: meningkatkan "
            "kapasitas produksi tahunan 40%, menangkap pasar ekspor Asia Tenggara, dan "
            "menurunkan biaya operasional 15% melalui digitalisasi.",
            "<b>III. KAJIAN KELAYAKAN KOMERSIAL DAN ASPEK FINANSIAL</b> (di-review oleh "
            "MD Investment & MD Finance Danantara). Berdasarkan Feasibility Study yang "
            "disusun bersama Konsultan Independen PT Daya Makara Konsultan:",
            table(fin_rows, [100, 70]),
            "<b>IV. MANAJEMEN RISIKO DAN KEPATUHAN (ESG)</b> (di-review oleh MD Risk & "
            "Sustainability serta MD Legal Danantara). Risiko bahan baku dimitigasi "
            "melalui kontrak pasokan jangka panjang 5 tahun; risiko likuiditas "
            "diselaraskan dengan arus kas (grace period 2 tahun). ESG: target reduksi "
            "emisi karbon 20% dan sistem pengolahan limbah mandiri (Zero Waste).",
            "<b>V. REKOMENDASI DEWAN KOMISARIS.</b> Sesuai Surat Dewan Komisaris Nomor "
            "S-027/DEKOM-KS/VI/2026 tanggal 10 Juni 2026, Dewan Komisaris memberikan "
            "Rekomendasi Penuh kepada Direksi untuk mengeksekusi dan mengajukan "
            "persetujuan akhir ke Danantara.",
            "<b>VI. KESIMPULAN DAN PERMOHONAN PERSETUJUAN.</b> Aksi korporasi ekspansi "
            "pabrik ini layak secara finansial, risikonya termitigasi, dan sejalan "
            "dengan fokus value creation Danantara. Kami memohon Surat Persetujuan "
            "Prinsip atas Rencana Investasi Ekspansi Pabrik.",
            "Hormat kami, Direksi PT Krakatau Steel (Persero) Tbk. "
            "Tembusan: CIO Danantara; MD Risk & Sustainability Danantara; Dewan "
            "Komisaris Perseroan.",
        ],
    )
    # --- N2: Feasibility Study (collateral) ---
    fs_rows = [
        ["Parameter", "Nilai / Value"],
        ["Total nilai investasi (project size)", money(850_000_000_000)],
        ["Tambahan kapasitas produksi", "+40% per tahun"],
        ["Efisiensi biaya operasional", "-15%"],
        ["IRR proyek", "14,5%"],
        ["WACC perusahaan", "9,5%"],
        ["NPV", "Positif " + money(120_000_000_000)],
        ["Payback period", "5,8 tahun"],
        ["Proyeksi pertumbuhan permintaan", "12% per tahun s.d. 2030"],
    ]
    pdf(
        "N2_feasibility_study.pdf",
        "FEASIBILITY STUDY (KAJIAN KELAYAKAN)",
        "Ekspansi Pabrik Baja Lapis Unit 2 · Konsultan Independen PT Daya Makara Konsultan",
        [
            "Ringkasan kelayakan komersial dan finansial atas rencana pembangunan "
            "Pabrik Baja Lapis Unit 2:",
            table(fs_rows, [100, 70]),
            "<b>Kesimpulan:</b> Proyek layak dilaksanakan — IRR (14,5%) berada di atas "
            "WACC (9,5%), NPV positif, dan payback period dalam batas wajar industri. "
            "Struktur pendanaan 30% kas internal dan 70% sindikasi Bank Himbara.",
        ],
    )
    # --- N3: Kajian Hukum (legal review collateral) ---
    pdf(
        "N3_kajian_hukum.pdf",
        "KAJIAN HUKUM (LEGAL REVIEW)",
        "Aspek Hukum Rencana Ekspansi Pabrik · Divisi Hukum PT Krakatau Steel (Persero) Tbk",
        [
            "<b>1. Status lahan:</b> Seluruh lahan pembangunan unit baru merupakan milik "
            "sah Perseroan dengan sertifikat Hak Guna Bangunan (HGB) aktif dan bebas "
            "dari sengketa hukum.",
            "<b>2. Kewenangan korporasi:</b> Rencana investasi sesuai Anggaran Dasar "
            "Pasal 12; nilai transaksi melampaui batas kewenangan Direksi sehingga "
            "memerlukan persetujuan Pemegang Saham (Danantara).",
            "<b>3. Kepatuhan eksternal:</b> Sesuai Peraturan Pemerintah tentang "
            "pengalihan hak Pemegang Saham Negara kepada Danantara; tidak terdapat "
            "hambatan regulasi sektoral atas pembangunan lini produksi baru.",
            "<b>4. Perizinan:</b> Izin lingkungan (AMDAL) dan izin usaha industri dalam "
            "proses perpanjangan; tidak ada perkara litigasi yang membahayakan proyek.",
            "<b>Kesimpulan:</b> Tidak ditemukan halangan hukum yang menghalangi "
            "pelaksanaan aksi korporasi ini sepanjang persetujuan Pemegang Saham diperoleh.",
        ],
    )
    # --- N4: Surat Rekomendasi Dewan Komisaris (collateral) ---
    pdf(
        "N4_surat_rekomendasi_dekom.pdf",
        "SURAT REKOMENDASI DEWAN KOMISARIS",
        "Nomor: S-027/DEKOM-KS/VI/2026 · Tanggal: 10 Juni 2026",
        [
            "Kepada Yth. Direksi PT Krakatau Steel (Persero) Tbk.",
            "<b>Perihal:</b> Rekomendasi atas Rencana Investasi Strategis Ekspansi "
            "Pabrik Baja Lapis Unit 2.",
            "Setelah melakukan peninjauan dan pengawasan atas rencana investasi senilai "
            + money(850_000_000_000) + ", termasuk kajian kelayakan dan mitigasi risiko, "
            "Dewan Komisaris menilai bahwa rencana ini layak secara strategis dan "
            "finansial serta memiliki struktur risiko yang termitigasi dengan baik.",
            "Dengan ini Dewan Komisaris memberikan <b>Rekomendasi Penuh</b> kepada "
            "Direksi untuk mengeksekusi rencana tersebut dan mengajukan permohonan "
            "persetujuan akhir kepada Danantara selaku Pemegang Saham.",
            "Hormat kami, Dewan Komisaris PT Krakatau Steel (Persero) Tbk.",
        ],
    )


# ── Standardized NOTA cover sheets (PRD addendum: mandatory fields + disclaimer) ─
# One per case. Bilingual mandatory-field table + completeness checklist + the
# mandatory AI-assistance disclaimer + human sign-off blocks (left blank — the
# judgment/approval is recorded by people, never pre-filled by the system).
APPROVAL_LABEL = {
    "none": "Tidak memerlukan persetujuan (di bawah ambang batas) / Not required",
    "ceo": "CEO Danantara (Level 1)",
    "dewan_pengawas": "Dewan Pengawas (Level 2)",
    "president": "Presiden Republik Indonesia (Level 3)",
}

# (filename, ref, requesting_unit, cluster, action, value, classification, sop, approval)
COVERS = [
    ("A0_lembar_pengantar.pdf", "042/PTPN-III/DIV/VI/2026", "PT Perkebunan Nusantara III (Persero)",
     "Perkebunan", "Divestasi aset / Asset disposal", 420_000_000_000, "Confidential / Rahasia",
     "SOP-DAM-001", "ceo"),
    ("B0_lembar_pengantar.pdf", "118/PELINDO/SEWA/VI/2026", "PT Pelabuhan Indonesia (Persero)",
     "Logistik", "Sewa aset / Asset lease", 750_000_000, "Internal", "SOP-DAM-003", "none"),
    ("C0_lembar_pengantar.pdf", "077/INJOURNEY/PMN/VI/2026", "PT Aviasi Pariwisata Indonesia (InJourney)",
     "Pariwisata", "Penyertaan modal / Equity investment", 1_200_000_000_000, "Restricted / Terbatas",
     "SOP-DAM-002", "dewan_pengawas"),
    ("D0_lembar_pengantar.pdf", "205/PLN/KEU/VI/2026", "PT PLN (Persero)",
     "Energi", "Penerbitan obligasi global / Debt issuance", 4_800_000_000_000, "Confidential / Rahasia",
     "SOP-DAM-004", "dewan_pengawas"),
    ("E0_lembar_pengantar.pdf", "061/MINDID/MNA/VI/2026", "PT Mineral Industri Indonesia (MIND ID)",
     "Mineral & Batu Bara", "Akuisisi saham pengendali / Acquisition", 4_200_000_000_000,
     "Restricted / Terbatas", "SOP-DAM-005", "dewan_pengawas"),
    ("F0_lembar_pengantar.pdf", "312/PTM/INV/VI/2026", "PT Pertamina (Persero)",
     "Energi", "Belanja modal (PSN) / Capital expenditure", 32_000_000_000_000, "Confidential / Rahasia",
     "SOP-DAM-006", "president"),
    ("G0_lembar_pengantar.pdf", "089/PELNI/HAPUS/VI/2026", "PT Pelayaran Nasional Indonesia (Pelni)",
     "Logistik", "Penghapusan aset / Asset write-off", 12_000_000_000, "Internal", "SOP-DAM-007", "ceo"),
    ("H0_lembar_pengantar.pdf", "003/DANA/MRG/VI/2026", "Komite Konsolidasi Bank Syariah BUMN",
     "Jasa Keuangan", "Merger / konsolidasi / Merger", 240_000_000_000_000, "Restricted / Terbatas",
     "SOP-DAM-005", "president"),
    ("I0_lembar_pengantar.pdf", "071/MINDID/MNA/VI/2026", "PT Mineral Industri Indonesia (MIND ID)",
     "Mineral & Batu Bara", "Akuisisi saham pengendali / Acquisition", 56_000_000_000_000,
     "Restricted / Terbatas", "SOP-DAM-005", "president"),
    ("J0_lembar_pengantar.pdf", "145/SIG/HMETD/VI/2026", "PT Semen Indonesia (Persero) Tbk",
     "Industri & Manufaktur", "Rights issue (HMETD)", 3_800_000_000_000, "Confidential / Rahasia",
     "SOP-DAM-008", "dewan_pengawas"),
    ("K0_lembar_pengantar.pdf", "222/TLKM/SPO/VI/2026", "PT Telkom Indonesia (Persero) Tbk",
     "Telekomunikasi & Media", "Spin-off unit usaha / Spin-off", 4_500_000_000_000,
     "Confidential / Rahasia", "SOP-DAM-005", "dewan_pengawas"),
    ("L0_lembar_pengantar.pdf", "058/PGE/IPO/VI/2026", "PT Pertamina Geothermal Energy Tbk",
     "Energi", "Penawaran umum perdana (IPO)", 9_000_000_000_000, "Confidential / Rahasia",
     "SOP-DAM-008", "president"),
    ("M0_lembar_pengantar.pdf", "011/MNA/LIK/VI/2026", "Tim Restrukturisasi Portofolio BUMN",
     "Logistik", "Pembubaran / likuidasi / Dissolution", 1_200_000_000_000, "Restricted / Terbatas",
     "SOP-DAM-009", "dewan_pengawas"),
    ("N0_lembar_pengantar.pdf", "ND-0412/KS/VI/2026", "PT Krakatau Steel (Persero) Tbk",
     "Industri & Manufaktur", "Investasi strategis / ekspansi pabrik (CAPEX)", 850_000_000_000,
     "Confidential / Rahasia", "SOP-DAM-006", "dewan_pengawas"),
]

DISCLAIMER = (
    "<b>Disclaimer:</b> Bagian deskriptif NOTA ini dapat disusun dengan bantuan "
    "kecerdasan buatan (AI-assisted) dan wajib bersumber pada dokumen yang "
    "tercantum (source-grounded). Seluruh pertimbangan, analisis, dan "
    "rekomendasi merupakan penilaian manusia. Persetujuan dan tanda tangan di "
    "bawah ini sah hanya bila dibubuhkan oleh pejabat berwenang. / The "
    "descriptive sections may be AI-assisted and must be grounded in the listed "
    "sources; all judgment and recommendations are human; sign-offs are valid "
    "only when affixed by the authorized officer."
)


def cover_sheet(spec):
    fname, ref, unit, cluster, action, value, classification, sop, approval = spec
    fields = [
        ["Field", "Value"],
        ["Nomor NOTA / Reference", ref],
        ["BPI / Holding", "Danantara Asset Management (DAM)"],
        ["Unit pengusul / Requesting unit", unit],
        ["Klaster / Cluster", cluster],
        ["Jenis aksi korporasi / Action type", action],
        ["Nilai transaksi / Transaction value", money(value)],
        ["Klasifikasi data / Classification", classification],
        ["SOP terkait / Applicable SOP", sop],
        ["Level persetujuan / Approval level", APPROVAL_LABEL[approval]],
    ]
    checklist = [
        ["Kelengkapan dokumen / Completeness checklist", "Status"],
        ["Surat permohonan / Request letter", "Terlampir / Attached"],
        ["Dokumen pendukung (valuasi, term sheet, dll.)", "Terlampir / Attached"],
        ["Kajian hukum / Legal review", "Menunggu reviewer / Pending"],
        ["Kajian risiko / Risk assessment", "Menunggu reviewer / Pending"],
    ]
    pdf(
        fname,
        "LEMBAR PENGANTAR NOTA — NOTA COVER SHEET",
        "Danantara Asset Management (DAM) · Governance Intake",
        [
            "Lembar pengantar ini merangkum data wajib (mandatory fields) atas "
            "permohonan aksi korporasi berikut:",
            table(fields, [75, 95]),
            "<b>Daftar periksa kelengkapan / Completeness checklist:</b>",
            table(checklist, [110, 60]),
            DISCLAIMER,
            "<b>Tanda tangan / Sign-off:</b> Penyusun (Drafter): ____________  ·  "
            "Pemeriksa (Reviewer): ____________  ·  Pemberi persetujuan (Approver): "
            "____________",
        ],
    )


if __name__ == "__main__":
    print("Generating sample SOE corporate-action packages into", OUT)
    for fn in (case_a, case_b, case_c, case_d, case_e, case_f, case_g,
               case_h, case_i, case_j, case_k, case_l, case_m, case_n):
        fn()
    for spec in COVERS:
        cover_sheet(spec)
    print("Done. Seed them with: backend/.venv/bin/python scripts/seed.py")
