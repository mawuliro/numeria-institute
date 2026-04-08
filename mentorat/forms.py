from django import forms
from django.contrib.auth.models import User
from .models import Mentor, Mentee, DemandeMentorat, SeanceMentorat


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
            'bio_mentorat'
        ]
        widgets = {
            'bio_mentorat': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Décrivez votre parcours, vos expériences, et vos motivations à devenir mentor...'
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