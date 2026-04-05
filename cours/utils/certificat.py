"""
Numeria Institute — Générateur de certificats PDF
Utilise ReportLab pour créer des certificats professionnels.
"""

import qrcode
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from django.conf import settings


# ── COULEURS NUMERIA ──────────────────────────────────────────────
BLEU_MARINE  = HexColor('#1A3C6E')
BLEU_FONCE   = HexColor('#152f58')
OR_NUMERIA   = HexColor('#E8A020')
OR_CLAIR     = HexColor('#f5c15e')
BLANC        = white
GRIS_CLAIR   = HexColor('#F4F6F8')
GRIS_TEXTE   = HexColor('#6B7280')


def dessiner_atome(c, cx, cy, rayon_orbite=28, rayon_noyau=7, couleur_orbite=None, couleur_noyau=None):
    """
    Dessine le logo atome Numeria à la position (cx, cy).
    """
    if couleur_orbite is None:
        couleur_orbite = OR_NUMERIA
    if couleur_noyau is None:
        couleur_noyau = OR_NUMERIA

    # Noyau central
    c.setFillColor(couleur_noyau)
    c.circle(cx, cy, rayon_noyau, fill=1, stroke=0)

    # 3 orbites elliptiques
    c.setStrokeColor(couleur_orbite)
    c.setLineWidth(1.5)

    rayon_petit = rayon_orbite * 0.35

    # Orbite 1 — horizontale
    c.ellipse(cx - rayon_orbite, cy - rayon_petit,
              cx + rayon_orbite, cy + rayon_petit,
              fill=0, stroke=1)

    # Orbite 2 — inclinée 60°
    c.saveState()
    c.translate(cx, cy)
    c.rotate(60)
    c.ellipse(-rayon_orbite, -rayon_petit,
               rayon_orbite,  rayon_petit,
               fill=0, stroke=1)
    c.restoreState()

    # Orbite 3 — inclinée 120°
    c.saveState()
    c.translate(cx, cy)
    c.rotate(120)
    c.ellipse(-rayon_orbite, -rayon_petit,
               rayon_orbite,  rayon_petit,
               fill=0, stroke=1)
    c.restoreState()

    # 3 électrons
    c.setFillColor(BLANC)
    c.circle(cx + rayon_orbite, cy, 3.5, fill=1, stroke=0)
    c.circle(cx - rayon_orbite * 0.5, cy + rayon_petit * 0.85, 3.5, fill=1, stroke=0)
    c.circle(cx - rayon_orbite * 0.5, cy - rayon_petit * 0.85, 3.5, fill=1, stroke=0)


