from django import forms


class FormulaireContact(forms.Form):
    """Formulaire de contact de la page Contact."""

    SUJETS = [
        ('', '— Choisir un sujet —'),
        ('information', 'Demande d\'information'),
        ('inscription', 'Inscription aux filières'),
        ('partenariat', 'Proposition de partenariat'),
        ('presse', 'Contact presse / média'),
        ('technique', 'Problème technique'),
        ('autre', 'Autre'),
    ]

    nom_complet = forms.CharField(
        label='Nom complet',
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Votre nom et prénom',
        })
    )

    email = forms.EmailField(
        label='Adresse email',
        widget=forms.EmailInput(attrs={
            'placeholder': 'votre@email.com',
        })
    )

    organisation = forms.CharField(
        label='Organisation / Université',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Optionnel — Ex: Université de Lomé',
        })
    )

    sujet = forms.ChoiceField(
        label='Sujet',
        choices=SUJETS,
    )

    message = forms.CharField(
        label='Message',
        min_length=20,
        widget=forms.Textarea(attrs={
            'placeholder': 'Écrivez votre message ici...',
            'rows': 6,
        })
    )

    # Case à cocher pour les partenariats
    est_partenaire = forms.BooleanField(
        label='Je souhaite discuter d\'un partenariat avec Numeria Institute',
        required=False,
    )