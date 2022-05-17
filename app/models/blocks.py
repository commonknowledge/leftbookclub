from wagtail import blocks
from wagtail.blocks import RichTextBlock
from wagtail.embeds.blocks import EmbedBlock
from wagtail.fields import StreamField


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

    return StreamField(
        common_block_types + (block_types or []), use_json_field=True, **kwargs
    )
