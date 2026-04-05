"""
Numeria Institute — Générateur de certificats PDF
"""

import qrcode
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# ── COULEURS NUMERIA ──────────────────────────────────────────────
BLEU_MARINE = HexColor('#1A3C6E')
BLEU_FONCE  = HexColor('#152f58')
OR_NUMERIA  = HexColor('#E8A020')
BLANC       = white
GRIS_TEXTE  = HexColor('#6B7280')
BLEU_CLAIR  = HexColor('#93b8e8')


def dessiner_atome(c, cx, cy, rayon_orbite=28, rayon_noyau=7,
                   couleur_orbite=None, couleur_noyau=None):
    if couleur_orbite is None:
        couleur_orbite = OR_NUMERIA
    if couleur_noyau is None:
        couleur_noyau = OR_NUMERIA

    c.setFillColor(couleur_noyau)
    c.circle(cx, cy, rayon_noyau, fill=1, stroke=0)

    c.setStrokeColor(couleur_orbite)
    c.setLineWidth(1.5)
    rp = rayon_orbite * 0.35

    c.ellipse(cx - rayon_orbite, cy - rp,
              cx + rayon_orbite, cy + rp, fill=0, stroke=1)

    c.saveState()
    c.translate(cx, cy)
    c.rotate(60)
    c.ellipse(-rayon_orbite, -rp, rayon_orbite, rp, fill=0, stroke=1)
    c.restoreState()

    c.saveState()
    c.translate(cx, cy)
    c.rotate(120)
    c.ellipse(-rayon_orbite, -rp, rayon_orbite, rp, fill=0, stroke=1)
    c.restoreState()

    c.setFillColor(BLANC)
    c.circle(cx + rayon_orbite, cy, 3.5, fill=1, stroke=0)
    c.circle(cx - rayon_orbite * 0.5,  cy + rp * 0.85, 3.5, fill=1, stroke=0)
    c.circle(cx - rayon_orbite * 0.5,  cy - rp * 0.85, 3.5, fill=1, stroke=0)


def generer_qr_code(texte):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=6,
        border=2,
    )
    qr.add_data(texte)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1A3C6E", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return ImageReader(buf)


