from django.test import TestCase
from home.models import CarouselImage
from django.core.exceptions import ValidationError

class CarouselImageModelTest(TestCase):
    """
    Tests the CarouselImage model that allows for posters to be uploaded
    and used in a Carousel in the web application.
    """
    def setUp(self):
        """
        Set up a valid carousel image that can be used by the tests.
        """
        CarouselImage.objects.create(title='test123', image='carousel/img.jpg')
    
    def test_carousel_img_creation(self):
        """
        Test that the carousel_img was properly created.
        """
        carousel_img = CarouselImage.objects.get(id=1)

        self.assertEqual(carousel_img.title, 'test123')
        self.assertIsNotNone(carousel_img.image)
        self.assertTrue(carousel_img.image.name.startswith('carousel/'))
        self.assertTrue(carousel_img.image.name.endswith('.jpg'))


    def test_str_method(self):
        """
        Test the str method is correctly formatted.
        """
        carousel_img = CarouselImage.objects.get(id=1)
        self.assertEqual(str(carousel_img.title), 'test123')

    def test_title_length(self):
        """
        Test that the length of the title must be less than 255 characters.
        """
        title = 'Test Title' * 200
        carousel_img = CarouselImage.objects.create(
            title=title,
            image='carousel/img.jpg'
        )
        with self.assertRaises(ValidationError):
            carousel_img.full_clean()

    def test_title_length_exact(self):
        """
        Test that the title can be exactly 255 characters.
        """
        title = 'A' * 255
        carousel_img = CarouselImage.objects.create(
            title=title,
            image='carousel/img.jpg'
        )

        self.assertEqual(carousel_img.title, title)
        self.assertIsNotNone(carousel_img.image)
        self.assertTrue(carousel_img.image.name.startswith('carousel/'))
        self.assertTrue(carousel_img.image.name.endswith('.jpg'))
