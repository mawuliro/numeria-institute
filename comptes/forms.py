from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profil

# Liste complète des pays francophones et africains en priorité
PAYS_CHOICES = [
    ('', '🌍 Sélectionner votre pays'),
    # ── Afrique de l\'Ouest (priorité) ──────────────────────────────
    ('Togo', '🇹🇬 Togo'),
    ('Bénin', '🇧🇯 Bénin'),
    ('Ghana', '🇬🇭 Ghana'),
    ('Côte d\'Ivoire', '🇨🇮 Côte d\'Ivoire'),
    ('Sénégal', '🇸🇳 Sénégal'),
    ('Mali', '🇲🇱 Mali'),
    ('Burkina Faso', '🇧🇫 Burkina Faso'),
    ('Niger', '🇳🇪 Niger'),
    ('Guinée', '🇬🇳 Guinée'),
    ('Sierra Leone', '🇸🇱 Sierra Leone'),
    ('Liberia', '🇱🇷 Liberia'),
    ('Gambie', '🇬🇲 Gambie'),
    ('Guinée-Bissau', '🇬🇼 Guinée-Bissau'),
    ('Cap-Vert', '🇨🇻 Cap-Vert'),
    ('Mauritanie', '🇲🇷 Mauritanie'),
    ('Nigeria', '🇳🇬 Nigeria'),
    # ── Afrique Centrale ────────────────────────────────────────────
    ('Cameroun', '🇨🇲 Cameroun'),
    ('Congo', '🇨🇬 Congo'),
    ('RD Congo', '🇨🇩 RD Congo'),
    ('Gabon', '🇬🇦 Gabon'),
    ('Tchad', '🇹🇩 Tchad'),
    ('République Centrafricaine', '🇨🇫 République Centrafricaine'),
    ('Guinée Équatoriale', '🇬🇶 Guinée Équatoriale'),
    ('São Tomé-et-Príncipe', '🇸🇹 São Tomé-et-Príncipe'),
    ('Burundi', '🇧🇮 Burundi'),
    ('Rwanda', '🇷🇼 Rwanda'),
    # ── Afrique de l\'Est ───────────────────────────────────────────
    ('Éthiopie', '🇪🇹 Éthiopie'),
    ('Kenya', '🇰🇪 Kenya'),
    ('Tanzanie', '🇹🇿 Tanzanie'),
    ('Ouganda', '🇺🇬 Ouganda'),
    ('Mozambique', '🇲🇿 Mozambique'),
    ('Madagascar', '🇲🇬 Madagascar'),
    ('Comores', '🇰🇲 Comores'),
    ('Djibouti', '🇩🇯 Djibouti'),
    ('Érythrée', '🇪🇷 Érythrée'),
    ('Somalie', '🇸🇴 Somalie'),
    # ── Afrique du Nord ─────────────────────────────────────────────
    ('Maroc', '🇲🇦 Maroc'),
    ('Algérie', '🇩🇿 Algérie'),
    ('Tunisie', '🇹🇳 Tunisie'),
    ('Libye', '🇱🇾 Libye'),
    ('Égypte', '🇪🇬 Égypte'),
    # ── Afrique du Sud ──────────────────────────────────────────────
    ('Afrique du Sud', '🇿🇦 Afrique du Sud'),
    ('Zimbabwe', '🇿🇼 Zimbabwe'),
    ('Zambie', '🇿🇲 Zambie'),
    ('Angola', '🇦🇴 Angola'),
    ('Namibie', '🇳🇦 Namibie'),
    ('Botswana', '🇧🇼 Botswana'),
    ('Malawi', '🇲🇼 Malawi'),
    ('Lesotho', '🇱🇸 Lesotho'),
    ('Eswatini', '🇸🇿 Eswatini'),
    # ── Europe ──────────────────────────────────────────────────────
    ('France', '🇫🇷 France'),
    ('Belgique', '🇧🇪 Belgique'),
    ('Suisse', '🇨🇭 Suisse'),
    ('Canada', '🇨🇦 Canada'),
    ('Luxembourg', '🇱🇺 Luxembourg'),
    ('Allemagne', '🇩🇪 Allemagne'),
    ('Royaume-Uni', '🇬🇧 Royaume-Uni'),
    ('Espagne', '🇪🇸 Espagne'),
    ('Italie', '🇮🇹 Italie'),
    ('Portugal', '🇵🇹 Portugal'),
    ('Pays-Bas', '🇳🇱 Pays-Bas'),
    # ── Amériques ───────────────────────────────────────────────────
    ('États-Unis', '🇺🇸 États-Unis'),
    ('Haïti', '🇭🇹 Haïti'),
    ('Brésil', '🇧🇷 Brésil'),
    ('Mexique', '🇲🇽 Mexique'),
    # ── Asie & Océanie ──────────────────────────────────────────────
    ('Chine', '🇨🇳 Chine'),
    ('Inde', '🇮🇳 Inde'),
    ('Japon', '🇯🇵 Japon'),
    ('Australie', '🇦🇺 Australie'),
    # ── Autre ───────────────────────────────────────────────────────
    ('Autre', '🌐 Autre'),
]


