import sys
from urllib.parse import quote_plus, urlsplit, urlunsplit

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.management import call_command
from django.test import TestCase, modify_settings, override_settings
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType


@override_settings(
    DEBUG=True,
    LOGGING={
        "loggers": {
            "django.request": {
                "handlers": ["console"],
            }
        }
    },
)
@modify_settings(
    MIDDLEWARE={
        "remove": [
            # 'django.contrib.sessions.middleware.SessionMiddleware',
            "django.middleware.csrf.CsrfViewMiddleware"
        ],
        "append": "app.tests.DisableCSRFMiddleware",
    }
)
class SeleniumTestCase(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Setup pages
        url = urlsplit(cls.live_server_url)
        call_command("setup_pages", host=url.hostname, port=url.port)

        # Setup browser spoofing
        chrome_service = Service(
            ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
        )

        chrome_options = Options()
        options = [
            "--headless",
            "--disable-gpu",
            "--window-size=1920,1200",
            "--ignore-certificate-errors",
            "--disable-extensions",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]
        for option in options:
            chrome_options.add_argument(option)

        cls.driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def tearDown(self):
        if sys.exc_info()[0]:
            test_method_name = self._testMethodName
            self.driver.save_screenshot("selenium-error-%s.png" % test_method_name)
        super().tearDown()
