# ruff: noqa: E501
"""The one look of the dashboard (owner request 2026-11-19: calm, simple, like System Settings): five sidebar items, a wide search field,
one column of rounded groups. The settings page (``settings_ui_shell``) and the pages wrapped by ``dashboard_shell`` both use these tokens,
the sidebar and the search field, so there is one definition of each. Words follow docs/plan/settings-simplification.md."""

from __future__ import annotations

# (id, label, path, icon path). The path of a settings page item opens the settings page on that item.
NAV: tuple[tuple[str, str, str, str], ...] = (
    ("home", "Home", "/settings#home", "M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10"),
    ("robot", "Robot", "/settings#robot", "M12 3v3M7 6h10a3 3 0 013 3v7a3 3 0 01-3 3H7a3 3 0 01-3-3V9a3 3 0 013-3zM9 12v1M15 12v1M9.5 16h5"),
    ("brain", "Brain", "/brain", "M9 4a3 3 0 00-3 3 3 3 0 00-2 5 3 3 0 002 5 3 3 0 003 3h1V4zM15 4a3 3 0 013 3 3 3 0 012 5 3 3 0 01-2 5 3 3 0 01-3 3h-1V4z"),
    ("safety", "Safety", "/settings#safety", "M12 3l8 3v6c0 4.5-3.2 7.8-8 9-4.8-1.2-8-4.5-8-9V6z"),
    ("more", "More", "/settings#more", "M5 12h.01M12 12h.01M19 12h.01"),
)
BRAND_ICON = "/assets/brand/maipai-bot-icon-{theme}.png"  # light and dark copies of the org's robot mark, never redrawn
SEARCH_PLACEHOLDER = "Search settings"
SPONSOR_LINE = 'Support this project: <a href="https://github.com/sponsors/JesseWebDotCom">GitHub Sponsors</a>.'

CSS = """
:root{color-scheme:light dark;--bg:#f2f2f7;--grp:#fff;--grp2:#f2f2f7;--sep:#e5e5ea;--fg:#1c1c1e;--mut:#6c6c70;--ac:#0a7cff;--on-ac:#fff;--ok:#1f9d55;--warn:#b26a00;--bad:#d1342b;--side:#f9f9fb;--hover:rgba(60,60,67,.07);--font:system-ui,-apple-system,"SF Pro Text","Segoe UI",Roboto,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#000;--grp:#1c1c1e;--grp2:#2c2c2e;--sep:#38383a;--fg:#f2f2f7;--mut:#98989f;--ac:#4da3ff;--on-ac:#001a33;--ok:#32d583;--warn:#f0b64a;--bad:#ff6b61;--side:#111113;--hover:rgba(235,235,245,.08)}}
:root[data-theme=dark]{color-scheme:dark;--bg:#000;--grp:#1c1c1e;--grp2:#2c2c2e;--sep:#38383a;--fg:#f2f2f7;--mut:#98989f;--ac:#4da3ff;--on-ac:#001a33;--ok:#32d583;--warn:#f0b64a;--bad:#ff6b61;--side:#111113;--hover:rgba(235,235,245,.08)}
:root[data-theme=light]{color-scheme:light}
.side{position:sticky;top:0;height:100vh;width:232px;flex:none;background:var(--side);border-right:1px solid var(--sep);padding:20px 12px;display:flex;flex-direction:column;gap:20px;box-sizing:border-box;font-family:var(--font)}
.side .brand{display:flex;align-items:center;gap:10px;padding:0 8px;font-weight:700;font-size:15px;letter-spacing:-.01em;color:var(--fg);text-decoration:none}
.side .brand img{width:30px;height:30px;display:block}
.side .nv{display:flex;flex-direction:column;gap:2px}
.side .nv a,.side .nv button{display:flex;align-items:center;gap:12px;min-height:40px;padding:0 10px;border:0;border-radius:10px;background:none;color:var(--fg);font:500 15px/1 var(--font);text-align:left;text-decoration:none;cursor:pointer;transition:background .15s}
.side .nv a:hover,.side .nv button:hover{background:var(--hover)}
.side .nv [aria-current=page]{background:var(--ac);color:var(--on-ac)}
.side .nv svg{width:20px;height:20px;flex:none;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.side .foot{margin-top:auto;padding:0 8px;font-size:12px;color:var(--mut);line-height:1.4}.side .foot a{color:var(--mut)}
.bar{position:sticky;top:0;z-index:30;display:flex;align-items:center;gap:12px;padding:14px 0 10px;background:color-mix(in srgb,var(--bg) 86%,transparent);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);font-family:var(--font)}
.find{position:relative;flex:1 1 auto;min-width:0}
.a2 .find input,.find input{width:100%;box-sizing:border-box;min-height:44px;border-radius:12px;border:0;background:var(--grp);color:var(--fg);font:400 17px/1.2 var(--font);padding:0 16px 0 44px;box-shadow:0 0 0 1px var(--sep) inset;transition:box-shadow .15s}
.a2 .find input{padding:0 16px 0 44px;background:var(--grp);min-height:44px;border-radius:12px;font:400 17px/1.2 var(--font)}
.find input:focus{outline:0;box-shadow:0 0 0 2px var(--ac) inset}
.find svg{position:absolute;left:14px;top:12px;width:20px;height:20px;stroke:var(--mut);fill:none;stroke-width:1.8;stroke-linecap:round;pointer-events:none}
@media (max-width:760px){.side{display:none}}
body.a2{margin:0;background:var(--bg);color:var(--fg);font:400 17px/1.4 var(--font);-webkit-font-smoothing:antialiased}
.a2 .app{display:flex;min-height:100vh;grid-template-columns:none}
.a2 .pane{flex:1 1 auto;min-width:0;padding:0 clamp(16px,4vw,48px) 96px}
.a2 .col{max-width:720px;margin:0 auto}
.a2 .brand .lt{display:block}.a2 .brand .dk{display:none}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]) .brand .lt{display:none}:root:not([data-theme=light]) .brand .dk{display:block}}
:root[data-theme=dark] .brand .lt{display:none}:root[data-theme=dark] .brand .dk{display:block}
.bottom{display:none;position:fixed;left:0;right:0;bottom:0;z-index:40;background:color-mix(in srgb,var(--side) 90%,transparent);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);border-top:1px solid var(--sep);padding:6px 4px calc(6px + env(safe-area-inset-bottom));justify-content:space-around}
.bottom a{display:flex;flex-direction:column;align-items:center;gap:3px;min-width:56px;padding:4px 6px;border-radius:10px;color:var(--mut);font:500 11px/1 var(--font);text-decoration:none}
.bottom a svg{width:24px;height:24px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.bottom a[aria-current=page]{color:var(--ac)}
.a2 .foot2{margin:40px 0 0;color:var(--mut);font-size:13px;text-align:center}.a2 .foot2 a{color:var(--mut)}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
@media (max-width:760px){
 .a2 .app{display:block}.a2 .pane{padding:0 16px 120px}
 .bottom{display:flex!important}.lt{font-size:30px}
 .bar .pick .st{display:none}
}
"""


