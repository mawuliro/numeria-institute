from django.test import TestCase

from .models import Formation


class FormationSlugTest(TestCase):
    def test_slug_auto_generated(self):
        f = Formation.objects.create(title='Test Formation', created_by=None)
        self.assertTrue(f.slug)
