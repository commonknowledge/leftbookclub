from django.template import Context, Template
from django.test import RequestFactory, TestCase
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore
from wagtail.models import Page, Site
from wagtailmenus.models import MainMenu

from app.models import (
    BlogIndexPage,
    BlogPage,
    BookIndexPage,
    CustomMainMenuItem,
    InformationPage,
)


class MainMenuDropdownTestCase(TestCase):
    def setUp(self):
        site = Site.objects.get(is_default_site=True)
        home = site.root_page

        self.books = home.add_child(
            instance=BookIndexPage(
                title="Books",
                slug="books",
                repeat_in_subnav=True,
                repeated_item_text="All Books",
            )
        )
        self.collections = self.books.add_child(
            instance=InformationPage(title="Collections", slug="collections")
        )
        self.blog = home.add_child(instance=BlogIndexPage(title="Blog", slug="blog"))
        self.blog.add_child(instance=BlogPage(title="A blog post", slug="a-post", intro="Intro"))

        menu = MainMenu.get_for_site(site)
        CustomMainMenuItem.objects.create(
            menu=menu, link_page=self.books, allow_subnav=True, sort_order=0
        )
        CustomMainMenuItem.objects.create(
            menu=menu, link_page=self.blog, allow_subnav=False, sort_order=1
        )
        self.home = home

    def render_menu(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        request.session = SessionStore()
        template = Template(
            '{% load menu_tags %}{% main_menu max_levels=2 template="menus/header.html" %}'
        )
        return template.render(
            Context({"request": request, "user": request.user, "page": self.home})
        )

    def test_dropdown_for_item_with_subnav(self):
        html = self.render_menu()
        self.assertIn('data-bs-toggle="dropdown"', html)
        self.assertIn("All Books", html)
        self.assertIn(self.collections.url, html)

    def test_no_dropdown_for_item_without_subnav(self):
        html = self.render_menu()
        self.assertIn(self.blog.url, html)
        self.assertNotIn("A blog post", html)

    def test_allow_subnav_off_by_default(self):
        item = CustomMainMenuItem(menu=MainMenu.get_for_site(Site.objects.get(is_default_site=True)))
        self.assertFalse(item.allow_subnav)
