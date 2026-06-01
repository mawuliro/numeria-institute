"""
Numeria Institute — Générateur de certificats PDF
Inspiré du style classique de certificat avec bordure ornementale.
"""

import qrcode
import io
import math
from datetime import datetime
from django.conf import settings
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# ── COULEURS ──────────────────────────────────────────────────────
BLEU_MARINE  = HexColor('#1A3C6E')
BLEU_FONCE   = HexColor('#0f2847')
OR_NUMERIA   = HexColor('#C8960C')
OR_CLAIR     = HexColor('#E8B830')
OR_PALE      = HexColor('#F5D878')
BLANC        = white
GRIS_TEXTE   = HexColor('#444444')
GRIS_CLAIR   = HexColor('#888888')
FOND_PARCHEMIN = HexColor('#F5F0E8')
BLEU_CLAIR   = HexColor('#93b8e8')


# ── FONTES DISPONIBLES ────────────────────────────────────────────
# Helvetica, Helvetica-Bold, Helvetica-Oblique, Helvetica-BoldOblique
# Times-Roman, Times-Bold, Times-Italic, Times-BoldItalic
# Courier, Courier-Bold, Courier-Oblique


def dessiner_motif_coins(c, largeur, hauteur, marge=0.5*cm):
    """Dessine des motifs décoratifs dans les 4 coins."""
    taille = 1.0 * cm
    coins = [
        (marge, marge),                          # bas-gauche
        (largeur - marge - taille, marge),       # bas-droit
        (marge, hauteur - marge - taille),       # haut-gauche
        (largeur - marge - taille, hauteur - marge - taille),  # haut-droit
    ]
    c.setStrokeColor(OR_NUMERIA)
    c.setFillColor(OR_NUMERIA)
    c.setLineWidth(1.5)
    for (x, y) in coins:
        cx = x + taille / 2
        cy = y + taille / 2
        # petite étoile / croix ornementale
        for angle_deg in range(0, 360, 45):
            angle = math.radians(angle_deg)
            r1 = taille * 0.15
            r2 = taille * 0.45
            x1 = cx + r1 * math.cos(angle)
            y1 = cy + r1 * math.sin(angle)
            x2 = cx + r2 * math.cos(angle)
            y2 = cy + r2 * math.sin(angle)
            c.line(x1, y1, x2, y2)
        c.circle(cx, cy, taille * 0.12, fill=1, stroke=0)


def dessiner_bordure_ornementale(c, largeur, hauteur):
    """
    Dessine une bordure ornementale inspirée du certificat classique :
    - Fond parchemin
    - Cadre extérieur bleu épais
    - Cadre intérieur or
    - Motif de vagues/festons sur les bords
    """

    # ── Fond parchemin ────────────────────────────────────────────
    c.setFillColor(FOND_PARCHEMIN)
    c.rect(0, 0, largeur, hauteur, fill=1, stroke=0)

    # ── Rectangle de fond intérieur légèrement plus clair ─────────
    marge_fond = 1.1 * cm
    c.setFillColor(white)
    c.rect(marge_fond, marge_fond,
           largeur - 2 * marge_fond, hauteur - 2 * marge_fond,
           fill=1, stroke=0)

    # ── Bordure externe — bleu épais ──────────────────────────────
    c.setStrokeColor(BLEU_MARINE)
    c.setFillColor(BLEU_MARINE)
    c.setLineWidth(18)
    ep = 0.45 * cm
    c.rect(ep, ep, largeur - 2 * ep, hauteur - 2 * ep, fill=0, stroke=1)

    # ── Bordure intermédiaire — or ─────────────────────────────────
    c.setStrokeColor(OR_NUMERIA)
    c.setLineWidth(4)
    ep2 = 0.85 * cm
    c.rect(ep2, ep2, largeur - 2 * ep2, hauteur - 2 * ep2, fill=0, stroke=1)

    # ── Bordure intérieure — bleu fin ─────────────────────────────
    c.setStrokeColor(BLEU_MARINE)
    c.setLineWidth(1.5)
    ep3 = 1.05 * cm
    c.rect(ep3, ep3, largeur - 2 * ep3, hauteur - 2 * ep3, fill=0, stroke=1)

    # ── Motif festons (demi-cercles) sur chaque côté ──────────────
    _dessiner_festons(c, largeur, hauteur, ep2)

    # ── Motifs de coins ───────────────────────────────────────────
    dessiner_motif_coins(c, largeur, hauteur, marge=0.5 * cm)


