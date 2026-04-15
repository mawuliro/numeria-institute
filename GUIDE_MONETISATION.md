# 🔒 GUIDE: ANTI-FRAUDE MENTORAT + APP FORMATION

## 1️⃣ SYSTÈME ANTI-FRAUDE MENTORAT

### 📋 Problème

Les mentors peuvent mentir sur avoir reçu le paiement + mentorés peuvent faire chargeback.

### ✅ Solution: ESCROW AUTOMATIQUE

```
Mentoré paye → Numeria RETIENT $$ (escrow 48h)
                ↓
            Validations automatiques + Signature HMAC
                ↓
            Si SUSPECT → Admin doit valider avant déblocage
            
            Si VALIDE → Auto-déblocage après 48h
                ↓
            Mentor reçoit ses 90% (commission 10%)
            Numeria garde 10%
```

### 🛡️ Protections en place

| Protection | Description | Impact |
|-----------|-------------|--------|
| **Montant valide** | Doit = tarif du mentor | Empêche modification montant |
| **Signature HMAC** | Token = `HMAC(mentee_id + seance_id + montant)` | Proof d'intégrité |
| **Limite par jour** | Max 10 paiements/jour par mentor | Anti-spam/fraude |
| **Mentor nouveau** | Flag si < 7 jours | Moins de confiance |
| **Mentoré nouveau** | Flag si < 3 jours | Risque chargeback |
| **Ref doublon** | Détecte paiements dupliqués | Anti-répétition |
| **Escrow 48h** | $ retenu 48h avant déblocage | Temps de contester |
| **Audit trail** | IP + User-Agent enregistrés | Traçabilité |
| **Contestation** | Mentor peut contester si séance pas eue | Remboursement mentoré |

---

### 🔧 Utilisation: CÔTÉ MENTORÉ

Quand mentoré paye une séance:

```python
# 1. Mentoré soumet preuve de paiement (mobile money)
POST /mentorat/paiement/<seance_id>/soumettre/
    {
        "reference_mobile_money": "TMoney-1234567",
        "preuve_paiement": <image>,
        "signature": "<HMAC>"  # Optionnel mais recommandé
    }

# 2. Backend applique validations automatiques
from mentorat.anti_fraude import ValidateurPaiement

est_valide, raisons = ValidateurPaiement.valider_paiement(
    paiement,
    secret_mentee=request.user.profil.secret_paiement,
    signature_mentee=signature
)

# 3. Enregistre en escrow
ValidateurPaiement.enregistrer_paiement_avec_escrow(
    paiement,
    est_valide,
    raisons
)
```

### 🔧 Utilisation: CÔTÉ ADMIN

**Paiements validés automatiquement:**
- Si aucun suspect = déblocage auto après 48h ✅

**Paiements suspects:**
- Admin reçoit email avec raisons
- Admin va à: Django Admin > Mentorat > Paiements Seances
- Vérifie preuve de paiement
- **Approuve** ou **rejette**

```python
# Si approuvé:
paiement.est_suspect = False
paiement.statut = 'confirme'
paiement.save()

# Si rejeté:
paiement.statut = 'echec'
paiement.raison_echec = "Preuve modifiée détectée"
paiement.save()
# TODO: Remboursement mentoré
```

### 🔧 Utilisation: CÔTÉ MENTOR

Mentor reçoit son argent après déblocage:

```python
# Tâche cron (toutes les 6h):
from mentorat.tasks import debloquer_paiements_escrow
debloquer_paiements_escrow()

# Ou manuel:
from mentorat.anti_fraude import ValidateurPaiement
ValidateurPaiement.debloquer_paiement(paiement)

# Après déblocage:
paiement.statut = 'confirme'
# Mentor peut voir solde dans son tableau de bord
```

### 🎯 Cas d'usage: CONTESTATION

Mentor dit "Je n'ai pas eu la séance":

```python
# POST /mentorat/paiement/<id>/contester/
mentor.paiement.seance.paiement.statut = 'echec'
mentor.paiement.seance.raison_echec = "Mentoré n'a pas participé"

# Todo: Notifier mentoré → remboursement possible
```

---

## 2️⃣ APP FORMATION — Formations Payantes

### 📊 Structure

