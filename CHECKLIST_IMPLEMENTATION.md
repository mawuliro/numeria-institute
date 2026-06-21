# ✅ CHECKLIST IMPLÉMENTATION

## 🔴 URGENT — Phase 1: Base données

### Step 1: Générer migrations
```bash
cd /home/roland/Projets/numeria
python manage.py makemigrations mentorat formation
```

**À faire:** Revoir les migrations avant appliquer
- [ ] Check `mentorat/0004_*.py` — 9 nouveaux champs PaiementSeance
- [ ] Check `formation/0001_*.py` — 6 nouveaux modèles

### Step 2: Appliquer migrations
```bash
python manage.py migrate
```

**Résultat:** Tables création + colonnes escrow

---

## 🟡 MOYEN — Phase 2: Formations (templates)

### Templates à créer

**1. `/home/roland/Projets/numeria/formation/templates/formation/liste.html`**
```html
{% extends 'base.html' %}
{% load i18n %}

{% block title %}{% trans "Formations" %}{% endblock %}

{% block content %}
<div class="container">
  <h1>{% trans "Formations" %}</h1>
  
  <!-- Filtres -->
  <div class="filters">
    <select name="type">
      <option value="">Tous types</option>
      <option value="Bootcamp">Bootcamp</option>
      <option value="Masterclass">Masterclass</option>
    </select>
  </div>
  
  <!-- Liste -->
  <div class="formations-grid">
    {% for formation in formations %}
      <div class="card">
        <h3>{{ formation.titre }}</h3>
        <p>{{ formation.description|truncatewords:20 }}</p>
        <p>{{ formation.duree }} heures | Niveau: {{ formation.niveau }}</p>
        
        <!-- Session suiv. -->
        {% with session=formation.prochaine_session %}
          {% if session %}
            <p><strong>Prochaine:</strong> {{ session.date_debut|date:"d/m/Y" }}</p>
            <p>{{ session.places_disponibles }}/{{ session.places_totales }} places</p>
            <a href="{% url 'formation:session_detail' session.id %}">Voir détails</a>
          {% else %}
            <p class="text-gray">Pas de session à venir</p>
          {% endif %}
        {% endwith %}
      </div>
    {% endfor %}
  </div>
</div>
{% endblock %}
```

**2. `/home/roland/Projets/numeria/formation/templates/formation/detail_formation.html`**
```html
{% extends 'base.html' %}
{% load i18n %}

{% block title %}{{ formation.titre }}{% endblock %}

{% block content %}
<div class="container">
  <h1>{{ formation.titre }}</h1>
  
  <div class="formation-info">
    <p>{{ formation.description }}</p>
    <p><strong>Durée:</strong> {{ formation.duree }} heures</p>
    <p><strong>Niveau:</strong> {{ formation.niveau }}</p>
    <p><strong>Instructeurs:</strong> 
      {% for instr in formation.instructeurs.all %}
        {{ instr.prenom }} {{ instr.nom }}
      {% endfor %}
    </p>
  </div>
  
  <h2>{% trans "Sessions disponibles" %}</h2>
  <div class="sessions">
    {% for session in formation.sessions_actives %}
      <div class="session-card">
        <p><strong>{{ session.date_debut|date:"d/m/Y" }} → {{ session.date_fin|date:"d/m/Y" }}</strong></p>
        <p>Format: {{ session.format }}</p>
        <p>{{ session.places_disponibles }}/{{ session.places_totales }} {% trans "places" %}</p>
        <p><strong>Prix:</strong> {{ session.prix_fcfa|floatformat:0 }} FCFA</p>
        
        {% if session.est_ouverte_aux_inscriptions %}
          <a href="{% url 'formation:inscrire' session.id %}" class="btn btn-primary">
            {% trans "S'inscrire" %}
          </a>
        {% else %}
          <p class="text-gray">{% trans "Inscriptions fermées" %}</p>
        {% endif %}
      </div>
    {% endfor %}
  </div>
  
  <!-- Leçons preview -->
  <h2>{% trans "Contenu du cours" %}</h2>
  <ul class="lessons">
    {% for lecon in formation.leconformation_set.all %}
      <li>
        <strong>{{ lecon.titre }}</strong>
        {% if lecon.duree_estimee %} — {{ lecon.duree_estimee }} min{% endif %}
      </li>
    {% endfor %}
  </ul>
</div>
{% endblock %}
```

