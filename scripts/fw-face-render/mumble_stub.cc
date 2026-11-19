// Host renderer stand-in for hal/maipai_mumble.cc (the unit's audio-timed mumble): no mumble plays on the host, so the face never gets a mouth level from it.
// Placement: host-side development tool; no firmware change. Upstream: none.
bool maipai_mumble_level(int*) { return false; }
