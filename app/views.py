import djstripe
import stripe
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic.base import RedirectView, TemplateView
from djstripe import settings as djstripe_settings


class MemberSignupUserRegistrationMixin(LoginRequiredMixin):
    login_url = reverse_lazy("account_signup")


class CreateCheckoutSessionView(MemberSignupUserRegistrationMixin, RedirectView):
    context = {}

    def get_redirect_url(self, *args, **kwargs):
        """
        Creates and returns a Stripe Checkout Session
        """

        # get the id of the Model instance of djstripe_settings.djstripe_settings.get_subscriber_model()
        # here we have assumed it is the Django User model. It could be a Team, Company model too.
        # note that it needs to have an email field.
        user = self.request.user

        # example of how to insert the SUBSCRIBER_CUSTOMER_KEY: id in the metadata
        # to add customer.subscriber to the newly created/updated customer.
        metadata = {
            f"{djstripe_settings.djstripe_settings.SUBSCRIBER_CUSTOMER_KEY}": user.id
        }

        session_args = dict(
            **self.context,
            metadata=metadata,
        )

        try:
            additional_args = {}
            # retreive the Stripe Customer.
            customer, is_new = user.get_or_create_customer()
            if customer is not None:
                additional_args["customer"] = customer.id
            elif user.email is not None:
                additional_args["customer_email"] = user.email

            # ! Note that Stripe will always create a new Customer Object if customer id not provided
            # ! even if customer_email is provided!
            session = stripe.checkout.Session.create(**session_args, **additional_args)

        except djstripe.models.Customer.DoesNotExist:
            session = stripe.checkout.Session.create(**session_args)

        return session.url


class CheckoutSessionCompleteView(MemberSignupUserRegistrationMixin, TemplateView):
    template_name = "app/post_purchase_success.html"

    def get_context_data(self, *args, **kwargs):
        session = stripe.checkout.Session.retrieve(self.request.GET.get("session_id"))
        stripe_customer = stripe.Customer.retrieve(session.customer)
        customer, is_new = djstripe.models.Customer._get_or_create_from_stripe_object(
            stripe_customer
        )
        customer.subscriber = self.request.user
        customer.save()

        # Get Parent Context
        context = {**super().get_context_data(**kwargs), "customer": customer}

        return context
