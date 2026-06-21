from django.urls import path
from . import views_sandbox

urlpatterns = [
    path('', views_sandbox.sandbox_page, name='sandbox_page'),
    path('scripts/', views_sandbox.sandbox_list_scripts, name='sandbox_list_scripts'),
    path('scripts/save/', views_sandbox.sandbox_save_script, name='sandbox_save_script'),
    path('scripts/<int:script_id>/', views_sandbox.sandbox_load_script, name='sandbox_load_script'),
    path('scripts/<int:script_id>/delete/', views_sandbox.sandbox_delete_script, name='sandbox_delete_script'),
]
