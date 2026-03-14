from django.test import TestCase
from django.urls import reverse
from home.models import CarouselImage

class CustomLogInViewTest(TestCase):
    """
    Tests that the carousel images are passed to the login page.
    """
    def setUp(self):       
        """
        Set up a valid carousel image that can be used by the tests.
        """
        self.carousel_img = CarouselImage.objects.create(
            title='test123', 
            image='carousel/img.jpg'
        )
    

    def test_login_html(self):
        """
        Test that the login_html function returns the movies for a carousel.
        """
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')
        self.assertIn("carousel_imgs", response.context)