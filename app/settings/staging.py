from .production import *

STAGING = True
STRIPE_LIVE_MODE = False
STRIPE_API_KEY = STRIPE_TEST_SECRET_KEY

try:
    from .local import *
except ImportError:
    pass
