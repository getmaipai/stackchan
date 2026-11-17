#!/usr/bin/env python3
"""Writes the renderer script for the game screens (patch UI13): usage scene_games.py <packs dir> <out dir>. The state and counter numbers are the
places of the names in each pack's table (firmware/games/<game>.json)."""
import sys

packs, out = sys.argv[1], sys.argv[2]
L = []


def snap(name):
    L.append(f"snap {out}/{name}.png")


def game(name, *cmds):
    L.append(f"load {packs}/{name}.mpk")
    L.extend(cmds)


L.append("guides off")
# whack-a-mole: counters score0 moles1 cell2 face3 miss4; states intro0 down1 up2 hit3 over4
game("whack", "state 0"); snap("whack_intro")
L += ["state 1", "ctr 0 3", "ctr 2 -1"]; snap("whack_down")
for face, cell in ((0, 4), (1, 1), (2, 6), (3, 8)):
    L += ["state 2", f"ctr 3 {face}", f"ctr 2 {cell}", "ctr 4 -1"]; snap(f"whack_up_face{face}")
L += ["state 3", "ctr 3 4", "ctr 2 4", "ctr 0 4"]; snap("whack_hit_dazed")
L += ["state 2", "ctr 3 0", "ctr 2 5", "ctr 4 2"]; snap("whack_miss_mark")
L += ["guides on", "state 2", "ctr 3 0", "ctr 2 0", "ctr 4 -1"]; snap("whack_layout_guides"); L.append("guides off")
L += ["state 4", "ctr 0 11"]; snap("whack_over")
L += ["lang es", "state 2", "ctr 3 1", "ctr 2 4", "ctr 4 -1"]; snap("whack_up_es"); L.append("lang en")
# tic-tac-toe: counters score0 diff1 cell2 move3 res4 said5 row6 col7; states menu0 turn1 pcheck2 think3 bcheck4 win5 lose6 draw7
game("tictactoe", "state 0"); snap("ttt_menu")
L += ["guides on"]; snap("ttt_menu_guides"); L += ["guides off"]
cells = {0: 1, 4: 2, 8: 1, 2: 2, 6: 1}
L.append("state 1")
for i, v in cells.items():
    L.append(f"board {i} {v}")
L += ["ctr 5 1", "ctr 6 2", "ctr 7 3"]; snap("ttt_turn")
L += ["state 3", "ctr 5 0"]; snap("ttt_think")
L += ["state 5", "ctr 5 1", "board 1 1", "board 2 1", "board 4 1"]; snap("ttt_win")
L += ["state 6", "board 0 2", "board 1 2", "board 2 2", "board 4 1", "board 8 1", "board 6 1"]; snap("ttt_lose")
L += ["lang es", "state 0"]; snap("ttt_menu_es"); L.append("lang en")
# do it (button game): counters score0 act1 limit2 tmp3 cue4 z5; states intro0 pick1 call2 ok3 over4
game("bopit", "state 0"); snap("doit_intro")
for act in (0, 1, 3, 5):
    L += ["state 2", f"ctr 1 {act}", f"ctr 0 {act + 3}"]
    snap(f"doit_call_{act}")
