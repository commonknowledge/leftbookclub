from django.conf import settings

# def user_data(request):
#     user_data = {}

#     if request.user.is_authenticated:
#         user_data = {
#           "email": request.user.email,
#           "name": request.user.get_full_name(),
#           "stripe_customer_id": request.user.stripe_customer.id
#         }

#         if not settings.STRIPE_LIVE_MODE:
#             userId = f"{userId}—{request.get_host()}"

#     return {
#         "user_data": user_data
#     }
