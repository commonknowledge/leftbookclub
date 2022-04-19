from wagtail.core import blocks
from wagtail.core.blocks import RichTextBlock
from wagtail.core.fields import StreamField
from wagtail.embeds.blocks import EmbedBlock


def ArticleContentStream(block_types=None, **kwargs):
    common_block_types = [
        (
            "text",
            RichTextBlock(
                features=[
                    "h3",
                    "h4",
                    "bold",
                    "italic",
                    "link",
                    "ol",
                    "ul",
                ],
                template="app/content/text.html",
            ),
        ),
        ("embed", EmbedBlock(template="app/content/embed.html")),
    ]

    return StreamField(common_block_types + (block_types or []), **kwargs)