class FormulaireInscription(UserCreationForm):
    """Formulaire d'inscription personnalisé pour Numeria."""

    email = forms.EmailField(
        required=True,
        label="Adresse email",
        widget=forms.EmailInput(attrs={'placeholder': 'votre@email.com'})
    )
    first_name = forms.CharField(
        required=True,
        label="Prénom",
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'Votre prénom'})
    )
    last_name = forms.CharField(
        required=True,
        label="Nom de famille",
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'Votre nom'})
    )
    pays = forms.ChoiceField(
        required=False,
        label="Pays",
        choices=PAYS_CHOICES,
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2', 'pays']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Nom d'utilisateur"
        self.fields['username'].help_text = "Lettres, chiffres et @/./+/-/_ uniquement."
        self.fields['username'].widget.attrs['placeholder'] = "Nom d'utilisateur unique"
        self.fields['password1'].label = "Mot de passe"
        self.fields['password1'].help_text = ""
        self.fields['password1'].widget.attrs['placeholder'] = "8 caractères minimum"
        self.fields['password2'].label = "Confirmer le mot de passe"
        self.fields['password2'].help_text = ""
        self.fields['password2'].widget.attrs['placeholder'] = "Répète ton mot de passe"

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            Profil.objects.create(
                utilisateur=user,
                pays=self.cleaned_data.get('pays', '')
            )
        return user


class FormulaireConnexion(forms.Form):
    """Formulaire de connexion."""
    username = forms.CharField(
        label="Nom d'utilisateur",
        widget=forms.TextInput(attrs={'placeholder': "Nom d'utilisateur"})
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={'placeholder': "Ton mot de passe"})
    )


class FormulaireProfil(forms.ModelForm):
    """Formulaire de modification du profil."""

    first_name = forms.CharField(
        required=True,
        label="Prénom",
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'Votre prénom'})
    )
    last_name = forms.CharField(
        required=True,
        label="Nom",
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'Votre nom'})
    )
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={'placeholder': 'votre@email.com'})
    )
    pays = forms.ChoiceField(
        required=False,
        label="Pays",
        choices=PAYS_CHOICES,
    )

    class Meta:
        model = Profil
        fields = [
            'photo', 'bio', 'pays', 'ville',
            'niveau_etudes', 'domaine', 'linkedin', 'github',
        ]
        widgets = {
            'photo': forms.FileInput(attrs={
                'accept': 'image/*',
                'class': 'hidden',
                'id': 'input-photo'
            }),
            'bio': forms.Textarea(attrs={
                'placeholder': 'Parlez-nous de vous...',
                'rows': 4
            }),
            'ville': forms.TextInput(attrs={'placeholder': 'Ex: Lomé'}),
            'domaine': forms.TextInput(attrs={'placeholder': 'Ex: Mathématiques, Physique...'}),
            'linkedin': forms.URLInput(attrs={'placeholder': 'https://linkedin.com/in/...'}),
            'github': forms.URLInput(attrs={'placeholder': 'https://github.com/...'}),
        }
        labels = {
            'photo': 'Photo de profil',
            'bio': 'Biographie',
            'pays': 'Pays',
            'ville': 'Ville',
            'niveau_etudes': "Niveau d'études",
            'domaine': "Domaine d'études",
            'linkedin': 'LinkedIn',
            'github': 'GitHub',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email

    def save(self, commit=True):
        profil = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            self.user.email = self.cleaned_data['email']
            self.user.save()
        if commit:
            profil.save()
        return profil