def _dessiner_festons(c, largeur, hauteur, ep):
    """
    Dessine des petits demi-cercles en bleu le long des 4 bords,
    simulant les festons du certificat classique.
    """
    c.setStrokeColor(BLEU_MARINE)
    c.setFillColor(BLEU_MARINE)
    c.setLineWidth(0.5)
    r = 0.28 * cm  # rayon des demi-cercles

    # Côté bas
    x = ep + r
    while x < largeur - ep - r:
        c.circle(x, ep, r, fill=1, stroke=0)
        x += 2 * r + 0.05 * cm

    # Côté haut
    x = ep + r
    while x < largeur - ep - r:
        c.circle(x, hauteur - ep, r, fill=1, stroke=0)
        x += 2 * r + 0.05 * cm

    # Côté gauche
    y = ep + r
    while y < hauteur - ep - r:
        c.circle(ep, y, r, fill=1, stroke=0)
        y += 2 * r + 0.05 * cm

    # Côté droit
    y = ep + r
    while y < hauteur - ep - r:
        c.circle(largeur - ep, y, r, fill=1, stroke=0)
        y += 2 * r + 0.05 * cm


def dessiner_logo_N(c, cx, cy, taille=40, couleur_trait=None, couleur_noeud=None, couleur_cercle=None):
    """
    Dessine le logo officiel Numeria Institute :
    - Un grand 'N' formé de segments avec des nœuds (cercles) aux extrémités
    - Un cercle englobant en gris clair
    - Les nœuds centraux (milieu de la diagonale) en teal/vert
    Fidèle au logo vectoriel officiel.
    """
    if couleur_trait is None:
        couleur_trait = BLEU_MARINE
    if couleur_noeud is None:
        couleur_noeud = HexColor('#2DD4BF')   # teal du logo officiel
    if couleur_cercle is None:
        couleur_cercle = HexColor('#CCCCCC')  # gris clair du cercle

    # ── Dimensions relatives ──────────────────────────────────────
    r_cercle   = taille * 0.52          # rayon du cercle englobant
    r_noeud    = taille * 0.085         # nœuds aux coins (ouverts = stroke only)
    r_noeud_c  = taille * 0.075         # nœuds centraux (pleins, teal)
    epaisseur  = taille * 0.055         # épaisseur des traits du N

    # ── Points du N (coordonnées relatives à cx, cy) ──────────────
    # haut-gauche, bas-gauche, haut-droit, bas-droit
    margeH = taille * 0.30
    margeV = taille * 0.38
    hg = (cx - margeH, cy + margeV)   # haut-gauche
    bg = (cx - margeH, cy - margeV)   # bas-gauche
    hd = (cx + margeH, cy + margeV)   # haut-droit
    bd = (cx + margeH, cy - margeV)   # bas-droit

    # Milieux de la diagonale (pour les nœuds teal)
    mid1 = (cx - margeH * 0.15, cy + margeV * 0.15)   # proche haut-gauche
    mid2 = (cx + margeH * 0.15, cy - margeV * 0.15)   # proche bas-droit

    # ── 1. Cercle englobant ───────────────────────────────────────
    c.saveState()
    c.setStrokeColor(couleur_cercle)
    c.setLineWidth(epaisseur * 0.5)
    c.circle(cx, cy, r_cercle, fill=0, stroke=1)
    c.restoreState()

    # ── 2. Traits du N ────────────────────────────────────────────
    c.saveState()
    c.setStrokeColor(couleur_trait)
    c.setLineWidth(epaisseur)
    c.setLineCap(1)   # round caps

    # Jambe gauche (haut-gauche → bas-gauche)
    c.line(hg[0], hg[1], bg[0], bg[1])
    # Diagonale (haut-gauche → bas-droit)
    c.line(hg[0], hg[1], bd[0], bd[1])
    # Jambe droite (haut-droit → bas-droit)
    c.line(hd[0], hd[1], bd[0], bd[1])
    c.restoreState()

    # ── 3. Nœuds aux 4 coins — cercles ouverts (fond blanc) ───────
    for (px, py) in [hg, bg, hd, bd]:
        # fond blanc pour "trouer" le trait
        c.setFillColor(FOND_PARCHEMIN)
        c.setStrokeColor(couleur_trait)
        c.setLineWidth(epaisseur * 0.7)
        c.circle(px, py, r_noeud, fill=1, stroke=1)

    # ── 4. Nœuds centraux — pleins, couleur teal ─────────────────
    c.setFillColor(couleur_noeud)
    c.setStrokeColor(couleur_noeud)
    for (px, py) in [mid1, mid2]:
        c.circle(px, py, r_noeud_c, fill=1, stroke=0)


