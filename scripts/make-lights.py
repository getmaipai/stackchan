#!/usr/bin/env python3
"""Intent: draw the robot's ring colours and tone shapes as small animated SVGs for the docs.
Usage: python3 -I scripts/make-lights.py   (writes docs/images/light-*.svg and tone-*.svg)."""
import math, pathlib
out = pathlib.Path(__file__).resolve().parent.parent / 'docs' / 'images'

def ring(name, alt, colour=None, anim='steady', dur=2, rainbow=False, back_red=False, dim=False):
    dots = ''
    for i in range(12):
        a = math.radians(i * 30 - 90)
        x, y = 80 + 56 * math.cos(a), 38 + 20 * math.sin(a)
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
    extra = '<circle cx="80" cy="38" r="5" fill="#ef4444"/><circle cx="80" cy="38" r="9" fill="#ef4444" opacity=".35"/>' if back_red else ''
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 76" width="160" height="76" role="img" aria-label="{alt}">'
           '<defs><filter id="b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter></defs>'
           '<rect width="160" height="76" rx="14" fill="#10141b"/><ellipse cx="80" cy="38" rx="68" ry="27" fill="#161b24" stroke="#232b38" stroke-width="2"/>'
           f'{extra}{group}</svg>\n')
    (out / f'{name}.svg').write_text(svg)

ring('light-green', 'A ring of twelve green lights, glowing steady.', '#22c55e')
ring('light-pink', 'A ring of twelve pink lights flashing twice, then glowing steady.', '#ec4899', 'flash', 3)
ring('light-cyan', 'A ring of twelve cyan lights pulsing slowly.', '#06b6d4', 'pulse', 2)
ring('light-amber', 'A ring of twelve amber lights giving one short pulse, then waiting.', '#f59e0b', 'blip', 6)
ring('light-blue', 'A ring of twelve blue lights, glowing steady.', '#3b82f6')
ring('light-white', 'A ring of twelve white lights pulsing fast.', '#f8fafc', 'pulse', 1)
ring('light-dark', 'A ring of twelve lights, all off.', None)
ring('light-charging', 'A ring of lights off, with one small red light glowing at the back.', None, back_red=True)
ring('light-rainbow', 'A ring of twelve lights where the colour walks around the ring, one turn every two seconds.', rainbow=True)
ring('light-beat', 'A ring of twelve lights pulsing together in time with the music, the colour stepping on each beat.', 'beat', 'beat')

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
