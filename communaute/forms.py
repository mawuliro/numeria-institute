from django import forms
from .models import Categorie, Sujet, Message, ProfilUtilisateur

class CategorieForm(forms.ModelForm):
    class Meta:
        model = Categorie
        fields = ['nom', 'description', 'ordre', 'est_active']
        widgets = {
            'nom': forms.TextInput(attrs={'placeholder': 'Nom de la catégorie', 'class': 'w-full rounded-xl border border-gray-300 px-4 py-3'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Description de la catégorie', 'class': 'w-full rounded-xl border border-gray-300 px-4 py-3'}),
            'ordre': forms.NumberInput(attrs={'class': 'w-full rounded-xl border border-gray-300 px-4 py-3'}),
        }
        labels = {
            'nom': 'Nom de la catégorie',
            'description': 'Description',
            'ordre': 'Ordre d’affichage',
            'est_active': 'Activer la catégorie',
        }

class SujetForm(forms.ModelForm):
    categorie = forms.ModelChoiceField(
        queryset=Categorie.objects.filter(est_active=True),
        empty_label='Sélectionnez une catégorie',
        widget=forms.Select(attrs={'class': 'w-full rounded-xl border border-gray-300 px-4 py-3'}),
        label='Catégorie'
    )

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

    def __init__(self, *args, **kwargs):
        categorie_initial = kwargs.pop('categorie_initial', None)
        super().__init__(*args, **kwargs)
        self.fields['categorie'].queryset = Categorie.objects.filter(est_active=True)
        if categorie_initial is not None:
            self.fields['categorie'].initial = categorie_initial

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