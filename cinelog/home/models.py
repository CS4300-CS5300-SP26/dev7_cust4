"""Models for the Cinelog home app."""

from django.db import models
from django.utils import timezone


class Movie(models.Model):
    user = models.UUIDField()
    title = models.CharField(max_length=255)
    poster_url = models.URLField(max_length=500, null=True, blank=True)
    tmdb_id = models.IntegerField()
    rating = models.IntegerField(default=0)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    watched_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.rating}★)"
