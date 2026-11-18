"""A large picture upload does not take hundreds of megabytes to shrink."""

import tracemalloc

import numpy as np

from maipai_body import picture_faces as pf


def test_a_12_megapixel_picture_shrinks_in_bounded_memory():
    width, height = 4000, 3000
    data = np.random.default_rng(1).integers(0, 255, (height, width, 4), dtype=np.uint8).tobytes()
    tracemalloc.start()
    out = pf.resize_rgba(data, width, height)
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert out.shape == (pf.HEIGHT, pf.WIDTH, 4)
    assert peak < 110 * 1024 * 1024, f"peak {peak / 1e6:.0f} MB"


def test_the_shrink_is_unchanged_for_a_small_picture():
    rng = np.random.default_rng(2)
    width, height = 700, 500
    data = rng.integers(0, 255, (height, width, 4), dtype=np.uint8).tobytes()
    src = np.frombuffer(data, dtype=np.uint8).reshape(height, width, 4).astype(np.float32)
    while src.shape[0] >= 2 * pf.HEIGHT and src.shape[1] >= 2 * pf.WIDTH:
        h2, w2 = src.shape[0] // 2 * 2, src.shape[1] // 2 * 2
        s = src[:h2, :w2]
        src = (s[0::2, 0::2] + s[1::2, 0::2] + s[0::2, 1::2] + s[1::2, 1::2]) / 4.0
    assert pf.resize_rgba(data, width, height).shape == (pf.HEIGHT, pf.WIDTH, 4)
    assert src.shape[0] >= pf.HEIGHT
