# Accelerometer games: the design

Rank 5, 6, 9 and 10 of `docs/plan/more-games.md` (Balance, Maze, Racing, Flying). Design only: no screens, no patches yet. This page says what each game costs against the budget (`docs/plan/games-visual-budget.md`), what the one engine change is, how the tilt reaches a game, and how the playground and the bench check it before a game is written.

## 1. What the unit can give

Facts read from the b66 tree (`hal_imu.cpp`, `maipai_games.cc`, `maipai_games_input_core.h`):

- The accelerometer sits in the head. It reads about +1 g along the axis that points up when the unit stands. A roll to the unit's right turns the pull toward +x, a roll to its left toward -x; face down is toward -z, on its back toward +z.
- The IMU task runs every 20 ms and hands **every** sample to `maipai_games_imu_feed(ax, ay, az, now_ms)` (patch UI15). The gentle shake sees all of them; the tilt detector sees every fifth (10 per second) and answers only with four events: left, right, forward, back, each when the filtered pull leaves the rest pose by about 22 degrees (0.38 g) for two samples.
- The rest pose is the pose the unit rests in when the game starts and follows a pose held still for 0.8 s, so a head that looks a little up or down reads as level. Nothing counts while the pull's length is not one g (the unit is moving or carried) or for 0.7 s after a shake.
- A game never drives the head, and a carried unit never starts a tilt game (the motion limiter already refuses head motion when carried).

The discrete tilt is enough for Racing (one lane change per clear lean) and Flying (up and down by steps). Balance and Maze want a continuous value.

## 2. The one engine change: an analog tilt reading

Spec for the firmware track (patch number from the series, for example `SFxx-analog-tilt-for-games`; pure core plus a few lines, no new task, no heap):

