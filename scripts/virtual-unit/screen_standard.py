"""The physical screen standard, in one place (docs/design/screen-style.md, "Physical standard"). The panel is a 2.0 inch 320 by 240 glass: 40.6 by 30.5 mm computed from the diagonal (ASSUMED
until someone puts a ruler on the glass: 7.88 pixels a millimeter). Everything below is derived from that one number. Placement: host-side development tool. Upstream: none."""
PANEL_W_PX, PANEL_H_PX = 320, 240
PANEL_DIAGONAL_IN = 2.0
PANEL_W_MM = PANEL_DIAGONAL_IN * 25.4 * 0.8   # 3:4 panel: width is 0.8 of the diagonal
PX_PER_MM = PANEL_W_PX / PANEL_W_MM

PRIMARY_MM = 7.0           # a primary target: 7 mm, 56 px
SECONDARY_MM = 6.0         # a secondary target: 6 mm, 48 px
PRIMARY_PX = 56
SECONDARY_PX = 48
GAP_PX = 8                 # between adjacent targets
MARGIN_PX = 16             # screen margin
LABEL_GAP_PX = 12          # a label and its control
GRID_PX = 8
# Text: LVGL's line height of the fonts the unit has (Noto Sans basic at 16 and 20 px, the 28 px title): body text at least the 20 px font, secondary text the 16 px font, nothing smaller.
LINE_BODY = 23
LINE_SECONDARY = 19


def mm(px: float) -> float:
    return px / PX_PER_MM


def px(mmv: float) -> int:
    return round(mmv * PX_PER_MM)
