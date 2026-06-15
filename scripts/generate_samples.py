"""Generate realistic SOE corporate-action submission packages (NOTA inputs).

Produces PDFs and DOCX into ../samples/ — three cases spanning the
delegation-of-authority tiers, in Bahasa Indonesia (with English glosses),
using real Indonesian SOE names and plausible figures. Two deliberate
defects are planted for the demo:
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


if __name__ == "__main__":
    print("Generating sample SOE corporate-action packages into", OUT)
    case_a()
    case_b()
    case_c()
    print("Done. Seed them with: backend/.venv/bin/python scripts/seed.py")
