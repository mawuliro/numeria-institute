from django.urls import path
from . import views
from . import views_cours, views_blog, views_media

app_name = 'admin_panel'

urlpatterns = [
    # ── Dashboard ─────────────────────────────────────────────────────────────
    path('', views.dashboard, name='dashboard'),

    # ── Contacts ──────────────────────────────────────────────────────────────
    path('contacts/', views.contacts_list, name='contacts_list'),
    path('contacts/<int:message_id>/', views.contact_detail, name='contact_detail'),

    # ── Candidatures ──────────────────────────────────────────────────────────
    path('candidatures/', views.candidatures_list, name='candidatures_list'),
    path('candidatures/<int:candidature_id>/', views.candidature_detail, name='candidature_detail'),
    path('candidatures/<int:candidature_id>/action/', views.candidature_action, name='candidature_action'),

    # ── Mentorat ──────────────────────────────────────────────────────────────
    path('mentorat/', views.mentorat_list, name='mentorat_list'),
    path('mentorat/<int:demande_id>/', views.mentorat_detail, name='mentorat_detail'),
    path('mentorat/<int:demande_id>/action/', views.mentorat_action, name='mentorat_action'),

    # ── Utilisateurs ──────────────────────────────────────────────────────────
    path('utilisateurs/', views.users_list, name='users_list'),
    path('utilisateurs/<int:user_id>/', views.user_detail, name='user_detail'),
    path('utilisateurs/<int:user_id>/action/', views.user_action, name='user_action'),

    # ── Activité ──────────────────────────────────────────────────────────────
    path('activite/', views.activity_log, name='activity_log'),

    # ── Exercices de code ─────────────────────────────────────────────────────
    path('exercices/', views.exercises_list, name='exercises_list'),
    path('exercices/resultats/', views.exercise_results, name='exercise_results'),
    path('exercices/resultats/csv/', views.exercise_results_csv, name='exercise_results_csv'),
    path('exercices/lecon/<int:lecon_id>/ajouter/', views.exercise_create, name='exercise_create'),
    path('exercices/<int:exercise_id>/modifier/', views.exercise_edit, name='exercise_edit'),
    path('exercices/<int:exercise_id>/supprimer/', views.exercise_delete, name='exercise_delete'),
    path('exercices/<int:exercise_id>/reorder/', views.exercise_reorder, name='exercise_reorder'),

    # ── Cours (CMS) ───────────────────────────────────────────────────────────
    path('cours/', views_cours.cours_list, name='cours_list'),
    path('cours/nouveau/', views_cours.cours_create, name='cours_create'),
    path('cours/<slug:slug>/modifier/', views_cours.cours_edit, name='cours_edit'),
    path('cours/<slug:slug>/supprimer/', views_cours.cours_delete, name='cours_delete'),
    path('cours/<slug:slug>/preview/', views_cours.cours_preview, name='cours_preview'),
    path('cours/<slug:slug>/statistiques/', views_cours.cours_analytics, name='cours_analytics'),

    # AJAX — course meta
    path('cours/<slug:slug>/ajax/save/', views_cours.ajax_cours_save, name='ajax_cours_save'),
    # AJAX — modules
    path('cours/<slug:slug>/ajax/module/create/', views_cours.ajax_module_create, name='ajax_module_create'),
    path('cours/ajax/module/<int:module_id>/update/', views_cours.ajax_module_update, name='ajax_module_update'),
    path('cours/ajax/module/<int:module_id>/delete/', views_cours.ajax_module_delete, name='ajax_module_delete'),
    # AJAX — lessons
    path('cours/<slug:slug>/ajax/lecon/create/', views_cours.ajax_lecon_create, name='ajax_lecon_create'),
    path('cours/ajax/lecon/<int:lecon_id>/', views_cours.ajax_lecon_get, name='ajax_lecon_get'),
    path('cours/ajax/lecon/<int:lecon_id>/save/', views_cours.ajax_lecon_save, name='ajax_lecon_save'),
    path('cours/ajax/lecon/<int:lecon_id>/delete/', views_cours.ajax_lecon_delete, name='ajax_lecon_delete'),
    # AJAX — reorder
    path('cours/<slug:slug>/ajax/reorder/', views_cours.ajax_reorder, name='ajax_reorder'),
    # Image upload
    path('upload/image/', views_cours.image_upload, name='image_upload'),

    # ── Blog (CMS) ────────────────────────────────────────────────────────────
    path('blog/', views_blog.blog_list, name='blog_list'),
    path('blog/nouveau/', views_blog.blog_create, name='blog_create'),
    path('blog/<slug:slug>/modifier/', views_blog.blog_edit, name='blog_edit'),
    path('blog/<slug:slug>/sauvegarder/', views_blog.blog_save, name='blog_save'),
    path('blog/<slug:slug>/supprimer/', views_blog.blog_delete, name='blog_delete'),
    path('blog/<slug:slug>/preview/', views_blog.blog_preview, name='blog_preview'),

    # ── Médiathèque ───────────────────────────────────────────────────────────
    path('mediatheque/', views_media.media_list, name='media_list'),
    path('mediatheque/upload/', views_media.media_upload, name='media_upload'),
    path('mediatheque/<int:media_id>/supprimer/', views_media.media_delete, name='media_delete'),
]
