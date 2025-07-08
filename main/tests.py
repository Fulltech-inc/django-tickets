from django.test import TestCase
import socket

class SmokeTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Just log hostname once when tests are initialized
        print("Running tests on host:", socket.gethostname())

    def test_placeholder(self):
        # Example test that always passes
        self.assertTrue(True)