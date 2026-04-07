from django import forms
from .models import Sujet, Message, ProfilUtilisateur

class SujetForm(forms.ModelForm):
    contenu = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10, 'placeholder': 'Décrivez votre sujet...'}),
        label='Message initial'
    )

    class Meta:
        model = Sujet
        fields = ['titre', 'categorie', 'contenu']
        widgets = {
            'titre': forms.TextInput(attrs={'placeholder': 'Titre de votre sujet'}),
        }

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['contenu']
        widgets = {
            'contenu': forms.Textarea(attrs={
                'rows': 8,
                'placeholder': 'Votre réponse...'
            }),
        }
        labels = {
            'contenu': 'Message',
        }

class ProfilUtilisateurForm(forms.ModelForm):
    class Meta:
        model = ProfilUtilisateur
        fields = ['avatar', 'bio', 'specialisation', 'niveau_etudes', 'site_web']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Parlez-nous de vous...'}),
            'specialisation': forms.TextInput(attrs={'placeholder': 'Ex: Mathématiques, Physique...'}),
            'site_web': forms.URLInput(attrs={'placeholder': 'https://...'}),
        }