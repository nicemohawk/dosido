"""Generate printable badge PDFs with QR codes (Avery 5395 compatible)."""

from __future__ import annotations

import json
import sys

import qrcode
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# Avery 5395 name badge layout (2 columns x 4 rows per page)
BADGE_WIDTH = 3.5 * inch
BADGE_HEIGHT = 2.25 * inch
LEFT_MARGIN = 0.5 * inch
TOP_MARGIN = 0.75 * inch
COL_GAP = 0.25 * inch
ROW_GAP = 0.0


def make_qr_image(url: str, size: int = 120) -> str:
    """Generate a QR code image and return the temp file path."""
    qr = qrcode.QRCode(version=1, box_size=4, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    tmp_path = f"/tmp/qr_{hash(url)}.png"
    img.save(tmp_path)
    return tmp_path


def generate_attendee_badges(
    attendees_path: str = "data/enriched_attendees.json",
    output_path: str = "badges_attendees.pdf",
    base_url: str = "http://localhost:8000",
    event_slug: str = "climate-week-2026",
) -> None:
    """Generate badge PDF for pre-registered attendees."""
    with open(attendees_path) as f:
        attendees = json.load(f)

    c = canvas.Canvas(output_path, pagesize=LETTER)
    page_width, page_height = LETTER

    for i, att in enumerate(attendees):
        col = i % 2
        row = (i // 2) % 4

        if i > 0 and i % 8 == 0:
            c.showPage()

        x = LEFT_MARGIN + col * (BADGE_WIDTH + COL_GAP)
        y = page_height - TOP_MARGIN - (row + 1) * BADGE_HEIGHT

        # Badge border (light gray, for cutting guide)
        c.setStrokeColorRGB(0.85, 0.85, 0.85)
        c.setLineWidth(0.5)
        c.rect(x, y, BADGE_WIDTH, BADGE_HEIGHT)

        # Name — large and bold
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 18)
        name = att.get("name", "?")
        c.drawCentredString(x + BADGE_WIDTH / 2, y + BADGE_HEIGHT - 40, name)

        # Tagline (role + top area)
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        tagline = f"{att.get('role', '')} · {att.get('top_climate_area', '')}"
        c.drawCentredString(x + BADGE_WIDTH / 2, y + BADGE_HEIGHT - 56, tagline)

        # QR code
        token = att.get("token", "")
        url = f"{base_url}/{event_slug}/a/{token}"
        qr_path = make_qr_image(url)
        qr_size = 1.0 * inch
        c.drawImage(
            qr_path,
            x + BADGE_WIDTH / 2 - qr_size / 2,
            y + 12,
            width=qr_size,
            height=qr_size,
        )

        # Small URL hint
        c.setFont("Helvetica", 6)
        c.setFillColorRGB(0.6, 0.6, 0.6)
        c.drawCentredString(x + BADGE_WIDTH / 2, y + 4, "Scan for your matches")

    c.save()
    print(f"Generated {len(attendees)} badges → {output_path}")


def generate_walkup_badges(
    walkup_path: str = "data/walkup_badges.json",
    output_path: str = "badges_walkups.pdf",
    base_url: str = "http://localhost:8000",
    event_slug: str = "climate-week-2026",
) -> None:
    """Generate badge PDF for walk-up reserve badges with fun slugs."""
    with open(walkup_path) as f:
        badges = json.load(f)

    c = canvas.Canvas(output_path, pagesize=LETTER)
    page_width, page_height = LETTER

    for i, badge in enumerate(badges):
        col = i % 2
        row = (i // 2) % 4
        if i > 0 and i % 8 == 0:
            c.showPage()

        x = LEFT_MARGIN + col * (BADGE_WIDTH + COL_GAP)
        y = page_height - TOP_MARGIN - (row + 1) * BADGE_HEIGHT

        # Badge border
        c.setStrokeColorRGB(0.85, 0.85, 0.85)
        c.setLineWidth(0.5)
        c.rect(x, y, BADGE_WIDTH, BADGE_HEIGHT)

        # Fun slug — large and bold
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(x + BADGE_WIDTH / 2, y + BADGE_HEIGHT - 38, badge["slug"])

        # "WALK-UP" label
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0.6, 0.4, 0.0)
        c.drawCentredString(x + BADGE_WIDTH / 2, y + BADGE_HEIGHT - 54, "WALK-UP GUEST")

        # "Write your name:" line
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawString(x + 20, y + BADGE_HEIGHT - 72, "Name: ________________________")

        # QR code
        url = f"{base_url}/{event_slug}/a/{badge['token']}"
        qr_path = make_qr_image(url)
        qr_size = 0.9 * inch
        c.drawImage(
            qr_path,
            x + BADGE_WIDTH / 2 - qr_size / 2,
            y + 10,
            width=qr_size,
            height=qr_size,
        )

        c.setFont("Helvetica", 6)
        c.setFillColorRGB(0.6, 0.6, 0.6)
        c.drawCentredString(x + BADGE_WIDTH / 2, y + 4, "Scan for your matches")

    c.save()
    print(f"Generated {len(badges)} walk-up badges → {output_path}")


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    slug = sys.argv[2] if len(sys.argv) > 2 else "climate-week-2026"

    generate_attendee_badges(base_url=base_url, event_slug=slug)
    generate_walkup_badges(base_url=base_url, event_slug=slug)
