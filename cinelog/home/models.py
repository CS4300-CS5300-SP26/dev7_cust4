from django.db import models


class CarouselImage(models.Model):
    """
    Class for images that can be used in carousel different pages of web application.
    """
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to="carousel/")

    def __str__(self):
        """Returns the title of the movie."""
        return self.title
