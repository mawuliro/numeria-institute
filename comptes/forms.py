from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profil


class FormulaireInscription(UserCreationForm):
    """Formulaire d'inscription personnalisé."""

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
    pays = forms.CharField(
        required=False,
        label="Pays",
        max_length=100,
        initial='Togo',
        widget=forms.TextInput(attrs={'placeholder': "Ex: Togo, Sénégal..."})
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
                pays=self.cleaned_data.get('pays', 'Togo')
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
    """Formulaire de modification du profil avec photo."""

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

    class Meta:
        model = Profil
        fields = [
            'photo',        # On ajoute la photo ici
            'bio',
            'pays',
            'ville',
            'niveau_etudes',
            'domaine',
            'linkedin',
            'github',
        ]
        widgets = {
            'photo': forms.FileInput(attrs={
                'accept': 'image/*',    # Accepte seulement les images
                'class': 'hidden',      # On cachera l'input par défaut
                'id': 'input-photo'
            }),
            'bio': forms.Textarea(attrs={
                'placeholder': 'Parlez-nous de vous...',
                'rows': 4
            }),
            'pays': forms.TextInput(attrs={'placeholder': 'Ex: Togo'}),
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