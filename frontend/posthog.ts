import posthog from "posthog-js";

export default function initialisePosthog() {
  if (
    typeof window === undefined ||
    !window.POSTHOG_PUBLIC_TOKEN ||
    !window.POSTHOG_URL
  )
    return;

  posthog.init(window.POSTHOG_PUBLIC_TOKEN, {
    api_host: window.POSTHOG_URL,
    autocapture: true,
    loaded: (posthog) => {
      if (window.DEBUG) {
        // Permanently opt out all devs from analytics, if they ever run the system in debug mode
        posthog.opt_out_capturing();
      }

      // Capture visits mediated by Turbo
      // window.addEventListener("turbo:load", () => {
      //   posthog.capture("$pageview");
      // });

      // Identify user
      if (
        !window.userData ||
        !window.userData.is_authenticated ||
        !window.userData.set
      )
        return;

      posthog.identify(window.userData.set.django_id, window.userData?.set);

      posthog.register(window.userData?.register || {});

      if (!!window.userData.set.email && window.userData.set.email.length > 5) {
        posthog.alias(window.userData.set.email, window.userData.set.django_id);
      }

      if (
        !!window.userData.set.stripe_customer_id &&
        window.userData.set.stripe_customer_id.length > 8
      ) {
        posthog.alias(
          window.userData.set.stripe_customer_id,
          window.userData.set.django_id
        );
      }
    },
  });
}