def sidebar_html(active: str, *, buttons: bool = False) -> str:
    """The sidebar. ``buttons`` makes the items buttons (the settings page switches pages without a reload); otherwise they are links."""
    items = []
    for ident, label, path, icon in NAV:
        cur = ' aria-current="page"' if ident == active else ""
        svg = f'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="{icon}"/></svg>'
        items.append(f'<a href="{path}" data-nav="{ident}"{cur}>{svg}{label}</a>')
    return (
        f'<nav class="side" aria-label="Sections"><a class="brand" href="/settings#home"><img class="lt" src="{BRAND_ICON.format(theme="light")}" alt="" width="30" height="30"><img class="dk" src="{BRAND_ICON.format(theme="dark")}" alt="" width="30" height="30">MaiPai for StackChan</a>'
        f'<div class="nv">{"".join(items)}</div><div class="foot">{SPONSOR_LINE}</div></nav>'
    )


def search_html() -> str:
    """The wide search field. On a page that is not the settings page it sends the question to the settings page, which shows the answers."""
    return (
        '<form class="find" role="search" action="/settings" method="get"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M11 4a7 7 0 100 14 7 7 0 000-14zM21 21l-5-5"/></svg>'
        f'<input type="search" name="q" aria-label="{SEARCH_PLACEHOLDER}" placeholder="{SEARCH_PLACEHOLDER}" autocomplete="off"></form>'
    )


def bottom_html(active: str) -> str:
    """The five items as a bar at the foot of a phone screen."""
    links = "".join(
        f'<a href="{path}" data-nav="{ident}"{" aria-current=page" if ident == active else ""}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="{icon}"/></svg>{label}</a>'
        for ident, label, path, icon in NAV
    )
    return f'<nav class="bottom" aria-label="Sections">{links}</nav>'


# The pages wrapped by dashboard_shell keep their own colors under these names; the new tokens replace them.
WRAPPED_CSS = """
:root:root:root{--card:var(--grp);--card2:var(--grp2);--line:var(--sep);--muted:var(--mut);--accent:var(--ac);--on-accent:var(--on-ac);--good:var(--ok);--surface:var(--grp)}
.a2 main{max-width:none;margin:0;padding:0 0 24px;font:400 17px/1.45 var(--font)}
.a2 main>h1:first-child{font:700 34px/1.1 var(--font);letter-spacing:-.025em;margin:18px 0 12px}
.a2 main h2{font:600 13px/1.2 var(--font);color:var(--mut);text-transform:uppercase;letter-spacing:.04em;margin:24px 0 8px 4px}
.a2 .card{background:var(--grp);border-radius:14px;border:0;padding:16px}
.a2 button{background:var(--ac);color:var(--on-ac);border-radius:10px;font:600 16px/1 var(--font)}
.a2 button.plain{background:transparent;color:var(--ac);border:1px solid var(--ac)}
.a2 input,.a2 select{background:var(--grp2);color:var(--fg);border:0;border-radius:10px;min-height:44px;padding:0 12px;font:400 17px/1.2 var(--font)}
"""
