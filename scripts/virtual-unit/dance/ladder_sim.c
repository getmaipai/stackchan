/* The real dance ladder core (firmware patch MD01, maipai_dance_ladder_core.h) behind a plain C interface for ctypes: the virtual unit calls the unit's own step rule,
 * pose table, head budget and ring swell, never a copy of them. The header is cut out of the patch by dance_core.py. Placement: host-side development tool. Upstream: none. */
#include <stdlib.h>
#include "maipai_dance_ladder_core.h"

typedef struct {
    mdl_t st;
    mdl_energy_t en;
    mdl_budget_t bud;
} sim_t;

sim_t* sim_new(void)
{
    sim_t* s = (sim_t*)calloc(1, sizeof(*s));
    return s;
}

void sim_start(sim_t* s, int max_stage, uint32_t now_ms)
{
    mdl_start(&s->st, max_stage, now_ms);
    mdl_energy_reset(&s->en);
    mdl_budget_reset(&s->bud);
}

void sim_set_max(sim_t* s, int max_stage) { s->st.max_stage = (uint8_t)max_stage; }
int sim_stage(const sim_t* s) { return s->st.stage; }
int sim_down(const sim_t* s) { return s->st.down; }

/* one second of the unit's own ladder (maipai_music.cc ladder_tick): the energy average, then the step. Returns the stage; the average is written to *avg. */
int sim_tick(sim_t* s, uint32_t now_ms, uint32_t period_ms, int level, int tc, int music, int* avg)
{
    *avg = mdl_energy_push(&s->en, level);
    mdl_in_t in = {now_ms, period_ms, *avg, tc, music};
    return mdl_step(&s->st, &in);
}

int sim_effective(int stage, uint32_t no_beat_ms) { return mdl_effective_stage(stage, no_beat_ms); }
uint32_t sim_dwell(int stage, int down, uint32_t period_ms) { return mdl_dwell_ms(stage, down, period_ms); }
void sim_budget_reset(sim_t* s) { mdl_budget_reset(&s->bud); }
int sim_budget_take(sim_t* s, uint32_t now_ms) { return mdl_budget_take(&s->bud, now_ms); }
int sim_swell(uint32_t phase_ms, uint32_t span_ms) { return mdl_swell(phase_ms, span_ms); }

void sim_pose(int stage, int side, int beat, uint32_t span_ms, int loud, int out[6])
{
    mdl_pose_t p = mdl_pose(stage, side, beat, span_ms, loud);
    out[0] = p.eye_x; out[1] = p.eye_y; out[2] = p.head; out[3] = p.yaw; out[4] = p.pitch; out[5] = p.speed;
}

void sim_ring(uint8_t out[36], int swell, int side, uint32_t turn)
{
    uint8_t px[MDL_RING_PIXELS][3];
    mdl_ring_frame(px, swell, side, turn);
    memcpy(out, px, 36);
}

int sim_consts(int which)
{
    switch (which) {
        case 0: return MDL_LEVEL_HIGH;
        case 1: return MDL_BUDGET_MOVES;
        case 2: return MDL_CLIMB_TC_2;
        case 3: return MDL_CLIMB_TC_3;
        case 4: return MDL_CLIMB_TC_4;
        case 5: return MDL_CLIMB_LEVEL_3;
        case 6: return MDL_CLIMB_LEVEL_4;
        default: return -1;
    }
}

/* ---- the dance session of patch SF51: a synthetic beat and the show (core functions of the same header) ---- */
typedef struct { mdl_synth_t y; uint32_t rng; uint8_t hist[2]; } synth_t;

synth_t* synth_new(void) { synth_t* s = (synth_t*)calloc(1, sizeof(*s)); s->hist[0] = s->hist[1] = 0xff; return s; }
void synth_start(synth_t* s, uint32_t now_ms, int bpm, uint32_t total_ms, uint32_t seed) { mdl_synth_start(&s->y, now_ms, bpm, total_ms); s->rng = seed | 1u; s->hist[0] = s->hist[1] = 0xff; }
uint32_t synth_period(const synth_t* s) { return s->y.period_ms; }
void synth_input(const synth_t* s, uint32_t now_ms, int out[5]) { mdl_in_t in; mdl_synth_input(&s->y, now_ms, &in); out[0] = (int)in.now_ms; out[1] = (int)in.period_ms; out[2] = in.level; out[3] = in.tc; out[4] = in.music; }
/* one second of a session: the synthetic input, then the step. Returns the stage. */
int sim_synth_tick(sim_t* s, synth_t* y, uint32_t now_ms) { mdl_in_t in; mdl_synth_input(&y->y, now_ms, &in); return mdl_step(&s->st, &in); }
int synth_bpm_for(const char* name) { return mdl_synth_bpm_for(name); }
void show_for_step(int previous, int stage, int out[4]) { mdl_show_t sh; mdl_show_for_step(previous, stage, &sh); out[0] = sh.notes; out[1] = sh.disco; out[2] = sh.confetti; out[3] = sh.clear_overlays; }
int synth_face_next(synth_t* s, int stage) { return mdl_face_next(&s->rng, stage, s->hist); }
const char* face_name(int i) { return MDL_FACES[i]; }
void ring_breath(uint8_t out[36], uint32_t t_ms, uint32_t beat_ms, int full_depth) { uint8_t px[MDL_RING_PIXELS][3]; mdl_ring_breath(px, t_ms, beat_ms, full_depth); memcpy(out, px, 36); }
void ring_chase(uint8_t out[36], uint32_t beat_index, int level_pct, int down) { uint8_t px[MDL_RING_PIXELS][3]; mdl_ring_chase(px, beat_index, level_pct, down); memcpy(out, px, 36); }