L += ["state 3", "ctr 0 7"]; snap("doit_ok")
L += ["state 4", "ctr 0 7"]; snap("doit_over")
L += ["guides on", "state 2", "ctr 1 4"]; snap("doit_guides"); L.append("guides off")
L += ["lang es", "state 2", "ctr 1 2"]; snap("doit_call_es"); L.append("lang en")
# rock paper scissors: counters score0 me1 bot2 d3; states intro0 choose1 beat1 2 beat2 3 beat3 4 beat4 5 reveal6 win7 tie8 lose9 over10
game("rps", "state 0"); snap("rps_intro")
L += ["state 1", "ctr 0 2", "ctr 1 -1", "ctr 2 -1"]; snap("rps_choose")
L += ["guides on"]; snap("rps_choose_guides"); L += ["guides off"]
L += ["state 3", "ctr 1 1"]; snap("rps_beat_paper_picked")
L += ["state 5"]; snap("rps_beat_shoot")
L += ["state 7", "ctr 1 0", "ctr 2 2"]; snap("rps_win_rock_beats_scissors")
L += ["state 9", "ctr 1 0", "ctr 2 1"]; snap("rps_lose_paper_beats_rock")
L += ["state 8", "ctr 1 2", "ctr 2 2"]; snap("rps_tie_scissors")
L += ["state 10", "ctr 0 3"]; snap("rps_over")
L += ["lang es", "state 1", "ctr 1 -1", "ctr 2 -1"]; snap("rps_choose_es")
# magic 8 ball: counters score0 ans1 kind2 z3; states ready0 shake1 answer2 easy3
L += ["lang en"]
game("eightball", "state 0"); snap("ball_ready")
L += ["state 1"]; snap("ball_shake")
L += ["state 2", "ctr 1 3", "ctr 2 0"]; snap("ball_yes")
L += ["ctr 1 14", "ctr 2 1"]; snap("ball_maybe_long")
L += ["ctr 1 16", "ctr 2 2"]; snap("ball_no")
L += ["state 3"]; snap("ball_easy")
L += ["lang es", "state 2", "ctr 1 10", "ctr 2 1"]; snap("ball_es")
L += ["guides on"]; snap("ball_guides"); L += ["guides off", "lang en"]
# dice and coin: counters mode0 d1 1 d2 2 c3 cf4 tot5 z6 k7; states idle0 r1..r6 1..6 land7 easy8
game("dice", "state 0", "ctr 0 0", "ctr 1 4"); snap("dice_idle")
L += ["state 3", "ctr 1 2"]; snap("dice_tumble")
L += ["state 7", "ctr 1 6", "ctr 7 1"]; snap("dice_land_6")
L += ["ctr 0 1", "ctr 1 3", "ctr 2 5", "ctr 5 8", "ctr 7 2"]; snap("dice_two")
L += ["ctr 0 2", "ctr 3 0", "ctr 7 3"]; snap("coin_heads")
L += ["ctr 3 1", "ctr 7 4"]; snap("coin_tails")
L += ["state 2", "ctr 3 2"]; snap("coin_edge")
L += ["state 8"]; snap("dice_easy")
L += ["guides on", "state 7", "ctr 0 1", "ctr 7 2"]; snap("dice_guides"); L += ["guides off"]
L += ["lang es", "ctr 0 2", "ctr 3 0", "ctr 7 3"]; snap("coin_es")
# motion keyframes (patch UI15): a change is drawn at t=1000 and the picture is taken some milliseconds later
def key(game_name, name, dts, setup):
    for dt in dts:
        L.append(f"load {packs}/{game_name}.mpk")  # a fresh game each time: the change below starts its motion at t=1000
        L.extend(setup)
        L.extend(["t 1000", "draw", f"t {1000 + dt}", f"snap {out}/{name}_{dt}.png"])
L.append("clear")
key("whack", "m_pop", (0, 80, 160, 260), ["state 2", "ctr 3 1", "ctr 2 4", "ctr 4 -1"])   # the mole pops up with an overshoot
key("whack", "m_hit", (0, 120, 300), ["state 3", "ctr 3 4", "ctr 2 4"])                       # struck: squashed, stars circling
key("eightball", "b_wobble", (60, 200, 500), ["state 1"])
key("eightball", "b_fade", (60, 180, 400), ["state 2", "ctr 1 7", "ctr 2 0"])
L.append(f"sheet {out}/keys_a.png 4")
L.append("clear")
key("dice", "d_hop", (30, 60, 150, 260), ["state 4", "ctr 0 1", "ctr 1 3", "ctr 2 5"])
key("dice", "c_flip", (30, 120, 260), ["state 7", "ctr 0 2", "ctr 3 0", "ctr 7 3"])
key("rps", "r_bump", (60, 190, 330), ["state 3", "ctr 1 1"])
key("rps", "r_pop", (40, 120, 300), ["state 7", "ctr 1 0", "ctr 2 2"])
key("tictactoe", "t_draw", (40, 120, 250, 400), ["state 1", "board 4 1", "board 0 2", "ctr 5 1", "ctr 6 1", "ctr 7 1"])
key("bopit", "o_pulse", (0, 260, 520), ["state 2", "ctr 1 1", "ctr 0 3"])
L.append(f"sheet {out}/keys_b.png 4")
print("\n".join(L))
