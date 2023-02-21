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
    mailchimp.set_config(
        {
            "api_key": settings.MAILCHIMP_API_KEY,
            "server": settings.MAILCHIMP_SERVER_PREFIX,
        }
    )


def email_to_hash(email):
    return hashlib.md5(email.encode("utf-8").lower()).hexdigest()


def apply_gdpr_consent(member):
    if not MAILCHIMP_IS_ACTIVE:
        return False
    marketing_permissions = []
    for marketing_permission in member.get("marketing_permissions", []):
        marketing_permissions.append(
            {
                "marketing_permission_id": marketing_permission[
                    "marketing_permission_id"
                ],
                "enabled": True,
            }
        )
    updated = mailchimp.lists.set_list_member(
        member["list_id"],
        member["id"],
        {"marketing_permissions": marketing_permissions},
    )
    return updated


def mailchimp_contact_for_user(user: User, list_id=settings.MAILCHIMP_LIST_ID):
    if not MAILCHIMP_IS_ACTIVE:
        return False
    try:
        member = mailchimp.lists.set_list_member(
            list_id,
            email_to_hash(user.primary_email),
            {
                "email_address": user.primary_email,
                "merge_fields": {"FNAME": user.first_name, "LNAME": user.last_name},
                "status_if_new": "subscribed"
                if user.gdpr_email_consent
                else "unsubscribed",
            },
        )
        member = apply_gdpr_consent(member)
        return member
    except MailchimpApiClientError:
        member = mailchimp.lists.add_list_member(
            list_id,
            {
                "email_address": user.primary_email,
                "merge_fields": {"FNAME": user.first_name, "LNAME": user.last_name},
                "status": "subscribed" if user.gdpr_email_consent else "unsubscribed",
            },
        )
        member = apply_gdpr_consent(member)
        return member


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
        print(f"A Mailchimp API exception occurred: {error.text}")


def format_event_name(event: str):
    # Event name must only contain letters, numbers, underscores, and dashes.
    # Event name must be 30 chars or less
    event = str(event).replace(" ", "_")
    event = "".join([c for c in event if c.isalnum() or c in ["_", "-"]])
    return event[:30]


def track_event_for_user_in_mailchimp(user: User, event: str, properties=dict()):
    if not MAILCHIMP_IS_ACTIVE:
        print("track_event_for_user_in_mailchimp", event, properties)
        return
    contact = mailchimp_contact_for_user(user)
    if contact is None:
        return
    try:
        response = mailchimp.lists.create_list_member_event(
            settings.MAILCHIMP_LIST_ID,
            email_to_hash(user.primary_email),
            {"name": format_event_name(event), "properties": properties},
        )
        print(f"mailchimp.lists.create_list_member_event() response: {response}")
    except MailchimpApiClientError as error:
        print(f"A Mailchimp API exception occurred: {error.text}")