def generer_qr_code(texte):
    """
    Génère un QR code et le retourne comme ImageReader ReportLab.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=6,
        border=2,
    )
    qr.add_data(texte)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1A3C6E", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return ImageReader(buffer)


def generer_certificat_pdf(inscription, url_verification=None):
    """
    Génère un certificat PDF pour une inscription terminée.

    Args:
        inscription : objet InscriptionCours (doit avoir est_termine=True)
        url_verification : URL pour vérifier le certificat (optionnel)

    Returns:
        bytes : le contenu du fichier PDF
    """
    buffer = io.BytesIO()

    # Page en mode paysage A4
    largeur, hauteur = landscape(A4)   # 842 x 595 points
    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    etudiant = inscription.etudiant
    cours    = inscription.cours
    date_fin = inscription.date_fin or datetime.now()

    # Nom complet de l'étudiant
    prenom = etudiant.first_name or etudiant.username
    nom    = etudiant.last_name or ''
    nom_complet = f"{prenom} {nom}".strip()

    # ── FOND PRINCIPAL ────────────────────────────────────────────
    c.setFillColor(BLANC)
    c.rect(0, 0, largeur, hauteur, fill=1, stroke=0)

    # ── BANDE SUPÉRIEURE BLEU MARINE ─────────────────────────────
    c.setFillColor(BLEU_MARINE)
    c.rect(0, hauteur - 3.5*cm, largeur, 3.5*cm, fill=1, stroke=0)

    # ── BANDE INFÉRIEURE BLEU MARINE ─────────────────────────────
    c.setFillColor(BLEU_MARINE)
    c.rect(0, 0, largeur, 2.2*cm, fill=1, stroke=0)

    # ── BARRE OR SUPÉRIEURE (séparateur) ────────────────────────
    c.setFillColor(OR_NUMERIA)
    c.rect(0, hauteur - 3.5*cm - 0.35*cm, largeur, 0.35*cm, fill=1, stroke=0)

    # ── BARRE OR INFÉRIEURE ──────────────────────────────────────
    c.setFillColor(OR_NUMERIA)
    c.rect(0, 2.2*cm, largeur, 0.35*cm, fill=1, stroke=0)

    # ── BORDURE LATÉRALE GAUCHE OR ───────────────────────────────
    c.setFillColor(OR_NUMERIA)
    c.rect(0, 0, 0.5*cm, hauteur, fill=1, stroke=0)

    # ── BORDURE LATÉRALE DROITE OR ──────────────────────────────
    c.setFillColor(OR_NUMERIA)
    c.rect(largeur - 0.5*cm, 0, 0.5*cm, hauteur, fill=1, stroke=0)

    # ── LOGO ATOME (haut gauche dans la bande bleue) ─────────────
    atome_x = 1.8 * cm
    atome_y = hauteur - 1.85 * cm
    dessiner_atome(c, atome_x, atome_y, rayon_orbite=22, rayon_noyau=6,
                   couleur_orbite=OR_NUMERIA, couleur_noyau=OR_NUMERIA)

    # ── TEXTE LOGO HEADER ────────────────────────────────────────
    c.setFillColor(OR_NUMERIA)
    c.setFont('Helvetica-Bold', 16)
    c.drawString(3.2*cm, hauteur - 1.5*cm, 'NUMERIA')

    c.setFillColor(HexColor('#93b8e8'))
    c.setFont('Helvetica', 8)
    c.drawString(3.2*cm, hauteur - 2.1*cm, 'INSTITUTE')

    # Ligne or sous le texte logo
    c.setStrokeColor(OR_NUMERIA)
    c.setLineWidth(1)
    c.line(3.2*cm, hauteur - 2.3*cm, 8*cm, hauteur - 2.3*cm)

    # ── TITRE "CERTIFICAT DE RÉUSSITE" (header droite) ───────────
    c.setFillColor(BLANC)
    c.setFont('Helvetica-Bold', 11)
    c.drawRightString(largeur - 1.2*cm, hauteur - 1.55*cm, 'CERTIFICAT DE RÉUSSITE')

    c.setFillColor(HexColor('#93b8e8'))
    c.setFont('Helvetica', 8)
    c.drawRightString(largeur - 1.2*cm, hauteur - 2.1*cm, 'CALCUL · IA · SOLUTIONS LOCALES')

    # ── CORPS DU CERTIFICAT ──────────────────────────────────────
    corps_y_debut = hauteur - 4.3*cm
    corps_y_fin   = 2.6*cm
    corps_centre  = (corps_y_debut + corps_y_fin) / 2

    # Texte introductif
    c.setFillColor(GRIS_TEXTE)
    c.setFont('Helvetica', 10)
    c.drawCentredString(largeur / 2, corps_y_debut - 0.6*cm,
                        'Numeria Institute certifie que')

    # ── NOM DE L'ÉTUDIANT ────────────────────────────────────────
    c.setFillColor(BLEU_MARINE)
    c.setFont('Helvetica-Bold', 36)
    c.drawCentredString(largeur / 2, corps_y_debut - 2.0*cm, nom_complet)

    # Ligne décorative sous le nom
    ligne_w = min(len(nom_complet) * 18, 400)
    c.setStrokeColor(OR_NUMERIA)
    c.setLineWidth(2)
    c.line(largeur/2 - ligne_w/2, corps_y_debut - 2.5*cm,
           largeur/2 + ligne_w/2, corps_y_debut - 2.5*cm)

    # Texte "a complété avec succès"
    c.setFillColor(GRIS_TEXTE)
    c.setFont('Helvetica', 10)
    c.drawCentredString(largeur / 2, corps_y_debut - 3.2*cm,
                        'a complété avec succès le cours')

    # ── NOM DU COURS ────────────────────────────────────────────
    c.setFillColor(BLEU_MARINE)
    # Adapter la taille selon la longueur du titre
    taille_cours = 22 if len(cours.titre) < 40 else 17
    c.setFont('Helvetica-Bold', taille_cours)
    c.drawCentredString(largeur / 2, corps_y_debut - 4.3*cm, cours.titre)

    # Matière et niveau
    c.setFillColor(GRIS_TEXTE)
    c.setFont('Helvetica', 9)
    info_cours = f"{cours.get_matiere_display()} — Niveau {cours.get_niveau_display()}"
    c.drawCentredString(largeur / 2, corps_y_debut - 5.0*cm, info_cours)

    # ── ÉTOILES DÉCORATIVES ──────────────────────────────────────
    c.setFillColor(OR_NUMERIA)
    c.setFont('Helvetica', 14)
    c.drawCentredString(largeur / 2, corps_y_debut - 5.7*cm, '★  ★  ★')

    # ── DATE ─────────────────────────────────────────────────────
    mois_fr = {
        1: 'janvier', 2: 'février', 3: 'mars', 4: 'avril',
        5: 'mai', 6: 'juin', 7: 'juillet', 8: 'août',
        9: 'septembre', 10: 'octobre', 11: 'novembre', 12: 'décembre'
    }
    date_str = f"Lomé, le {date_fin.day} {mois_fr[date_fin.month]} {date_fin.year}"

    c.setFillColor(GRIS_TEXTE)
    c.setFont('Helvetica', 9)
    c.drawCentredString(largeur / 2, 3.4*cm, date_str)

    # ── SIGNATURE GAUCHE ─────────────────────────────────────────
    sig_y = 3.8*cm
    c.setStrokeColor(BLEU_MARINE)
    c.setLineWidth(0.8)
    c.line(1.5*cm, sig_y, 9*cm, sig_y)

    c.setFillColor(BLEU_MARINE)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(1.5*cm, sig_y + 0.3*cm, 'Ounimborbitibou Djabon')

    c.setFillColor(GRIS_TEXTE)
    c.setFont('Helvetica', 8)
    c.drawString(1.5*cm, sig_y - 0.5*cm, 'Co-fondateur & Directeur académique')
    c.drawString(1.5*cm, sig_y - 0.9*cm, 'Numeria Institute — Lomé, Togo')

    # ── SIGNATURE DROITE ─────────────────────────────────────────
    c.setStrokeColor(BLEU_MARINE)
    c.setLineWidth(0.8)
    c.line(largeur - 9*cm, sig_y, largeur - 1.5*cm, sig_y)

    c.setFillColor(BLEU_MARINE)
    c.setFont('Helvetica-Bold', 9)
    c.drawRightString(largeur - 1.5*cm, sig_y + 0.3*cm, 'Co-fondateur & Directeur technique')

    c.setFillColor(GRIS_TEXTE)
    c.setFont('Helvetica', 8)
    c.drawRightString(largeur - 1.5*cm, sig_y - 0.5*cm, 'Numeria Institute')

    # ── QR CODE (bas droite) ────────────────────────────────────
    if url_verification:
        qr_image = generer_qr_code(url_verification)
        qr_taille = 2.5 * cm
        qr_x = largeur - 4.2*cm
        qr_y = 2.8*cm
        c.drawImage(qr_image, qr_x, qr_y, width=qr_taille, height=qr_taille)

        c.setFillColor(GRIS_TEXTE)
        c.setFont('Helvetica', 7)
        c.drawCentredString(qr_x + qr_taille/2, 2.6*cm, 'Vérifier ce certificat')

    # ── RÉFÉRENCE CERTIFICAT (footer) ────────────────────────────
    ref = f"Réf : NIM-CERT-{inscription.id:06d}-{date_fin.year}"
    c.setFillColor(HexColor('#93b8e8'))
    c.setFont('Helvetica', 7.5)
    c.drawCentredString(largeur / 2, 0.9*cm, ref)

    c.setFillColor(HexColor('#93b8e8'))
    c.setFont('Helvetica', 7)
    c.drawCentredString(largeur / 2, 0.5*cm,
                        'Numeria Institute · Lomé, Togo · contact@numeriainstitute.com')

    # ── FINALISATION ────────────────────────────────────────────
    c.save()
    buffer.seek(0)
    return buffer.read()