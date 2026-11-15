#!/usr/bin/env python3
"""Intent: draw the robot's ring colours and tone shapes as small animated SVGs for the docs.
Usage: python3 -I scripts/make-lights.py   (writes docs/images/light-*.svg and tone-*.svg)."""
import math, pathlib
out = pathlib.Path(__file__).resolve().parent.parent / 'docs' / 'images'

def ring(name, alt, colour=None, anim='steady', dur=2, rainbow=False, back_red=False, dim=False):
    dots = ''
    for i in range(12):
        # two bars of six lights: left bar top to bottom, right bar bottom to top
        x = 44 if i < 6 else 116
        y = 12 + 10.4 * (i if i < 6 else 11 - i)
        if rainbow:
            hues = 'red;yellow;lime;cyan;blue;magenta;red'
            f = f'<animate attributeName="fill" values="{hues}" dur="2s" begin="-{i*2/12:.3f}s" repeatCount="indefinite"/>'
            dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="red">{f}</circle>'
        elif colour == 'beat':
            hues = '#ef4444;#f59e0b;#22c55e;#06b6d4;#3b82f6;#a855f7;#ef4444'
            dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="#ef4444"><animate attributeName="fill" values="{hues}" dur="4.8s" calcMode="discrete" repeatCount="indefinite"/></circle>'
        elif colour:
            dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="{colour}"/>'
        else:
            dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="#2b3340"/>'
    glow = f'<g filter="url(#b)" opacity=".9">{dots}</g>' if (colour or rainbow) else ''
    group = f'<g>{glow}{dots}'
    if anim == 'pulse':
        a = f'<animate attributeName="opacity" values=".18;1;.18" dur="{dur}s" repeatCount="indefinite"/>'
    elif anim == 'blip':
        a = f'<animate attributeName="opacity" values=".18;.18;1;.18;.18" keyTimes="0;.55;.65;.8;1" dur="{dur}s" repeatCount="indefinite"/>'
    elif anim == 'flash':
        a = f'<animate attributeName="opacity" values=".18;1;.18;1;.18;1;1;1" keyTimes="0;.08;.16;.24;.32;.4;.8;1" dur="{dur}s" repeatCount="indefinite"/>'
    elif anim == 'beat':
        a = f'<animate attributeName="opacity" values=".35;1;.35" dur="0.8s" repeatCount="indefinite"/>'
    else:
        a = ''
    group = f'<g>{a}{glow}{dots}</g>'
    extra = '<circle cx="80" cy="30" r="5" fill="#ef4444"/><circle cx="80" cy="30" r="9" fill="#ef4444" opacity=".35"/><text x="80" y="52" text-anchor="middle" font-size="10" font-family="system-ui,sans-serif" fill="#94a3b8">back</text>' if back_red else ''
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 76" width="160" height="76" role="img" aria-label="{alt}">'
           '<defs><filter id="b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter></defs>'
           '<rect width="160" height="76" rx="14" fill="#10141b"/><rect x="30" y="4" width="28" height="68" rx="12" fill="#161b24" stroke="#232b38" stroke-width="2"/><rect x="102" y="4" width="28" height="68" rx="12" fill="#161b24" stroke="#232b38" stroke-width="2"/>'
           f'{extra}{group}</svg>\n')
    (out / f'{name}.svg').write_text(svg)

ring('light-green', 'Two light bars, one on each side, glowing green and steady.', '#22c55e')
ring('light-pink', 'Two light bars glowing pink, flashing twice, then steady.', '#ec4899', 'flash', 3)
ring('light-cyan', 'Two light bars glowing cyan and pulsing slowly.', '#06b6d4', 'pulse', 2)
ring('light-amber', 'Two light bars glowing amber, one short pulse, then waiting.', '#f59e0b', 'blip', 6)
ring('light-blue', 'Two light bars glowing blue and steady.', '#3b82f6')
ring('light-white', 'Two light bars glowing white and pulsing fast.', '#f8fafc', 'pulse', 1)
ring('light-dark', 'Two light bars, all lights off.', None)
ring('light-charging', 'Two light bars off, with one small red charging light glowing at the back.', None, back_red=True)
ring('light-rainbow', 'Two light bars where the colour walks along one bar and up the other, one turn every two seconds.', rainbow=True)
ring('light-beat', 'Two light bars pulsing together in time with the music, the colour stepping on each beat.', 'beat', 'beat')

