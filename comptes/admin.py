from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Profil


class ProfilInline(admin.StackedInline):
    """
    Affiche le profil directement dans la page User de l'admin.
    StackedInline : affichage vertical (plus lisible)
    """
    model = Profil
    can_delete = False
    verbose_name_plural = 'Profil étudiant'


# On étend l'admin User existant pour y inclure le Profil
class UserAvecProfil(UserAdmin):
    inlines = (ProfilInline,)
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'is_active',
        'date_joined',
    ]


# On remplace l'admin User par défaut par notre version étendue
admin.site.unregister(User)
admin.site.register(User, UserAvecProfil)
admin.site.register(Profil)