1. **Pure core** in `maipai_games_input_core.h`, below the draft in section 5: `mgi_analog_t` holds a low-pass filtered pull (`f[3]`, 12 bytes) and the two outputs; `mgi_analog_update(&a, x, y, z, rest)` is called with **every** 20 ms sample and takes the rest pose of the existing tilt detector (`mgi_t.rest`). It returns two values in permille of a full lean: roll (right positive) and pitch (forward positive). The dead zone is 0.10 g (the head's own wobble reads as flat), full scale 0.50 g (about 30 degrees), clamped at plus and minus 1000. The filter is a single pole with alpha 0.25 per 20 ms sample (a time constant of about 70 ms: calm at 30 fps, quick enough to steer). When the pull's length is outside 7.0 to 12.6 m/s^2 (the unit is moving) or less than 700 ms after a shake, the reading is **not valid** and both values are 0.
2. **The feed**: in `maipai_games_imu_feed`, call `mgi_analog_update` on every sample before the `++s_imu_pass % 5` line, and store the two int16 values and the valid flag packed in one `std::atomic<uint32_t>` (relaxed). That is 4 bytes of RAM and nothing else: no lock, as the comment on the feed already requires ("atomics only inside").
3. **The reader**: `bool maipai_games_tilt_analog(int* roll_pm, int* pitch_pm)` loads the atomic and returns its valid flag. A game calls it once per tick (30 ms). It works for the data-pack games and the grid games alike (the grid listens too since SF77).
4. **Cost**: about 0.4 KB of code, 4 bytes of RAM, no frame cost, no change when no game is active (the feed returns early today).
5. **Bench and tests**: `self.game.bench_tilt {roll_pm, pitch_pm}` (bench builds only) forces the reading so a game can be driven without moving the unit, like `bench_event`; the host C test is the one in section 5 extended with the properties listed there.
6. **Safety**: unchanged rules. A reading is never valid while carried or shaken; a tilt game does not start while the unit is carried; the head does not move for a game.

## 3. The games, against the budget

How each plays, what moves, what it costs. Flash and state are estimates from the two measured analogs (Pong 1.7 KB and the flyer 1.3 KB with their screens, compiled with the unit's compiler) and the plan's table; the dirty area per tick is from `scripts/virtual-unit/tilt_games_budget.py`, which plays 20 seconds of each design and counts the rectangles a game would invalidate (the old and the new place of every moving thing, thin edge columns for a flat shape that scrolls a few pixels); the same method measured Pong and the flyer, and `games_cost.py` replaces these numbers once the screens exist.

| Game | Plays | Input | Flash KB | State, bytes | LVGL objects | Ends |
|---|---|---|---:|---:|---:|---|
| Balance | a ball on a round plate rolls toward the lean; keep it on the plate and out of the holes as long as you can | analog roll and pitch | 1.5 | 40 | 3 (root, one draw object, grabber) | Game over with the seconds (score-only) |
| Maze | an 8 by 8 maze from a seed (a generator of about 60 lines); roll the marble to the goal, a new maze each time | analog | 2.5 | 150 | 3 | You won with the time; a give-up button is the only target |
| Racing | three lanes, the road scrolls, dodge the cars | discrete left and right (analog optional for a smooth slide) | 2.0 | 70 | 3 | Game over with the distance |
| Flying | fly the plane through rings that grow toward you | discrete up and down by steps (analog optional) | 2.0 | 70 | 3 | Game over with the rings |

| Game | Dirty pixels per tick (mean) | Worst tick | Flush ms (mean) | Flush ms (worst) |
|---|---:|---:|---:|---:|
| Balance | 870 | 1,018 | 0.3 | 0.4 |
| Maze | 303 | 878 | 0.1 | 0.3 |
| Racing | 5,079 | 5,808 | 2.0 | 2.3 |
| Flying | 6,422 | 7,938 | 2.5 | 3.1 |

All four stay far under the rule (mean dirty area at most 12,000 pixels, worst at most 22,000; a full screen is 76,800): Balance and Maze move a small thing (under 1,000 pixels a tick), Racing and Flying scroll and grow (5,000 to 6,400 pixels, 2 to 3 ms of flush). The sum of the four is about 8 KB of flash and never more than 0.4 KB of internal RAM on screen (3 objects each), against the 1.29 to 1.99 MB the lean images free. Flash and RAM are not the limit; the bench's tick gaps are, as for every game.

Order to build them: **Balance and Maze first** (smallest, they need the analog reading and are what it is for), then **Racing**, then **Flying**. Racing and Flying could ship before the analog reading with the discrete tilt; they are better with it.

## 4. The playground and the bench

- **Playground:** the virtual unit's hardware model gets a tilt control (roll and pitch in degrees) that feeds the same core as the unit's code, so a scenario can lean the robot and a screen frame shows the ball roll. The 3D robot already leans with the head; this is the same number. `self.game.bench_tilt` is simulated like `bench_event`.
- **Tests before a game exists:** the core test in section 5 runs on the host against the draft; a game's own core test then drives it with scripted readings (a lean for 3 seconds rolls the ball to the edge, flat stops it, a shake is ignored).
- **Bench:** a train (`docs/dev/measure-a-game.md`) with `bench_tilt` steps, the heap before and during, and `bench_record` / `bench_frames` for the tick gaps. The one number only the bench can give is the real range of a hand lean on a unit that sits on a desk; the full scale of 0.50 g is chosen so that a 30 degree lean reaches it, and the bench should confirm that a person can steer with it (the first run measures the readings of a gentle lean left, right, forward and back).

## 5. The core, drafted and checked

The draft below is the whole pure core of section 2. `host/tests/test_accel_games_design.py` extracts it and compiles it against a test program that checks: a still unit reads (0, 0); a lean of 0.25 g reads about half scale; the dead zone holds below 0.10 g; the output clamps at plus and minus 1000; a pull of the wrong length (carried, shaken) reads 0 and not valid; a shake's quiet time reads not valid; the sign of right and forward is as written; and it needs no clock, no heap and no float library call beyond the arithmetic.

```c
/* Patch SFxx (draft): the analog tilt for games. Called with every 20 ms accelerometer sample (m/s^2). Pure C99, no clock of its own (the caller passes the time). */
#define MGA_ALPHA 0.25f          /* a single pole at 50 Hz: a time constant of about 70 ms */
#define MGA_DEAD_G 0.10f         /* the head's own wobble reads as flat */
#define MGA_FULL_G 0.50f         /* about 30 degrees reads as full scale */
#define MGA_MIN_MAG 7.0f         /* m/s^2: the same window as the tilt detector's */
#define MGA_MAX_MAG 12.6f
#define MGA_QUIET_MS 700u        /* no reading right after a shake */

typedef struct {
    float f[3];
    int primed;
    int roll_pm, pitch_pm, valid;   /* permille of a full lean: right and forward positive */
} mga_t;

static inline int mga_scale(float d)   /* d in m/s^2 from the rest pose */
{
    const float g = d / 9.80665f, a = g < 0 ? -g : g;
    if (a < MGA_DEAD_G) return 0;
    float v = (a - MGA_DEAD_G) / (MGA_FULL_G - MGA_DEAD_G) * 1000.0f;
    if (v > 1000.0f) v = 1000.0f;
    return g < 0 ? -(int)v : (int)v;
}

/* x, y, z: one sample. rest: the rest pose of the tilt detector. quiet: nonzero right after a shake. Returns the valid flag. */
static inline int mga_update(mga_t* a, float x, float y, float z, const float rest[3], int quiet)
{
    const float in[3] = {x, y, z};
    for (int i = 0; i < 3; i++) a->f[i] = a->primed ? a->f[i] + MGA_ALPHA * (in[i] - a->f[i]) : in[i];
    a->primed = 1;
    const float m2 = a->f[0] * a->f[0] + a->f[1] * a->f[1] + a->f[2] * a->f[2];
    if (quiet || m2 < MGA_MIN_MAG * MGA_MIN_MAG || m2 > MGA_MAX_MAG * MGA_MAX_MAG) {
        a->roll_pm = a->pitch_pm = 0;
        a->valid = 0;
        return 0;
    }
    a->roll_pm = mga_scale(a->f[0] - rest[0]);        /* a roll to the unit's right turns the pull toward +x */
    a->pitch_pm = -mga_scale(a->f[2] - rest[2]);      /* forward is toward -z, so forward reads positive */
    a->valid = 1;
    return 1;
}
```
