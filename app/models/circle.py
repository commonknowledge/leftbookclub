from typing import Any, Dict, Iterable, List, Optional, TypedDict, TypeVar

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

import humanize
from django import forms  # the default Django widgets live here
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from groundwork.core.datasources import RestDatasource, SyncConfig, SyncedModel
from wagtail.admin import widgets  # to use Wagtail's special datetime widget
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField

ResourceT = TypeVar("ResourceT")

import json
from datetime import datetime


class DTEncoder(json.JSONEncoder):
    def default(self, obj):
        # 👇️ if passed in object is datetime object
        # convert it to a string
        if isinstance(obj, datetime):
            return str(obj)
        # 👇️ otherwise use the default behavior
        return json.JSONEncoder.default(self, obj)


class CircleAPIResource(RestDatasource[ResourceT]):
    base_url = "https://app.circle.so/api/v1"
    api_key: str
    community_id: Optional[str] = None

    def __init__(self, resource_type: ResourceT, community_id=None, **kwargs):
        super().__init__(resource_type=resource_type, **kwargs)

        if not hasattr(self, "api_key"):
            self.api_key = getattr(settings, "CIRCLE_API_TOKEN", None)

    def get_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Token {self.api_key}"}

    def paginate(self, **query: Dict[str, Any]) -> Iterable[ResourceT]:
        page = query.get("page", 1)

        # Set defaults
        if not "per_page" in query:
            query["per_page"] = int(settings.CIRCLE_PER_PAGE)

        # Pull all of them
        while True:
            query["page"] = page

            data = self.fetch_url(self.url, query=query)
            yield from data

            if len(data) < query["per_page"]:
                # Ran out of results
                return
            else:
                page += 1

    def fetch_url(self, *args, **kwargs):
        kwargs["query"] = kwargs.get("query", {})

        if self.community_id is None:
            communities = super().fetch_url(f"{self.base_url}/communities", query={})
            self.community_id = communities[0]["id"]
        kwargs["query"]["community_id"] = self.community_id

        return super().fetch_url(*args, **kwargs)


@dataclass
class CircleAddress:
    """
    # Example:
    {
      "formatted_address": "5 Caledonian Rd, London N1 9DY, UK",
      "geometry": {
        "location": {
          "lat": 51.5312223,
          "lng": -0.1211209
        }
      },
      "name": "Housmans Bookshop",
      "place_id": "ChIJD6SY9z8bdkgRuHax27_5fwg",
      "url": "https://maps.google.com/?cid=612482676765587128",
      "website": "http://www.housmans.com/",
      "html_attributions": []
    }
    """

    formatted_address: str
    name: Optional[str] = None
    place_id: Optional[str] = None
    url: Optional[str] = None
    website: Optional[str] = None
    html_attributions: Optional[List[str]] = None
    geometry: Optional[
        TypedDict(
            "location",
            {"location": TypedDict("coordinates", {"lat": float, "lng": float})},
        )
    ] = None


@dataclass
class CircleEventBody:
    id: int
    name: str
    body: Optional[str] = None


@dataclass
class CircleEvent:
    id: int
    name: str
    slug: str
    starts_at: datetime
    url: str
    location_type: str
    in_person_location: Optional[str] = None
    virtual_location_url: Optional[str] = None
    body: Optional[CircleEventBody] = None
    human_readable_date: Optional[str] = None

    def __post_init__(self, *args, **kwargs):
        self.human_readable_date = humanize.naturalday(self.starts_at)

    @property
    def body_html(self):
        try:
            html = self.body.body
            return html
        except:
            return None

    @property
    def coordinates(self):
        try:
            point = Point(
                self.physical_address.geometry["location"]["lng"],
                self.physical_address.geometry["location"]["lat"],
            )
            return point
        except:
            return None

    @property
    def physical_address(self):
        if self.in_person_location is not None and isinstance(
            self.in_person_location, str
        ):
            return CircleAddress(**json.loads(self.in_person_location))

    @property
    def as_geojson_feature(self):
        try:
            geojson = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        self.physical_address.geometry["location"]["lng"],
                        self.physical_address.geometry["location"]["lat"],
                    ],
                },
                "properties": {
                    **asdict(self),
                    "physical_address": asdict(self.physical_address),
                },
            }
            return geojson
        except:
            geojson = {
                "type": "Feature",
                "properties": {**asdict(self)},
            }
            return geojson


@dataclass
class CircleCommunity:
    id: int


class DataclassJSONEncoder(DjangoJSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time, decimal types, and
    UUIDs.
    """

    def default(self, o):
        if isinstance(
            o,
            (
                CircleEventBody,
                CircleAddress,
                CircleEventBody,
                CircleEvent,
                CircleCommunity,
            ),
        ):
            # it's a dataclass
            return asdict(o)
        else:
            return super().default(o)


circle_events = CircleAPIResource(
    path="/events",
    resource_type=CircleEvent,
    api_key=settings.CIRCLE_API_KEY,
    community_id=int(settings.CIRCLE_COMMUNITY_ID)
)


circle_communities = CircleAPIResource(
    path="/communities",
    resource_type=CircleCommunity,
    api_key=settings.CIRCLE_API_KEY,
    community_id=int(settings.CIRCLE_COMMUNITY_ID)
)


class CircleEvent(SyncedModel):
    # This is where we specify the datasource, along with other options
    # for customizing how synchronization happens.
    sync_config = SyncConfig(
        datasource=circle_events,
        sync_interval=timedelta(minutes=settings.SYNC_INTERVAL_MINUTES_CIRCLE_EVENTS),
    )

    # This is used to join data returned from the remote API against
    # our local data.
    external_id = models.CharField(max_length=100)

    # This will be populated from the remote data.
    name = models.CharField(max_length=500)
    starts_at = models.DateTimeField()
    location_type = models.CharField(max_length=300)
    in_person_location = models.JSONField(
        blank=True, null=True, encoder=DjangoJSONEncoder
    )
    virtual_location_url = models.URLField(max_length=1024, blank=False, null=False)
    as_geojson_feature = models.JSONField(
        blank=True, null=True, encoder=DjangoJSONEncoder
    )
    body = models.JSONField(blank=True, null=True, encoder=DataclassJSONEncoder)
    url = models.URLField(max_length=1024, blank=False, null=False)
    coordinates = gis_models.PointField(null=True, blank=True)
    body_html = RichTextField(blank=True, null=True)

    title_widget = forms.TextInput(attrs={"placeholder": "Enter Full Title"})
    # using the correct widget for your field type and desired effect
    date_widget = widgets.AdminDateInput(attrs={"placeholder": "dd-mm-yyyy"})

    panels = [
        FieldPanel("name", widget=title_widget),  # then add them as a variable
        FieldPanel("starts_at", widget=date_widget),
    ]
