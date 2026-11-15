#!/usr/bin/env python3
"""Intent: draw an SVG placeholder for every screenshot named in the docs, and swap the text note for an image.
Usage: python3 -I scripts/make-placeholders.py   (idempotent; real screenshots replace an svg of the same name later)."""
import re, pathlib, html, textwrap
root = pathlib.Path(__file__).resolve().parent.parent
note = re.compile(r'^(?P<indent>\s*)> \*\*Screenshot placeholder:\*\* `(?P<name>[a-z0-9-]+)\.png`\. (?P<desc>.+)$', re.M)
robot_names = re.compile(r'^(hero|listening|reactions|low-battery|timer-ring|alarm-ringing|clock-face|face-styles|face-colors|quick-sliders|camera-cue|countdown|game-.*|mood-faces|agent-status|build-light|first-turn|pairing-code)$')
def svg(name, desc):
    robot = bool(robot_names.match(name))
    w, h = (320, 240) if robot else (640, 400)
    lines = textwrap.wrap(desc, 34 if robot else 70)[:4]
    t = ''.join(f'<text x="{w//2}" y="{h//2+28+i*18}" text-anchor="middle" font-size="13" fill="#6b7280">{html.escape(l)}</text>' for i, l in enumerate(lines))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{html.escape(desc)}">'
            f'<rect width="{w}" height="{h}" rx="12" fill="#e5e7eb"/><rect x="6" y="6" width="{w-12}" height="{h-12}" rx="8" fill="none" stroke="#9ca3af" stroke-width="2" stroke-dasharray="8 6"/>'
            f'<g transform="translate({w//2-24},{h//2-62})" fill="none" stroke="#6b7280" stroke-width="3"><rect width="48" height="36" rx="5"/><circle cx="24" cy="18" r="8"/><path d="M14 0l4-6h12l4 6"/></g>'
            f'<text x="{w//2}" y="{h//2-4}" text-anchor="middle" font-size="15" font-weight="600" fill="#374151" font-family="system-ui,sans-serif">Screenshot coming: {html.escape(name)}</text>'
            f'<g font-family="system-ui,sans-serif">{t}</g></svg>\n')
for md in [root/'README.md', *sorted((root/'docs'/'user').glob('*.md'))]:
    text = md.read_text(); prefix = 'docs/images/' if md.name == 'README.md' else '../images/'
    def sub(m):
        (root/'docs'/'images'/f"{m['name']}.svg").write_text(svg(m['name'], m['desc']))
        return f"{m['indent']}![{m['desc']}]({prefix}{m['name']}.svg)"
    new = note.sub(sub, text)
    if new != text: md.write_text(new)
