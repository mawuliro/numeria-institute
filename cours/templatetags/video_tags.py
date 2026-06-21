from django import template
from cours.models import convertir_url_youtube, extraire_id_youtube

register = template.Library()


@register.filter
def youtube_embed(url):
    """Convert a YouTube/Vimeo URL to an embed URL for iframes."""
    if not url:
        return ''
    return convertir_url_youtube(url.strip())


@register.inclusion_tag('cours/composants/lecteur_video.html')
def lecteur_video(url, titre='', hauteur='400px', autoplay=False):
    """
    Tag template pour afficher une vidéo YouTube ou Vimeo.

    Usage dans les templates :
        {% load video_tags %}
        {% lecteur_video lecon.video_youtube titre=lecon.titre %}
        {% lecteur_video cours.video_youtube titre=cours.titre autoplay=True %}

    Le tag reçoit l'URL originale (stockée en base) et la convertit
    en URL embed ici, à l'affichage — jamais en base de données.
    """
    if not url:
        return {'url': None}

    url = url.strip()

    # Convertit l'URL originale en URL embed
    embed_url  = convertir_url_youtube(url)

    # Extrait l'ID YouTube pour la miniature et le JS
    id_youtube = extraire_id_youtube(url)

    # URL de miniature YouTube (qualité max, repli sur hqdefault)
    miniature = None
    if id_youtube:
        miniature = f'https://img.youtube.com/vi/{id_youtube}/maxresdefault.jpg'

    # Ajouter autoplay si demandé
    # On vérifie si '?' est déjà présent pour choisir le bon séparateur
    if autoplay and embed_url:
        separateur = '&' if '?' in embed_url else '?'
        embed_url  = f'{embed_url}{separateur}autoplay=1&mute=1'

    # CORRIGÉ : détecter YouTube sur TOUS les formats d'URL
    # (youtube.com, youtu.be, youtube-nocookie.com, m.youtube.com)
    url_lower  = url.lower()
    est_youtube = (
        'youtube.com' in url_lower
        or 'youtu.be' in url_lower
        or 'youtube-nocookie.com' in url_lower
    )
    est_vimeo = 'vimeo.com' in url_lower

    return {
        'url':           embed_url,
        'url_originale': url,
        'miniature':     miniature,
        'titre':         titre,
        'hauteur':       hauteur,
        'est_youtube':   est_youtube,
        'est_vimeo':     est_vimeo,
        'id_youtube':    id_youtube,
    }