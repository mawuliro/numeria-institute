from django import forms
from .models import Mentor, Mentee, DemandeMentorat, SeanceMentorat, PaiementSeance


class InscriptionMentorForm(forms.ModelForm):
    """
    Formulaire d'inscription en tant que mentor.
    """
    class Meta:
        model = Mentor
        fields = [
            'domaines_expertise',
            'niveau_experience',
            'disponibilite',
            'tarif_par_seance',
            'bio_mentorat',
        ]
        widgets = {
            'bio_mentorat': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Décrivez votre parcours, vos expériences, et vos motivations à devenir mentor...'
            }),
            'tarif_par_seance': forms.NumberInput(attrs={
                'min': 0,
                'placeholder': '0',
            }),
        }
        help_texts = {
            'tarif_par_seance': 'Laissez 0 si votre mentorat est gratuit. Numeria prélève 20% de commission sur chaque séance payante.',
        }


class PaiementSeanceForm(forms.ModelForm):
    """
    Soumission de preuve de paiement mobile money.
    """
    class Meta:
        model = PaiementSeance
        fields = ['reference_mobile_money', 'preuve_paiement']
        widgets = {
            'reference_mobile_money': forms.TextInput(attrs={
                'placeholder': 'Ex: TM2504120001...',
            }),
        }


class InscriptionMenteeForm(forms.ModelForm):
    """
    Formulaire d'inscription en tant que mentoré.
    """
    class Meta:
        model = Mentee
        fields = [
            'objectifs',
            'niveau_etudes',
            'besoins'
        ]
        widgets = {
            'besoins': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Décrivez vos objectifs, vos difficultés actuelles, et ce que vous attendez de votre mentor...'
            }),
        }


class DemandeMentoratForm(forms.ModelForm):
    """
    Formulaire pour faire une demande de mentorat.
    """
    class Meta:
        model = DemandeMentorat
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Présentez-vous brièvement et expliquez pourquoi vous souhaitez ce mentor...'
            }),
        }


class SeanceMentoratForm(forms.ModelForm):
    """
    Formulaire pour planifier une séance de mentorat.
    """
    class Meta:
        model = SeanceMentorat
        fields = [
            'titre',
            'description',
            'date_heure',
            'duree_minutes',
            'modalite'
        ]
        widgets = {
            'date_heure': forms.DateTimeInput(attrs={
                'type': 'datetime-local'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Description de la séance...'
            }),
        }


class TerminerSeanceForm(forms.Form):
    """
    Formulaire pour terminer une séance avec des notes.
    """
    notes_mentor = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Vos notes sur la séance...'
        }),
        label="Notes du mentor"
    )

    notes_mentee = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Vos notes sur la séance...'
        }),
        label="Notes du mentoré"
    )