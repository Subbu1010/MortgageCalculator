#!/usr/bin/env python3
"""Create a searchable PDF sample for ingestion (prefers ReportLab text; falls back to pypdf blank)."""

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "sample-documents" / "internal-policies" / "escrow-audit-checklist.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(str(out), pagesize=letter)
        y = letter[1] - 72
        lines = [
            "Meridian Escrow Audit Checklist (Sample)",
            "• Verify Cushion Computation Worksheet Approved",
            "• Confirm disbursement timelines meet RESPA / state overlays",
            "• Review surplus > $50 refundable bucket routing",
            "• Escheatment escalation per servicing note MST-SVC-014",
            "• SLA: Ledger reconciliation discrepancies escalated ≤ 48 business hours.",
        ]
        for line in lines:
            c.drawString(72, y, line)
            y -= 16
        c.save()
    except ImportError:
        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.add_metadata({"/Title": "Escrow Audit Checklist"})
        with out.open("wb") as fh:
            writer.write(fh)
    print(out)


if __name__ == "__main__":
    main()
