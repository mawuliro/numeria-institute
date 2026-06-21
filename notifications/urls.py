from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('mark-read/', views.mark_read, name='mark_read'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('unread-count/', views.unread_count, name='unread_count'),
    path('admin-panel/send/', views.send_notification, name='send'),
]
