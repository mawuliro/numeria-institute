# admissions/forms.py
from django import forms
from .models import Candidature, CampagneRecrutement
from django.forms import DateInput


class FormulaireCandidature(forms.ModelForm):
    """Formulaire de candidature complet"""
    
    class Meta:
        model = Candidature
        fields = [
            # Informations personnelles
            'nom', 'prenom', 'sexe', 'date_naissance', 'lieu_naissance', 
            'nationalite', 'telephone', 'email_personnel', 'adresse', 
            'pays', 'ville',
            # Parcours académique
            'dernier_etablissement', 'niveau_etudes', 'diplome_obtenu', 
            'annee_obtention', 'moyenne_generale',
            # Documents
            'cv', 'lettre_motivation', 'releves_notes', 'autres_documents',
            # Questions
            'motivation', 'experiences', 'competences', 'source',
        ]
        widgets = {
            'date_naissance': DateInput(attrs={'type': 'date'}),
            'motivation': forms.Textarea(attrs={'rows': 5}),
            'experiences': forms.Textarea(attrs={'rows': 4}),
            'competences': forms.Textarea(attrs={'rows': 4}),
            'adresse': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ajouter des classes CSS
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 focus:outline-none focus:border-numeria-teal'
        
        # Placeholders
        self.fields['nom'].widget.attrs['placeholder'] = 'Votre nom'
        self.fields['prenom'].widget.attrs['placeholder'] = 'Votre prénom'
        self.fields['telephone'].widget.attrs['placeholder'] = '+228 XX XX XX XX'
        self.fields['email_personnel'].widget.attrs['placeholder'] = 'votre@email.com'
        self.fields['ville'].widget.attrs['placeholder'] = 'Lomé'
        self.fields['dernier_etablissement'].widget.attrs['placeholder'] = 'Nom de votre école/université'
        self.fields['niveau_etudes'].widget.attrs['placeholder'] = 'Ex: Licence 3, Master 1, Baccalauréat...'
        
        # Labels plus courts
        self.fields['cv'].label = "CV (PDF)"
        self.fields['lettre_motivation'].label = "Lettre de motivation (PDF)"
        self.fields['releves_notes'].label = "Relevés de notes (PDF)"
        self.fields['motivation'].label = "Pourquoi souhaitez-vous intégrer cette formation ?"