**3. `/home/roland/Projets/numeria/formation/templates/formation/mes_formations.html`**
```html
{% extends 'base.html' %}
{% load i18n %}

{% block title %}{% trans "Mes formations" %}{% endblock %}

{% block content %}
<div class="container">
  <h1>{% trans "Mes formations" %}</h1>
  
  <div class="formations-list">
    {% for inscription in inscriptions %}
      <div class="inscription-card">
        <h3>{{ inscription.session_formation.formation.titre }}</h3>
        
        <!-- Statut paiement -->
        <p>
          Statut:
          {% if inscription.statut == "confirmee" %}
            <span class="badge green">✅ {% trans "Payée" %}</span>
          {% else %}
            <span class="badge red">⏳ {% trans "En attente" %}</span>
          {% endif %}
        </p>
        
        <!-- Progression -->
        <div class="progress-bar">
          <div class="progress" style="width: {{ inscription.progression_pct }}%"></div>
        </div>
        <p>{{ inscription.progression_pct }}% {% trans "complété" %}</p>
        
        <!-- Boutons -->
        {% if inscription.a_acces %}
          <a href="{% url 'formation:mes_formations' %}" class="btn btn-primary">
            {% trans "Continuer" %}
          </a>
        {% else %}
          <p class="text-gray">{% trans "Paiement en attente" %}</p>
        {% endif %}
        
        <!-- Certificat -->
        {% if inscription.progression_pct == 100 %}
          <a href="{% url 'formation:certificat_detail' inscription.certificat.id %}" class="btn btn-success">
            🎓 {% trans "Certificat" %}
          </a>
        {% endif %}
      </div>
    {% endfor %}
  </div>
</div>
{% endblock %}
```

**4. `/home/roland/Projets/numeria/formation/templates/formation/voir_lecon.html`**
```html
{% extends 'base.html' %}
{% load i18n %}

{% block title %}{{ lecon.titre }}{% endblock %}

{% block content %}
<div class="container">
  <!-- Navigation -->
  <div class="lesson-nav">
    {% if lecon_prev %}
      <a href="{% url 'formation:voir_lecon' lecon_prev.id %}" class="btn-prev">← {% trans "Précédent" %}</a>
    {% endif %}
    
    <span>{{ lecon.numero }}/{{ total_lecons }}</span>
    
    {% if lecon_next %}
      <a href="{% url 'formation:voir_lecon' lecon_next.id %}" class="btn-next">{% trans "Suivant" %} →</a>
    {% endif %}
  </div>
  
  <!-- Contenu -->
  <div class="lesson-content">
    <h1>{{ lecon.titre }}</h1>
    
    <!-- HTML content -->
    <div class="html-content">
      {{ lecon.contenu_html|safe }}
    </div>
    
    <!-- Vidéo si existe -->
    {% if lecon.url_video %}
      <div class="video-container">
        {% if "youtube" in lecon.url_video %}
          <iframe width="100%" height="450" src="{{ lecon.url_video }}" frameborder="0" allowfullscreen></iframe>
        {% elif "vimeo" in lecon.url_video %}
          <iframe src="{{ lecon.url_video }}" width="100%" height="450" frameborder="0" allow="autoplay; fullscreen" allowfullscreen></iframe>
        {% endif %}
      </div>
    {% endif %}
    
    <!-- Ressources -->
    {% if lecon.ressources %}
      <div class="resources">
        <h3>{% trans "Ressources" %}</h3>
        <ul>
          {% for ressource in lecon.ressources %}
            <li><a href="{{ ressource.url }}" download>{{ ressource.nom }}</a></li>
          {% endfor %}
        </ul>
      </div>
    {% endif %}
  </div>
  
  <!-- Marquer complétée -->
  <form method="post" action="{% url 'formation:voir_lecon' lecon.id %}">
    {% csrf_token %}
    <button type="submit" name="mark_complete" class="btn btn-success" style="display:{% if progression.date_completion %}none{% endif %}">
      ✅ {% trans "Marquer complétée" %}
    </button>
  </form>
</div>
{% endblock %}
```

**5. `/home/roland/Projets/numeria/formation/templates/formation/certificat.html`**
```html
{% extends 'base.html' %}
{% load i18n %}

{% block title %}{% trans "Certificat" %}{% endblock %}

{% block content %}
<div class="certificate-container">
  <div class="certificate">
    <h1>{% trans "CERTIFICAT D'ACCOMPLISSEMENT" %}</h1>
    
    <p>{% trans "Ce certificat est décerné à" %}</p>
    <h2>{{ inscrit.user.get_full_name }}</h2>
    
    <p>{% trans "Pour avoir complété avec succès" %}</p>
    <h3>{{ certificat.inscription.session_formation.formation.titre }}</h3>
    
    <p>{% trans "Délivré le" %} <strong>{{ certificat.date_delivrance|date:"d/m/Y" }}</strong></p>
    
    <p>{% trans "Code de vérification:" %} <code>{{ certificat.token_verification }}</code></p>
    
    <p><small>{% trans "Vérifier l'authenticité:" %} 
      <a href="{% url 'formation:certificat_verifier' certificat.token_verification %}">
        {{ request.build_absolute_uri certificat.get_verification_url }}
      </a>
    </small></p>
  </div>
  
  <div class="actions">
    <button onclick="window.print()" class="btn btn-primary">🖨️ {% trans "Imprimer" %}</button>
    <a href="{% url 'formation:mes_formations' %}" class="btn btn-secondary">{% trans "Retour" %}</a>
  </div>
</div>

<style>
.certificate-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}

.certificate {
  border: 3px solid #gold;
  padding: 40px;
  text-align: center;
  background: linear-gradient(to bottom, #fffef5, #fff9e6);
  font-family: Georgia, serif;
  min-height: 600px;
  display: flex;
  flex-direction: column;
  justify-content: space-around;
}

.certificate h1 {
  font-size: 32px;
  margin: 20px 0;
}

.certificate h2 {
  font-size: 28px;
  margin: 30px 0;
}
</style>
{% endblock %}
```

