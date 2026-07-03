from django.contrib import admin

from .models import Achievement, CVPreset, Entry


class AchievementInline(admin.TabularInline):
    model = Achievement
    extra = 1


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "organization", "start_date", "end_date")
    list_filter = ("category", "start_date")
    search_fields = ("name", "organization", "description")
    inlines = [AchievementInline]


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("title", "entry", "date")
    list_filter = ("date", "entry__category")
    search_fields = ("title", "detail")


@admin.register(CVPreset)
class CVPresetAdmin(admin.ModelAdmin):
    list_display = ("name", "achievement_layout", "created_at")
    filter_horizontal = ("entries", "achievements")
