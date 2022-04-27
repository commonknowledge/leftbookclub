from django.conf import settings as django_settings


def settings(request):
    return {
        "settings": {
            "posthog_token": django_settings.POSTHOG_PUBLIC_TOKEN,
            "posthog_url": django_settings.POSTHOG_URL,
        }
    }