def generer_certificat_pdf(inscription, url_verification=None):
    buffer = io.BytesIO()

    largeur, hauteur = landscape(A4)   # 842 x 595 pts
    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    etudiant  = inscription.etudiant
    cours     = inscription.cours
    date_fin  = inscription.date_fin or datetime.now()

    prenom     = etudiant.first_name or etudiant.username
    nom        = etudiant.last_name  or ''
    nom_complet = f"{prenom} {nom}".strip()

    CX = largeur / 2   # centre horizontal = 421 pts

    # ══════════════════════════════════════════════════════
    # FOND BLANC
    # ══════════════════════════════════════════════════════
    c.setFillColor(BLANC)
    c.rect(0, 0, largeur, hauteur, fill=1, stroke=0)

    # ══════════════════════════════════════════════════════
    # BORDURES LATÉRALES OR (gauche et droite)
    # ══════════════════════════════════════════════════════
    c.setFillColor(OR_NUMERIA)
    c.rect(0, 0, 0.6*cm, hauteur, fill=1, stroke=0)
    c.rect(largeur - 0.6*cm, 0, 0.6*cm, hauteur, fill=1, stroke=0)

    # ══════════════════════════════════════════════════════
    # BANDE HEADER BLEU MARINE (haut)
    # ══════════════════════════════════════════════════════
    HEADER_H = 3.8 * cm
    c.setFillColor(BLEU_MARINE)
    c.rect(0, hauteur - HEADER_H, largeur, HEADER_H, fill=1, stroke=0)

    # Barre or sous le header
    c.setFillColor(OR_NUMERIA)
    c.rect(0, hauteur - HEADER_H - 0.4*cm, largeur, 0.4*cm, fill=1, stroke=0)

    # ══════════════════════════════════════════════════════
    # BANDE FOOTER BLEU MARINE (bas)
    # ══════════════════════════════════════════════════════
    FOOTER_H = 1.8 * cm
    c.setFillColor(BLEU_MARINE)
    c.rect(0, 0, largeur, FOOTER_H, fill=1, stroke=0)

    # Barre or au-dessus du footer
    c.setFillColor(OR_NUMERIA)
    c.rect(0, FOOTER_H, largeur, 0.4*cm, fill=1, stroke=0)

    # ══════════════════════════════════════════════════════
    # LOGO — HEADER GAUCHE
    # ══════════════════════════════════════════════════════
    atome_cx = 1.8 * cm
    atome_cy = hauteur - HEADER_H / 2
    dessiner_atome(c, atome_cx, atome_cy,
                   rayon_orbite=22, rayon_noyau=6,
                   couleur_orbite=OR_NUMERIA, couleur_noyau=OR_NUMERIA)

    # Texte logo
    c.setFillColor(OR_NUMERIA)
    c.setFont('Helvetica-Bold', 17)
    c.drawString(3.2*cm, hauteur - HEADER_H/2 + 0.3*cm, 'NUMERIA')

    c.setFillColor(BLEU_CLAIR)
    c.setFont('Helvetica', 9)
    c.drawString(3.2*cm, hauteur - HEADER_H/2 - 0.35*cm, 'INSTITUTE')

    c.setStrokeColor(OR_NUMERIA)
    c.setLineWidth(1)
    c.line(3.2*cm, hauteur - HEADER_H/2 - 0.6*cm,
           8.5*cm, hauteur - HEADER_H/2 - 0.6*cm)

    # ══════════════════════════════════════════════════════
    # TITRE — HEADER DROITE
    # ══════════════════════════════════════════════════════
    c.setFillColor(BLANC)
    c.setFont('Helvetica-Bold', 13)
    c.drawRightString(largeur - 1.4*cm,
                      hauteur - HEADER_H/2 + 0.3*cm,
                      'CERTIFICAT DE RÉUSSITE')

    c.setFillColor(BLEU_CLAIR)
    c.setFont('Helvetica', 8.5)
    c.drawRightString(largeur - 1.4*cm,
                      hauteur - HEADER_H/2 - 0.35*cm,
                      'CALCUL · IA · SOLUTIONS LOCALES')

    # ══════════════════════════════════════════════════════
    # CORPS — zones de travail
    # zone_haut : bas du header+barre = hauteur - HEADER_H - 0.4cm
    # zone_bas  : haut du footer+barre = FOOTER_H + 0.4cm
    # ══════════════════════════════════════════════════════
    zone_haut = hauteur - HEADER_H - 0.4*cm   # ≈ 554 pts
    zone_bas  = FOOTER_H + 0.4*cm             # ≈ 65 pts
    zone_h    = zone_haut - zone_bas           # ≈ 489 pts

    # On divise la zone en 3 bandes verticales égales
    # Bande haute  : certifie que + NOM
    # Bande milieu : cours + infos
    # Bande basse  : signatures + date + QR

    # ── LIGNE 1 — "Numeria Institute certifie que" ────────
    y1 = zone_haut - 1.4*cm
    c.setFillColor(GRIS_TEXTE)
    c.setFont('Helvetica', 11)
    c.drawCentredString(CX, y1, 'Numeria Institute certifie que')

    # ── LIGNE 2 — NOM DE L'ÉTUDIANT ──────────────────────
    y2 = y1 - 1.6*cm
    c.setFillColor(BLEU_MARINE)
    c.setFont('Helvetica-Bold', 44)
    c.drawCentredString(CX, y2, nom_complet)

    # Ligne décorative sous le nom
    nom_largeur = min(len(nom_complet) * 22, 380)
    c.setStrokeColor(OR_NUMERIA)
    c.setLineWidth(2.5)
    c.line(CX - nom_largeur/2, y2 - 0.55*cm,
           CX + nom_largeur/2, y2 - 0.55*cm)

    # ── LIGNE 3 — "a complété avec succès le cours" ───────
    y3 = y2 - 1.6*cm
    c.setFillColor(GRIS_TEXTE)
    c.setFont('Helvetica', 11)
    c.drawCentredString(CX, y3, 'a complété avec succès le cours')

    # ── LIGNE 4 — NOM DU COURS ───────────────────────────
    y4 = y3 - 1.3*cm
    taille_titre = 26 if len(cours.titre) < 35 else 20
    c.setFillColor(BLEU_MARINE)
    c.setFont('Helvetica-Bold', taille_titre)
    c.drawCentredString(CX, y4, cours.titre)

    # ── LIGNE 5 — MATIÈRE ET NIVEAU ──────────────────────
    y5 = y4 - 1.0*cm
    c.setFillColor(GRIS_TEXTE)
    c.setFont('Helvetica', 10)
    info = f"{cours.get_matiere_display()} — Niveau {cours.get_niveau_display()}"
    c.drawCentredString(CX, y5, info)

    # ── LIGNE 6 — ÉTOILES ────────────────────────────────
    y6 = y5 - 0.9*cm
    c.setFillColor(OR_NUMERIA)
    c.setFont('Helvetica-Bold', 18)
    c.drawCentredString(CX, y6, '★   ★   ★')

    # ══════════════════════════════════════════════════════
    # ZONE BASSE — Signatures + Date + QR
    # On fixe une ligne de base à zone_bas + 2.8cm
    # ══════════════════════════════════════════════════════
    SIG_Y = zone_bas + 2.5*cm   # ligne de signature

    # ── SIGNATURE GAUCHE ─────────────────────────────────
    SIG_G_X1 = 1.4*cm
    SIG_G_X2 = 10.0*cm

    c.setStrokeColor(BLEU_MARINE)
    c.setLineWidth(0.8)
    c.line(SIG_G_X1, SIG_Y, SIG_G_X2, SIG_Y)

    c.setFillColor(BLEU_MARINE)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(SIG_G_X1, SIG_Y + 0.35*cm, 'Ounimborbitibou Djabon')

    c.setFillColor(GRIS_TEXTE)
    c.setFont('Helvetica', 9)
    c.drawString(SIG_G_X1, SIG_Y - 0.55*cm, 'Co-fondateur & Directeur académique')
    c.drawString(SIG_G_X1, SIG_Y - 1.0*cm,  'Numeria Institute — Lomé, Togo')

    # ── DATE — CENTRE ─────────────────────────────────────
    mois_fr = {
        1: 'janvier', 2: 'février',  3: 'mars',      4: 'avril',
        5: 'mai',     6: 'juin',     7: 'juillet',   8: 'août',
        9: 'septembre', 10: 'octobre', 11: 'novembre', 12: 'décembre'
    }
    date_str = f"Lomé, le {date_fin.day} {mois_fr[date_fin.month]} {date_fin.year}"
    c.setFillColor(GRIS_TEXTE)
    c.setFont('Helvetica', 10)
    c.drawCentredString(CX, SIG_Y - 0.2*cm, date_str)

    # ── SIGNATURE DROITE ──────────────────────────────────
    # On réserve la droite pour la sig droite
    # QR sera dans le coin bas-droit, donc on recule la sig droite
    SIG_D_X1 = largeur - 13.5*cm
    SIG_D_X2 = largeur - 4.5*cm   # on laisse 4.5cm pour le QR

    c.setStrokeColor(BLEU_MARINE)
    c.setLineWidth(0.8)
    c.line(SIG_D_X1, SIG_Y, SIG_D_X2, SIG_Y)

    c.setFillColor(BLEU_MARINE)
    c.setFont('Helvetica-Bold', 10)
    c.drawRightString(SIG_D_X2, SIG_Y + 0.35*cm, 'Co-fondateur & Directeur technique')

    c.setFillColor(GRIS_TEXTE)
    c.setFont('Helvetica', 9)
    c.drawRightString(SIG_D_X2, SIG_Y - 0.55*cm, 'Numeria Institute')

    # ── QR CODE — coin bas droit ──────────────────────────
    if url_verification:
        qr_img    = generer_qr_code(url_verification)
        qr_taille = 2.8 * cm
        qr_x      = largeur - 0.6*cm - qr_taille - 0.4*cm
        qr_y      = zone_bas + 0.2*cm
        c.drawImage(qr_img, qr_x, qr_y,
                    width=qr_taille, height=qr_taille)
        c.setFillColor(GRIS_TEXTE)
        c.setFont('Helvetica', 7.5)
        c.drawCentredString(qr_x + qr_taille/2,
                            qr_y - 0.35*cm,
                            'Vérifier ce certificat')

    # ══════════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════════
    ref = f"Réf : NIM-CERT-{inscription.id:06d}-{date_fin.year}"
    c.setFillColor(BLEU_CLAIR)
    c.setFont('Helvetica', 8)
    c.drawCentredString(CX, FOOTER_H/2 + 0.2*cm, ref)

    c.setFont('Helvetica', 7.5)
    c.drawCentredString(CX, FOOTER_H/2 - 0.3*cm,
                        'Numeria Institute · Lomé, Togo · contact@numeriainstitute.com')

    c.save()
    buffer.seek(0)
    return buffer.read()