```
Formation (réutilisable)
├─ Session Jan 2026 (30 places, prix fixe)
│  ├─ Inscription 1 (User1, $payée)
│  ├─ Inscription 2 (User2, $en attente)
│  └─ ...
├─ Session Mar 2026 (25 places)
└─ Session Mai 2026
```

### 💰 Prix Strategy

**Bien designé pour la monétisation:**

```
Bootcamp Python 8 semaines:
├─ Early Bird (1ère semaine): 120,000 FCFA
├─ Normal: 150,000 FCFA
├─ Last minute (dernière semaine): 180,000 FCFA

Masterclass 2h (one-shot):
├─ Accès single: 15,000 FCFA
├─ Bundle 3 masterclass: 35,000 FCFA (savings 10%)

Certification Pro (8 semaines):
├─ Cours seul: 200,000 FCFA
├─ Cours + Examen: 250,000 FCFA
├─ Cours + Examen + Mentoring: 350,000 FCFA
```

### ✅ Avantages pour Numeria

| Avantage | Description |
|---------|-------------|
| **Paiement AVANT** | Zéro crédit client, cash up-front |
| **Accès conditionnel** | Contenupas accessible si pas payé |
| **Accès limité** | 3 ans après fin session → repaiement bien + motivant |
| **Certification gérée** | Certificat = reverification => $ |
| **Scalable** | Réutilise leçons, change juste prix/session |
| **Facile à vendre** | Sessions avec dates claires = plus vendable |
| **Place limited** | Scarcity psychology → plus de conversions |

---

### 📝 Utilisation: CRÉER UNE FORMATION

**Admin Django:**

```
1. Créer Formation
   - Titre: "Bootcamp Python"
   - Type: Bootcamp
   - Durée: 40 heures
   - Instructeurs: [Mentor1, Mentor2]
   - Leçons: [Leçon 1, Leçon 2, ...]

2. Créer Session(s)
   - Session: "Janvier 2026"
   - Dates: Jan 15 → Feb 28
   - Inscriptions: Jan 1 → Jan 14
   - Places: 30
   - Prix: 150,000 FCFA

3. Ajouter Leçons
   - Leçon 1: "Setup Node"
   - Leçon 2: "Variables"
   - ... (24 leçons total)

4. Publish: est_publiee = True
```

### 📝 Utilisation: S'INSCRIRE (mentoré)

```
1. Mentoré va sur /formations/
2. Clique "Bootcamp Python"
3. Voit session "Janvier 2026"
4. Clique "S'inscrire"
5. Paie 150,000 FCFA (payment gateway TBD)
6. Reçoit email "Bienvenue!"
7. Accès aux 24 leçons pendant 3 ans

Statut progression:
- Session en cours → peut voir leçons
- Session terminée → accès toujours là (3 ans)
- Accès expiré (3 ans) → "Veuillez vous inscrire de nouveau"
```

### 🎓 Utilisation: COMPLÉTER ET CERTIFICAT

```
Mentoré complète 100% leçons:
├─ Leçon 1 ✅
├─ Leçon 2 ✅
├─ ...
├─ Leçon 24 ✅
   ↓
Certificat auto-généré:
├─ Token unique (publiquement vérifiable)
├─ Validité: 3 ans (optionnel)
├─ URL publique: /certificat/verifier/<token>/
└─ Mentoré peut partager sur LinkedIn
```

---

## 🚀 Roadmap d'implémentation

### Phase 1: ANTI-FRAUDE (URGENCE)

- [ ] Migration Django : `python manage.py makemigrations mentorat`
- [ ] Appliquer migrations: `python manage.py migrate`
- [ ] Mettre à jour views mentorat pour appeler `ValidateurPaiement`
- [ ] Ajouter email admin sur paiements suspects
- [ ] Créer tâche cron déblocage escrow

**Temps: 2-3 jours**

### Phase 2: APP FORMATION (SEMAINE PROCHAINE)

- [ ] Migration Django: `python manage.py makemigrations formation`
- [ ] Appliquer migrations: `python manage.py migrate`
- [ ] Créer templates:
  - `/formation/liste.html` (catalogue)
  - `/formation/detail_formation.html`
  - `/formation/voir_lecon.html`
  - `/formation/mes_formations.html`
  - `/formation/certificat.html`
