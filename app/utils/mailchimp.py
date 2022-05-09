import hashlib

import mailchimp_marketing as MailchimpMarketing
from django.conf import settings
from mailchimp_marketing.api_client import ApiClientError as MailchimpApiClientError

from app.models import User

mailchimp = MailchimpMarketing.Client()
MAILCHIMP_IS_ACTIVE = (
    settings.MAILCHIMP_API_KEY is not None
    and settings.MAILCHIMP_SERVER_PREFIX is not None
    and settings.MAILCHIMP_LIST_ID is not None
)
if MAILCHIMP_IS_ACTIVE:
    mailchimp.set_config(settings.MAILCHIMP_API_KEY, settings.MAILCHIMP_SERVER_PREFIX)


def email_to_hash(email):
    return hashlib.md5(email.encode("utf-8").lower()).hexdigest()


def mailchimp_contact_for_user(user: User):
    if not MAILCHIMP_IS_ACTIVE:
        return False
    return mailchimp.lists.set_list_member(
        settings.MAILCHIMP_LIST_ID,
        email_to_hash(user.primary_email),
        {
            "email_address": user.primary_email,
            "merge_fields": {"FNAME": user.first_name, "LNAME": user.last_name},
            "status_if_new": "subscribed"
            if user.gdpr_email_consent
            else "unsubscribed",
        },
    )


def tag_user_in_mailchimp(user: User, tags_to_enable=list(), tags_to_disable=list()):
    tags = [{"name": tag, "status": "active"} for tag in tags_to_enable] + [
        {"name": tag, "status": "inactive"} for tag in tags_to_disable
    ]
    if not MAILCHIMP_IS_ACTIVE:
        print("tag_user_in_mailchimp", tags)
        return
    contact = mailchimp_contact_for_user(user)
    if contact is None:
        return
    try:
        response = mailchimp.lists.update_list_member_tags(
            settings.MAILCHIMP_LIST_ID,
            email_to_hash(user.primary_email),
            {"tags": tags},
        )
        print(f"client.lists.update_list_member_tags() response: {response}")
    except MailchimpApiClientError as error:
        print(f"An exception occurred: {error.text}")
