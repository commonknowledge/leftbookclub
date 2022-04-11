from wagtail.core import blocks
from wagtail.core.blocks import RichTextBlock
from wagtail.core.fields import StreamField
from wagtail.embeds.blocks import EmbedBlock
from wagtail.images.blocks import ImageChooserBlock


class ImageBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=False)
    caption = blocks.CharBlock()

    class Meta:
        template = "app/content/image.html"
        icon = "image"


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
        ("embed", EmbedBlock(max_width=800, max_height=400)),
        ("image", ImageBlock()),
    ]

    return StreamField(common_block_types + (block_types or []), **kwargs)
