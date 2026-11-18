# ruff: noqa: E501
"""One layout for every host dashboard page, the same as the robot's settings: a left column of tabs (scrolls on its own), a right pane of content
(scrolls on its own), large rows, a clear active tab, and Done in the same place. On a phone the tabs become a selector at the top in the same order.

The tab order follows the robot where the same things exist (docs/design/screen-style.md). Each page keeps its own content; ``apply`` wraps it."""

from __future__ import annotations

# (id, label, path). Order: what is happening, what is on the robot, where the brain lives, then all other settings.
TABS: tuple[tuple[str, str, str], ...] = (
    ("health", "Status", "/health"),
    ("installed", "On my robot", "/on-my-robot"),
    ("brain", "Brain", "/brain"),
    ("settings", "Settings", "/settings"),
)

CSS = """
:root{--accent:#5AAAFF;--good:#46BE6E;--warn:#FABE32;--bad:#E64646;--surface:#202028;--muted:#8C96AA}
@media (prefers-color-scheme:light){:root{--accent:#0b6bcb;--good:#1e7a46;--warn:#9a6700;--bad:#b3261e;--surface:#f4f6f8;--muted:#566573}}
html,body{height:100%}body{margin:0;overflow:hidden}
.shell{display:grid;grid-template-columns:15rem 1fr;height:100vh}
.tabs{overflow-y:auto;background:var(--card,var(--surface));padding:.6rem;border-right:1px solid var(--line,#2c3640)}
.tabs h2{font-size:1rem;margin:.4rem .6rem}.tabs a{display:block;min-height:48px;line-height:48px;padding:0 .9rem;border-radius:10px;color:var(--fg);text-decoration:none;font-weight:600}
.tabs a[aria-current=page]{background:var(--accent);color:#fff}.tabs a:focus-visible{outline:3px solid var(--accent)}
.pane{overflow-y:auto;height:100vh;box-sizing:border-box}.pane>main{max-width:46rem;margin:0 auto;padding:1rem 16px 3rem}
.top{display:flex;justify-content:flex-end;padding:.5rem 16px 0}.top a{min-height:44px;line-height:44px;padding:0 1rem;font-weight:600;color:var(--accent);text-decoration:none}
.tabsel{display:none}.sr{position:absolute;left:-9999px}
details.advanced{margin:1rem 0}details.advanced>summary{min-height:48px;line-height:48px;font-weight:600;cursor:pointer}
@media (max-width:700px){.shell{grid-template-columns:1fr;grid-template-rows:auto 1fr}.tabs{display:none}.tabsel{display:block;padding:.5rem 16px}.tabsel select{font:inherit;width:100%;min-height:48px;padding:.4rem;border-radius:10px}.pane{height:auto}}
"""


def _tabs_html(active: str) -> str:
    links = "".join(f'<a href="{path}"{" aria-current=page" if tab == active else ""}>{label}</a>' for tab, label, path in TABS)
    options = "".join(f'<option value="{path}"{" selected" if tab == active else ""}>{label}</option>' for tab, label, path in TABS)
    return (
        f'<div class="shell"><nav class="tabs" aria-label="Sections"><h2>MaiPai</h2>{links}</nav>'
        f'<div class="pane"><div class="tabsel"><label class="sr" for="tabsel">Section</label><select id="tabsel" onchange="location.href=this.value">{options}</select></div>'
        '<div class="top"><a href="/settings">Done</a></div>'
    )


def apply(page: str, active: str) -> str:
    """Wrap a page that is `<style>...</style></head><body><main>...</main>...` in the shared layout."""
    page = page.replace("</style>", CSS + "</style>", 1)
    page = page.replace("<body><main>", "<body>" + _tabs_html(active) + "<main>", 1)
    page = page.replace("</main>", "</main></div></div>", 1)
    return page
