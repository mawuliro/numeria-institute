from django.contrib import admin
from .models import HomePage, AboutPage, ContactPage


@admin.register(HomePage)
class HomePageAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Section Héros', {
            'fields': ('hero_badge', 'hero_title', 'hero_description', 'hero_cta_primary_text', 'hero_cta_primary_url', 'hero_cta_secondary_text', 'hero_cta_secondary_url')
        }),
        ('Statistiques', {
            'fields': ('stats_students', 'stats_courses', 'stats_countries')
        }),
        ('Fonctionnalités', {
            'fields': ('features_title', 'features')
        }),
        ('Témoignages', {
            'fields': ('testimonials',)
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description')
        }),
    )


@admin.register(AboutPage)
class AboutPageAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Contenu principal', {
            'fields': ('title', 'content')
        }),
        ('Mission & Vision', {
            'fields': ('mission_title', 'mission_content', 'vision_title', 'vision_content')
        }),
        ('Équipe', {
            'fields': ('team',)
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description')
        }),
    )


@admin.register(ContactPage)
class ContactPageAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Contenu', {
            'fields': ('title', 'intro')
        }),
        ('Informations de contact', {
            'fields': ('address', 'phone', 'email', 'hours')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description')
        }),
    )
