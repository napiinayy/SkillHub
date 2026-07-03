from django.db import models


class Entry(models.Model):
    WORK = "work"
    CAMPUS = "campus"
    CERTIFICATE = "certificate"
    CATEGORY_CHOICES = [
        (WORK, "Work Experience"),
        (CAMPUS, "Campus Organization"),
        (CERTIFICATE, "Certificate"),
    ]

    name = models.CharField(max_length=200)
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default=WORK
    )
    organization = models.CharField(max_length=200, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(
        null=True, blank=True, help_text="Leave blank if ongoing"
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["category", "-start_date", "name"]
        verbose_name_plural = "Entries"

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    def date_range(self):
        fmt = "%b %Y"
        start = self.start_date.strftime(fmt) if self.start_date else ""
        if self.end_date:
            end = self.end_date.strftime(fmt)
        else:
            end = "Present" if self.start_date else ""
        if start and end:
            return f"{start} \u2013 {end}"
        return start or end


class Achievement(models.Model):
    entry = models.ForeignKey(
        Entry, related_name="achievements", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255)
    detail = models.TextField(blank=True)
    date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-date", "title"]

    def __str__(self):
        return self.title

    def display(self):
        if self.detail:
            return f"{self.title} \u2014 {self.detail}"
        return self.title


class CVPreset(models.Model):
    NESTED = "nested"
    SECTION = "section"
    LAYOUT_CHOICES = [
        (NESTED, "Nested under each experience"),
        (SECTION, "Grouped in a dedicated Achievements section"),
    ]

    name = models.CharField(max_length=120, unique=True)
    entries = models.ManyToManyField(Entry, blank=True, related_name="presets")
    achievements = models.ManyToManyField(
        Achievement, blank=True, related_name="presets"
    )
    achievement_layout = models.CharField(
        max_length=10, choices=LAYOUT_CHOICES, default=NESTED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