---

## 🟠 MOYEN — Phase 3: Configuration URLs

### Mettre à jour `/home/roland/Projets/numeria/numeria_project/urls.py`

Ajouter avant `urlpatterns`:
```python
from django.urls import path, include

urlpatterns = [
    # ... existant ...
    path('formation/', include('formation.urls', namespace='formation')),
]
```

Vérifier que URLs formation sont dans `/home/roland/Projets/numeria/formation/urls.py` ✅ (déjà créé)

---

## 🟠 MOYEN — Phase 4: Intégration anti-fraude

### Mettre à jour `/home/roland/Projets/numeria/mentorat/views.py`

Ajouter vue pour soumettre paiement:

```python
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from mentorat.anti_fraude import ValidateurPaiement
from mentorat.models import PaiementSeance
import hmac
import hashlib

@login_required
def soumettre_paiement(request, paiement_id):
    """Mentoré soumet preuve de paiement avec signature HMAC"""
    
    paiement = get_object_or_404(PaiementSeance, pk=paiement_id, mentee=request.user)
    
    if request.method == 'POST':
        reference = request.POST.get('reference_mobile_money')
        signature = request.POST.get('signature')
        preuve = request.FILES.get('preuve_paiement')
        
        # Valider signature
        est_valide, raisons = ValidateurPaiement.valider_paiement(
            paiement,
            signature_mentee=signature
        )
        
        # Enregistrer en escrow
        ValidateurPaiement.enregistrer_paiement_avec_escrow(
            paiement,
            est_valide,
            raisons
        )
        
        if est_valide:
            messages.success(request, "✅ Paiement reçu. Validation dans 48h.")
        else:
            messages.warning(request, f"⚠️ Paiement flagged: {', '.join(raisons)}")
        
        return redirect('mentorat:mes_seances')
    
    # GET: Afficher formulaire
    secret = request.user.profil.secret_paiement
    message = f"{request.user.id}:{paiement.seance.id}:{paiement.montant_fcfa}"
    signature_recommandee = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return render(request, 'mentorat/paiement.html', {
        'paiement': paiement,
        'signature_recommandee': signature_recommandee
    })
```

### Ajouter URL:
```python
# Dans mentorat/urls.py
path('paiement/<int:paiement_id>/soumettre/', views.soumettre_paiement, name='soumettre_paiement'),
```

---

## 🟢 FACILE — Phase 5: Tâche périodique (cron)

### Créer `/home/roland/Projets/numeria/mentorat/tasks.py`

```python
from django.core.mail import send_mail
from django.utils import timezone
from mentorat.anti_fraude import ValidateurPaiement
from mentorat.models import PaiementSeance
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

def debloquer_paiements_escrow():
    """
    Cron task (toutes les 6h): Débloquer paiements après 48h sans contestation
    """
    maintenant = timezone.now()
    limite = maintenant - timedelta(hours=48)
    
    paiements = PaiementSeance.objects.filter(
        statut='preuve_soumise',
        date_deblocage__lte=limite,
        est_suspect=False
    )
    
    for paiement in paiements:
        ValidateurPaiement.debloquer_paiement(paiement)
        logger.info(f"✅ Déblocage paiement #{paiement.id}")
    
    return f"Déblocage: {len(paiements)} paiements"
```

### Configurer dans `settings.py`:

```python
if not DEBUG:
    # Celery Beat schedule
    from celery.schedules import crontab
    
    CELERY_BEAT_SCHEDULE = {
        'debloquer-paiements': {
            'task': 'mentorat.tasks.debloquer_paiements_escrow',
            'schedule': crontab(minute=0, hour='*/6'),  # Chaque 6h
        },
    }
```

---

## ✅ CHECKLIST FINALE

- [ ] `python manage.py makemigrations mentorat formation`
- [ ] `python manage.py migrate`
- [ ] Créer 5 templates formation
- [ ] Vérifier formation URLs dans `numeria_project/urls.py`
- [ ] Ajouter `soumettre_paiement()` view + URL mentorat
- [ ] Créer `mentorat/tasks.py` cron
- [ ] Tester end-to-end:
  - [ ] Mentoré paie une formation
  - [ ] Paiement en escrow 48h
  - [ ] Accès aux leçons verouillé jusqu'à confirmation
  - [ ] Déverrouillage automatique après 48h
  - [ ] Certificat généré auto à 100%

---

**Prochaine étape à faire:** Exécuter les migrations (Phase 1)