def dessiner_medaillon_or(c, cx, cy, rayon=1.2*cm):
    """Dessine un médaillon doré façon sceau officiel."""
    # Cercle extérieur dentelé (simulé par des rayons)
    c.setFillColor(OR_NUMERIA)
    nb_dents = 18
    for i in range(nb_dents):
        angle = math.radians(i * 360 / nb_dents)
        x1 = cx + rayon * 0.82 * math.cos(angle)
        y1 = cy + rayon * 0.82 * math.sin(angle)
        x2 = cx + rayon * math.cos(angle)
        y2 = cy + rayon * math.sin(angle)
        c.setLineWidth(4)
        c.setStrokeColor(OR_NUMERIA)
        c.line(x1, y1, x2, y2)

    c.setFillColor(OR_CLAIR)
    c.circle(cx, cy, rayon * 0.80, fill=1, stroke=0)

    c.setFillColor(OR_NUMERIA)
    c.circle(cx, cy, rayon * 0.72, fill=1, stroke=0)

    c.setFillColor(OR_PALE)
    c.circle(cx, cy, rayon * 0.60, fill=1, stroke=0)

    # Lettre N au centre
    c.setFillColor(BLEU_FONCE)
    c.setFont('Times-Bold', 16)
    c.drawCentredString(cx, cy - 0.22 * cm, 'N')


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
    cours     = inscription.course
    date_fin  = inscription.date_fin or datetime.now()

    prenom      = etudiant.first_name or etudiant.username
    nom         = etudiant.last_name  or ''
    nom_complet = f"{prenom} {nom}".strip()

    CX = largeur / 2   # centre horizontal ≈ 421 pts

    # ══════════════════════════════════════════════════════════════
    # BORDURE ORNEMENTALE (fond + cadres + festons)
    # ══════════════════════════════════════════════════════════════
    dessiner_bordure_ornementale(c, largeur, hauteur)

    # Marges de travail à l'intérieur de la bordure
    MARGE_H = 1.5 * cm
    MARGE_V = 1.3 * cm
    zone_haut = hauteur - MARGE_V
    zone_bas  = MARGE_V

    # ══════════════════════════════════════════════════════════════
    # EN-TÊTE : Logo NUMERIA (gauche) + atome
    # ══════════════════════════════════════════════════════════════
    logo_y = zone_haut - 0.9 * cm

    atome_cx = MARGE_H + 0.9 * cm
    atome_cy = logo_y - 0.05 * cm
    dessiner_logo_N(c, atome_cx, atome_cy,
                    taille=34,
                    couleur_trait=BLEU_MARINE,
                    couleur_noeud=HexColor('#2DD4BF'),
                    couleur_cercle=HexColor('#CCCCCC'))

    c.setFillColor(BLEU_MARINE)
    c.setFont('Helvetica-Bold', 13)
    c.drawString(MARGE_H + 2.0 * cm, logo_y + 0.1 * cm, 'NUMERIA')

    c.setFillColor(GRIS_TEXTE)
    c.setFont('Helvetica', 8)
    c.drawString(MARGE_H + 2.0 * cm, logo_y - 0.42 * cm, 'INSTITUTE')

    # Ligne décorative sous le logo
    c.setStrokeColor(OR_NUMERIA)
    c.setLineWidth(1)
    c.line(MARGE_H + 2.0 * cm, logo_y - 0.65 * cm,
           MARGE_H + 6.0 * cm, logo_y - 0.65 * cm)

    # ══════════════════════════════════════════════════════════════
    # TITRE PRINCIPAL  —  style calligraphique via Times-BoldItalic
    # ══════════════════════════════════════════════════════════════
    titre_y = zone_haut - 1.8 * cm
    c.setFillColor(BLEU_MARINE)
    c.setFont('Times-BoldItalic', 38)
    c.drawCentredString(CX, titre_y, 'Certificat de Réussite')

    # Petite ligne décorative or sous le titre
    deco_long = 9 * cm
    c.setStrokeColor(OR_NUMERIA)
    c.setLineWidth(2)
    c.line(CX - deco_long / 2, titre_y - 0.45 * cm,
           CX + deco_long / 2, titre_y - 0.45 * cm)

    # Filet fin en dessous
    c.setLineWidth(0.8)
    c.line(CX - deco_long * 0.6 / 2, titre_y - 0.68 * cm,
           CX + deco_long * 0.6 / 2, titre_y - 0.68 * cm)

    # ══════════════════════════════════════════════════════════════
    # SOUS-TITRE  "Ce document certifie que"
    # ══════════════════════════════════════════════════════════════
    sub_y = titre_y - 1.35 * cm
    c.setFillColor(GRIS_TEXTE)
    c.setFont('Times-Italic', 13)
    c.drawCentredString(CX, sub_y, 'Ce document certifie que')

    # ══════════════════════════════════════════════════════════════
    # NOM DE L'ÉTUDIANT
    # ══════════════════════════════════════════════════════════════
    nom_y = sub_y - 1.5 * cm
    c.setFillColor(BLEU_MARINE)
    c.setFont('Times-Bold', 40)
    c.drawCentredString(CX, nom_y, nom_complet)

    # Ligne soulignant le nom
    longueur_nom = min(len(nom_complet) * 19, 400)
    c.setStrokeColor(BLEU_MARINE)
    c.setLineWidth(1.2)
    c.line(CX - longueur_nom / 2, nom_y - 0.40 * cm,
           CX + longueur_nom / 2, nom_y - 0.40 * cm)

    # ══════════════════════════════════════════════════════════════
    # "a complété avec succès"
    # ══════════════════════════════════════════════════════════════
    compl_y = nom_y - 1.30 * cm
    c.setFillColor(GRIS_TEXTE)
    c.setFont('Times-Italic', 13)
    c.drawCentredString(CX, compl_y, 'a complété avec succès le cours dispensé par')

    # ══════════════════════════════════════════════════════════════
    # NOM DE L'INSTITUT (grand, bleu, calligraphique)
    # ══════════════════════════════════════════════════════════════
    inst_y = compl_y - 1.2 * cm
    c.setFillColor(BLEU_MARINE)
    c.setFont('Times-BoldItalic', 28)
    c.drawCentredString(CX, inst_y, 'Numeria Institute')

    # ══════════════════════════════════════════════════════════════
    # NOM DU COURS
    # ══════════════════════════════════════════════════════════════
    cours_y = inst_y - 0.95 * cm
    taille_cours = 20 if len(cours.titre) < 40 else 15
    c.setFillColor(BLEU_MARINE)
    c.setFont('Times-Bold', taille_cours)
    c.drawCentredString(CX, cours_y, cours.titre)

    # ══════════════════════════════════════════════════════════════
    # DATE — style "le X mois YYYY"
    # ══════════════════════════════════════════════════════════════
    mois_fr = {
        1: 'janvier', 2: 'février',  3: 'mars',    4: 'avril',
        5: 'mai',     6: 'juin',     7: 'juillet',  8: 'août',
        9: 'septembre', 10: 'octobre', 11: 'novembre', 12: 'décembre'
    }
    date_str = f"le {date_fin.day} {mois_fr[date_fin.month]} {date_fin.year}"
    date_y = cours_y - 0.85 * cm
    c.setFillColor(BLEU_MARINE)
    c.setFont('Times-Bold', 13)
    c.drawCentredString(CX, date_y, date_str)

    # ══════════════════════════════════════════════════════════════
    # ZONE BAS : Médaillon (gauche) + Signature (centre-droit) + QR (droit)
    # ══════════════════════════════════════════════════════════════
    SIG_Y    = zone_bas + 2.4 * cm   # ligne de la signature
    MEDAL_CX = MARGE_H + 2.2 * cm   # centre médaillon

    # ── Médaillon doré ────────────────────────────────────────────
    dessiner_medaillon_or(c, MEDAL_CX, SIG_Y - 0.1 * cm, rayon=1.1 * cm)

    # ── Signature unique — centrée légèrement à droite ────────────
    SIG_CX = CX + 2.5 * cm   # léger décalage droit pour équilibre visuel

    # Nom du signataire
    c.setFillColor(BLEU_MARINE)
    c.setFont('Times-BoldItalic', 13)
    c.drawCentredString(SIG_CX, SIG_Y + 0.45 * cm, 'Ounimborbitibou Djabon')

    # Ligne de signature
    sig_demi = 4.5 * cm
    c.setStrokeColor(BLEU_MARINE)
    c.setLineWidth(1)
    c.line(SIG_CX - sig_demi, SIG_Y,
           SIG_CX + sig_demi, SIG_Y)

    # Titre du signataire
    c.setFillColor(GRIS_CLAIR)
    c.setFont('Times-Italic', 10)
    c.drawCentredString(SIG_CX, SIG_Y - 0.50 * cm,
                        'Co-fondateur & Directeur académique')
    c.drawCentredString(SIG_CX, SIG_Y - 0.90 * cm,
                        'Numeria Institute — Lomé, Togo')

    # ── QR Code — coin bas droit ──────────────────────────────────
    if url_verification:
        qr_img    = generer_qr_code(url_verification)
        qr_taille = 2.4 * cm
        qr_x      = largeur - MARGE_H - qr_taille - 0.2 * cm
        qr_y      = zone_bas + 0.2 * cm
        c.drawImage(qr_img, qr_x, qr_y,
                    width=qr_taille, height=qr_taille)
        c.setFillColor(GRIS_CLAIR)
        c.setFont('Helvetica', 7)
        c.drawCentredString(qr_x + qr_taille / 2,
                            qr_y - 0.30 * cm,
                            'Vérifier ce certificat')

    # ══════════════════════════════════════════════════════════════
    # PIED DE PAGE : référence centrée dans la zone basse
    # ══════════════════════════════════════════════════════════════
    ref = f"Réf : NIM-CERT-{inscription.id:06d}-{date_fin.year}"
    c.setFillColor(GRIS_CLAIR)
    c.setFont('Helvetica', 8)
    c.drawCentredString(CX, zone_bas + 0.55 * cm, ref)

    c.setFont('Helvetica', 7.5)
    c.drawCentredString(CX, zone_bas + 0.15 * cm,
                        f'Numeria Institute · Lomé, Togo · {settings.CONTACT_EMAIL}')

    c.save()
    buffer.seek(0)
    return buffer.read()