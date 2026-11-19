# ruff: noqa: E501
"""One layout for every host dashboard page, the same as the settings page (``shell_style``): a narrow sidebar of five items, a wide search field on top, one
column of content. A phone gets the five items as a bar at the foot. Each page keeps its own content; ``apply`` wraps it."""

from __future__ import annotations

from maipai_body import shell_style

# The tabs are the five sidebar items of the settings page (shell_style.NAV); a wrapped page names the item it belongs to.
TABS = tuple((ident, label, path) for ident, label, path, _icon in shell_style.NAV)
ACTIVE = {"health": "more", "installed": "more", "brain": "brain", "settings": "home", "about": "more", "legal": "more"}
CSS = shell_style.CSS + shell_style.WRAPPED_CSS


def apply(page: str, active: str) -> str:
    """Wrap a page that is `<style>...</style></head><body><main>...</main>...` in the shared layout: sidebar, a wide search field, the five items."""
    item = ACTIVE.get(active, active)
    page = page.replace("</style>", CSS + "</style>", 1)
    page = page.replace("<head>", "<head><link rel='icon' href='/assets/brand/maipai-bot-icon-light.png'>", 1)
    head = (
        '<body class="a2"><div class="app">' + shell_style.sidebar_html(item) + '<div class="pane"><div class="col"><div class="bar">' + shell_style.search_html() + "</div>"
    )
    page = page.replace("<body><main>", head + "<main>", 1)
    from maipai_body.legal import FOOTER_CSS, footer_html

    page = page.replace("</style>", FOOTER_CSS + "</style>", 1)
    page = page.replace("</main>", footer_html() + f'<p class="foot2">{shell_style.SPONSOR_LINE}</p></main></div></div></div>' + shell_style.bottom_html(item), 1)
    return page