def tone(name, alt, notes, click=False):
    w = 120; body = ''
    if click:
        for x in (42, 68):
            body += f'<rect x="{x}" y="19" width="10" height="18" rx="3" fill="#94a3b8"/>'
    else:
        n = len(notes); step = (w - 40) / max(n - 1, 1) if n > 1 else 0
        pts = []
        for i, h in enumerate(notes):
            x = 20 + step * i if n > 1 else w / 2
            y = 46 - h * 34
            pts.append((x, y))
        if n > 1:
            body += '<polyline points="' + ' '.join(f'{x:.0f},{y:.0f}' for x, y in pts) + '" fill="none" stroke="#475569" stroke-width="2"/>'
        for x, y in pts:
            body += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="6" fill="#38bdf8"/><circle cx="{x:.0f}" cy="{y:.0f}" r="10" fill="#38bdf8" opacity=".25"/>'
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} 56" width="{w}" height="56" role="img" aria-label="{alt}">'
           f'<rect width="{w}" height="56" rx="12" fill="#10141b"/>{body}</svg>\n')
    (out / f'{name}.svg').write_text(svg)

tone('tone-needs-you', 'Two notes, the second higher.', [0.2, 0.8])
tone('tone-plug-in', 'Two quick notes, the second higher.', [0.3, 0.7])
tone('tone-charged', 'Three notes, each higher than the last.', [0.1, 0.5, 0.9])
tone('tone-unplug', 'One note, lower.', [0.25])
tone('tone-offline', 'Two notes, the second lower.', [0.8, 0.2])
tone('tone-goodbye', 'Three notes, each lower than the last.', [0.9, 0.5, 0.1])
tone('tone-shutter', 'Two short clicks.', [], click=True)
tone('tone-back-online', 'A chime that rises over three notes.', [0.15, 0.5, 0.95])
tone('tone-listening', 'One short rising pop.', [0.6])
tone('tone-low-battery', 'A short chirp, two quick notes.', [0.6, 0.6])
tone('tone-error', 'One low, short tone.', [0.12])


def alert(name, alt):
    dots = ''
    for i in range(12):
        x = 44 if i < 6 else 116
        y = 12 + 10.4 * (i if i < 6 else 11 - i)
        a, b = ('#ef4444', '#3b82f6') if i < 6 else ('#3b82f6', '#ef4444')
        dots += (f'<circle cx="{x}" cy="{y:.1f}" r="6.5" fill="{a}"><animate attributeName="fill" values="{a};{b};{a}" '
                 f'keyTimes="0;.5;1" calcMode="discrete" dur="1s" repeatCount="indefinite"/></circle>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 76" width="160" height="76" role="img" aria-label="{alt}">'
           '<defs><filter id="b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter></defs>'
           '<rect width="160" height="76" rx="14" fill="#10141b"/>'
           '<rect x="30" y="4" width="28" height="68" rx="12" fill="#161b24" stroke="#232b38" stroke-width="2"/>'
           '<rect x="102" y="4" width="28" height="68" rx="12" fill="#161b24" stroke="#232b38" stroke-width="2"/>'
           f'<g filter="url(#b)" opacity=".9">{dots}</g>{dots}</svg>\n')
    (out / f'{name}.svg').write_text(svg)

alert('light-alert', 'Two light bars where the left glows red while the right glows blue, then they swap, twice a second.')
tone('tone-siren', 'A loud siren that rises and falls, over four notes.', [0.15, 0.95, 0.15, 0.95])
