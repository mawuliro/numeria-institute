from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from .models import Mentor, Mentee, DemandeMentorat, SeanceMentorat, PaiementSeance, MentorApplication


def validate_file_size(value):
    max_size = 5 * 1024 * 1024  # 5 MB
    if value.size > max_size:
        raise ValidationError("Le fichier dépasse la taille maximale de 5MB.")


class MentorApplicationForm(forms.ModelForm):
    certificate = forms.FileField(
        label='Certificat',
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png']), validate_file_size],
        help_text='PDF, JPG, PNG, ou JPEG. Taille max 5MB.',
    )
    cv = forms.FileField(
        label='CV',
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx']), validate_file_size],
        help_text='PDF, DOC, DOCX. Taille max 5MB.',
    )

    class Meta:
        model = MentorApplication
        fields = [
            'full_name',
            'professional_title',
            'bio',
            'expertise_categories',
            'linkedin',
            'portfolio',
            'github',
            'social_profiles',
            'certificate',
            'cv',
            'recommendation_letter',
            'additional_documents',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'Décrivez votre parcours, vos compétences et pourquoi vous souhaitez mentorer.'
            }),
            'expertise_categories': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Ex: Data Science, Python, Carrière tech'
            }),
            'social_profiles': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Ex: Twitter.com/moncompte, Instagram.com/moncompte'
            }),
        }
        help_texts = {
            'expertise_categories': 'Séparez les sujets par des virgules.',
            'social_profiles': 'Optionnel, séparez les liens par des virgules.',
        }

    def clean(self):
        cleaned_data = super().clean()
        certificate = cleaned_data.get('certificate')
        cv = cleaned_data.get('cv')
        if not certificate:
            self.add_error('certificate', 'Un certificat est requis.')
        if not cv:
            self.add_error('cv', 'Un CV est requis.')
        return cleaned_data


class MentorProfileForm(forms.ModelForm):
    linkedin = forms.URLField(required=False, label='LinkedIn')
    github = forms.URLField(required=False, label='GitHub')
    photo = forms.ImageField(required=False, label='Photo de profil')

    class Meta:
        model = Mentor
        fields = [
            'titre_professionnel',
            'domaines_expertise',
            'categories',
            'niveau_experience',
            'disponibilite',
            'tarif_par_seance',
            'langues',
            'bio_mentorat',
        ]
        widgets = {
            'bio_mentorat': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Parlez de votre expertise, de vos succès et de la façon dont vous accompagnez vos mentorés.'
            }),
            'categories': forms.TextInput(attrs={
                'placeholder': 'Ex: leadership, product management, entretien technique'
            }),
            'langues': forms.TextInput(attrs={
                'placeholder': 'Ex: Français, Anglais'
            }),
        }
        help_texts = {
            'tarif_par_seance': 'Entrez un tarif par séance en FCFA.',
            'categories': 'Mots-clés ou catégories de mentorat séparés par des virgules.',
        }

    def __init__(self, *args, **kwargs):
        profil = kwargs.pop('profil', None)
        super().__init__(*args, **kwargs)
        if profil is not None:
            self.fields['linkedin'].initial = profil.linkedin
            self.fields['github'].initial = profil.github
            self.fields['photo'].initial = profil.photo

    def save(self, commit=True):
        mentor = super().save(commit=False)
        if commit:
            mentor.save()
            profil = mentor.profil
            if self.cleaned_data.get('linkedin') is not None:
                profil.linkedin = self.cleaned_data['linkedin']
            if self.cleaned_data.get('github') is not None:
                profil.github = self.cleaned_data['github']
            if self.cleaned_data.get('photo') is not None:
                profil.photo = self.cleaned_data['photo']
            profil.save()
        return mentor


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