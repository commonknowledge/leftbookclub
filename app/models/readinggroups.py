from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField    
from django.shortcuts import render
from wagtail.models import Page

class ReadingGroupSubmission(Page):
    thank_you_text = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("thank_you_text"),
    ]

    def serve(self, request):
        from app.forms import PublicReadingGroupForm

        if request.method == "POST":
            form = PublicReadingGroupForm(request.POST)
            if form.is_valid():
                event = form.save(commit=False)
                event.is_approved = False
                event.save()
                return render(request, "readinggroups/thank_you.html", {"page": self})
        else:
            form = PublicReadingGroupForm()

        return render(request, "readinggroups/reading_group_form.html", {"form": form, "page": self})