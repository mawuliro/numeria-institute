from django import forms
from .models import InscriptionFormation


class FormulairInscriptionFormation(forms.ModelForm):
    """
    Formulaire d'inscription à une session de formation.
    
    Le prix est calculé automatiquement et ne peut pas être changé.
    """
    class Meta:
        model = InscriptionFormation
        fields = []  # Aucun champ — tout est auto

    def __init__(self, session, etudiant, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session
        self.etudiant = etudiant
        self.fields['prix_paye_fcfa'] = forms.IntegerField(
            initial=session.prix_reduit_fcfa or session.prix_fcfa,
            disabled=True,
            label='Prix (FCFA)',
            widget=forms.HiddenInput()
        )

    def save(self, commit=True):
        inscription = super().save(commit=False)
        inscription.session = self.session
        inscription.etudiant = self.etudiant
        inscription.prix_paye_fcfa = self.session.prix_reduit_fcfa or self.session.prix_fcfa
        inscription.statut = 'en_attente'  # Paiement requis
        if commit:
            inscription.save()
        return inscription
