from django.contrib import admin
from .models import MeetingRoom, MeetingParticipant, ChatMessage


@admin.register(MeetingRoom)
class MeetingRoomAdmin(admin.ModelAdmin):
    list_display = ('title', 'room_code', 'host', 'created_at', 'is_active', 'max_participants')
    list_filter = ('is_active',)
    search_fields = ('title', 'room_code', 'host__username')


@admin.register(MeetingParticipant)
class MeetingParticipantAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'room', 'user', 'is_host', 'joined_at', 'left_at')
    list_filter = ('is_host', 'room')
    search_fields = ('display_name', 'user__username', 'room__room_code')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'sender', 'timestamp', 'short_content')
    ordering = ('-timestamp',)

    def short_content(self, obj):
        return obj.content[:80]
    short_content.short_description = 'Message'