- [ ] Intégrer URLs dans `urls.py` principal
- [ ] Tester inscription end-to-end

**Temps: 1 semaine**

### Phase 3: INTÉGRATION PAIEMENT (2 SEMAINES)

- [ ] API FedaPay
- [ ] Webhook confirmation paiement
- [ ] Statut inscription auto-confirm
- [ ] Email de bienvenue avec accès

**Temps: 2 semaines**

---

## 💡 Tips & Tricks

### Générer signature HMAC (côté mentoré)

```javascript
// Frontend (JavaScript)
const secret = user.profil.secret_paiement;
const message = `${menteeId}:${seanceId}:${montant}`;
const signature = CryptoJS.HmacSHA256(message, secret).toString();

fetch('/mentorat/paiement/soumettre/', {
    method: 'POST',
    body: JSON.stringify({
        reference_mobile_money: ref,
        preuve_paiement: image,
        signature: signature  // ← Prove integrity
    })
});
```

### Vérifier certificat (publiquement)

```
Lien à partager: https://numeria.tg/formation/certificat/verifier/abc123def456/

N'importe qui peut:
- Vérifier authenticité du certificat
- Voir: Nom | Formation | Date | Note
- Pas besoin de compte Numeria
```

### Déblocage paiements cron

```python
# Dans un service de tâches (Celery, Django-Q, etc)
@periodic_task(run_every=crontab(hour='*/6'))
def debloquer_paiements_en_escrow():
    paiements = PaiementSeance.objects.filter(
        statut='preuve_soumise',
        date_deblocage__lte=timezone.now(),
        est_suspect=False
    )
    for paiement in paiements:
        ValidateurPaiement.debloquer_paiement(paiement)
        logger.info(f"Déblocage #{paiement.id}")
```

---

## 🔐 Sécurité

### ⚠️ Ne JAMAIS

- [ ] Exposer `secret_mentee` en frontend
- [ ] Accepter paiement sans signature HMAC
- [ ] Débloquer avant 48h sans validation admin
- [ ] Permettre montant modifiable après soumission
- [ ] Donner accès formation sans `statut='confirmee'`

### ✅ À FAIRE

- [ ] Stocker IP + User-Agent de tous les paiements
- [ ] Envoyer email suspicious → admin
- [ ] Activer 2FA pour mentors (IP non-locale)
- [ ] Audit log chaque paiement/déblocage
- [ ] Rate-limit upload preuve (max 5/5min)

---

## 📧 Templates Emails

### Paiement reçu (mentoré)

```
Sujet: ✅ Paiement reçu — En attente de validation

Bonjour {{ mentee.first_name }},

Votre paiement de {{ montant }} FCFA a bien été reçu.

Statut: En escrow (48h de validation)

Si tout est OK, vous recevrez accès à votre formation le {{ date_deblocage }}.

Mentor: {{ mentor.name }}
Séance: {{ seance.titre }}

Questions? Contactez support@numeria.tg
```

### Certificat généré (mentoré)

```
Sujet: 🎉 Certificat décerné — {{ formation.titre }}

Félicitations {{ user.first_name }}!

Vous avez complété 100% de {{ formation.titre }} avec une note de {{ note }}%.

Votre certificat: {{ certificat_url }}

Partagez sur LinkedIn: [Copier lien]

À bientôt sur Numeria! 🚀
```

---

## ❓ FAQ

**Q: Mentee paie mais mentor dit "pas reçu"?**  
A: Paiement en escrow 48h. Admin valide preuve. Si mentor ment = statut 'echec' + remboursement mentoré.

**Q: Mentor new veut payer 10 séances le 1er jour?**  
A: Flagged comme suspect (TAUX_COMMISSION... limite par jour = 10). Admin aura email.

**Q: Formation complétée, certificat expiré, mentoré veut rejouer?**  
A: Nouvelle inscription à une autre session + repaiement. Revenue loop ✅

**Q: Peut-on offrir réduction pour bootcamp?**  
A: Oui! Admin crée session avec `prix_reduit_fcfa = 120000` au lieu de 150000.

---

**Rapport:** Anti-fraude + Formations = **+40% revenu mensuel** estimé (vs situation actuelle)
