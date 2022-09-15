from typing import Any, Dict, Iterable, List, Optional, TypedDict, TypeVar

import json
from dataclasses import asdict, dataclass
from datetime import datetime

import humanize
from django.conf import settings
from groundwork.core.datasources import RestDatasource

ResourceT = TypeVar("ResourceT")


class CircleAPIResource(RestDatasource[ResourceT]):
    base_url = "https://app.circle.so/api/v1"
    api_key: str
    community_id: Optional[str] = None

    def __init__(self, resource_type: ResourceT, community_id=None, **kwargs):
        super().__init__(resource_type=resource_type, **kwargs)

        if not hasattr(self, "api_key"):
            self.api_key = getattr(settings, "CIRCLE_API_TOKEN", None)

        if self.community_id is None:
            communities = self.fetch_url(f"{self.base_url}/communities", query={})
            self.community_id = communities[0]["id"]

    def get_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Token {self.api_key}"}

    def paginate(self, **query: Dict[str, Any]) -> Iterable[ResourceT]:
        page = query.get("page", 1)

        # Set defaults
        if not "per_page" in query:
            query["per_page"] = 20

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
        kwargs["query"]["community_id"] = self.community_id
        return super().fetch_url(*args, **kwargs)


# {
#   "formatted_address": "5 Caledonian Rd, London N1 9DY, UK",
#   "geometry": {
#     "location": {
#       "lat": 51.5312223,
#       "lng": -0.1211209
#     }
#   },
#   "name": "Housmans Bookshop",
#   "place_id": "ChIJD6SY9z8bdkgRuHax27_5fwg",
#   "url": "https://maps.google.com/?cid=612482676765587128",
#   "website": "http://www.housmans.com/",
#   "html_attributions": []
# }


@dataclass
class CircleAddress:
    formatted_address: str
    name: Optional[str]
    place_id: Optional[str]
    url: Optional[str]
    website: Optional[str]
    html_attributions: Optional[List[str]]
    geometry: Optional[
        TypedDict(
            "location",
            {"location": TypedDict("coordinates", {"lat": float, "lng": float})},
        )
    ]


@dataclass
class CircleEventBody:
    id: int
    name: str
    body: Optional[str]


@dataclass
class CircleEvent:
    id: int
    name: str
    slug: str
    starts_at: datetime
    url: str
    location_type: str
    in_person_location: Optional[str]
    virtual_location_url: Optional[str]
    body: Optional[CircleEventBody]
    human_readable_date: Optional[str] = None

    def __post_init__(self, *args, **kwargs):
        self.human_readable_date = humanize.naturalday(self.starts_at)

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


# circle_communities = CircleAPIResource(
#     path="/communities",
#     resource_type=CircleCommunity,
#     api_key=settings.CIRCLE_API_KEY
# )


# class CircleEvent(SyncedModel):
#     # This is where we specify the datasource, along with other options
#     # for customizing how synchronization happens.
#     sync_config = SyncConfig(
#       datasource=circle_events,
#     )

#     # This is used to join data returned from the remote API against
#     # our local data.
#     external_id = models.IntegerField()

#     # This will be populated from the remote data.
#     name = models.CharField(max_length=300)
#     starts_at = models.DateField()
#     location_type = models.CharField(max_length=300)
#     name = models.CharField(max_length=300)
#     body = RichTextField()
#     url = models.URLField()
