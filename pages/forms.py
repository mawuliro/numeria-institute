from django import forms
from django.utils.translation import gettext_lazy as _


class FormulaireContact(forms.Form):
    """Formulaire de contact de la page Contact."""

    SUJETS = [
        ('', _('— Choisir un sujet —')),
        ('information', _("Demande d'information")),
        ('inscription', _('Inscription aux filières')),
        ('partenariat', _('Proposition de partenariat')),
        ('presse', _('Contact presse / média')),
        ('technique', _('Problème technique')),
        ('autre', _('Autre')),
    ]

    nom_complet = forms.CharField(
        label=_('Nom complet'),
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': _('Votre nom et prénom'),
        })
    )

    email = forms.EmailField(
        label=_('Adresse email'),
        widget=forms.EmailInput(attrs={
            'placeholder': 'votre@email.com',
        })
    )

    organisation = forms.CharField(
        label=_('Organisation / Université'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': _('Optionnel — Ex: Université de Lomé'),
        })
    )

    sujet = forms.ChoiceField(
        label=_('Sujet'),
        choices=SUJETS,
    )

    message = forms.CharField(
        label=_('Message'),
        min_length=20,
        widget=forms.Textarea(attrs={
            'placeholder': _('Écrivez votre message ici...'),
            'rows': 6,
        })
    )

    est_partenaire = forms.BooleanField(
        label=_("Je souhaite discuter d'un partenariat avec Numeria Institute"),
        required=False,
    )