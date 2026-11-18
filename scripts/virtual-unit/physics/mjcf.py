"""Build the physics model text (MJCF) of a pan-tilt desk robot from its description file (robots/NAME.robot.json). Pure Python, no engine needed.

The driver and the browser never read numbers from anywhere else: a robot is its description file. This builder knows the pan-tilt family (a base, a yaw
hinge, a pitch hinge, a head with an IMU); a robot with another layout adds its own builder next to this one and the same driver runs it.
Placement: host-side development tool; no firmware change. Upstream: none."""

from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str = "stackchan") -> dict:
    return json.loads((HERE / "robots" / f"{name}.robot.json").read_text())


def value(desc: dict, key: str):
    return desc["params"][key]["v"]


def provenance(desc: dict) -> dict[str, list[str]]:
    """parameter names grouped by their src (measured, assumed, "fitted, low confidence" or "fitted, measured on the unit" after a calibration): the groups the docs report."""
    out: dict[str, list[str]] = {"measured": [], "assumed": []}
    for key, entry in desc["params"].items():
        out.setdefault(entry["src"], []).append(key)
    return out


def _f(x: float) -> str:
    return f"{x:.6g}"


def mjcf(desc: dict) -> str:
    p = lambda k: value(desc, k)  # noqa: E731
    yaw_z = p("yaw_axis_z")                   # the yaw hinge, on the yaw axis
    pitch_rel = p("pitch_axis_z") - yaw_z     # the nod axis above the yaw hinge
    yaw = next(j for j in desc["joints"] if j["role"] == "head.yaw")
    pitch = next(j for j in desc["joints"] if j["role"] == "head.pitch")
    yr, pr = p(yaw["range"]), p(pitch["range"])
    tl = p("torque_limit")
    damp, fric, arm = p("joint_damping"), p("joint_friction"), p("joint_armature")
    ax = lambda j: " ".join(str(int(a)) for a in j["axis"])  # noqa: E731
    fr = f"{_f(p('table_friction'))} 0.005 0.0001"
    # Collision groups: the head box is a plain box, bigger than the real shell's outline, and would hit the base plate when it nods; the model's own collision sweep
    # finds the real head clear of the base over the whole range. So the head touches the table (when the unit tips over) but not the base.
    return f"""<mujoco model="{desc['robot']}">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="{_f(p('timestep'))}" gravity="0 0 -9.81" integrator="implicitfast"/>
  <worldbody>
    <geom name="table" type="plane" size="1 1 0.01" friction="{fr}" contype="1" conaffinity="3" rgba="0.2 0.2 0.25 1"/>
    <body name="base" pos="0 0 {_f(p('base_h') / 2)}">
      <freejoint name="base_free"/>
      <geom name="base_plate" type="box" pos="{_f(p('base_center_x'))} 0 0" size="{_f(p('base_d') / 2)} {_f(p('base_w') / 2)} {_f(p('base_h') / 2)}" mass="{_f(p('mass_base'))}" friction="{fr}"/>
      <site name="base_imu" pos="0 0 0" size="0.002"/>
      <body name="yaw_link" pos="0 0 {_f(yaw_z - p('base_h') / 2)}">
        <joint name="{yaw['name']}" type="hinge" axis="{ax(yaw)}" range="{_f(math.radians(yr[0]))} {_f(math.radians(yr[1]))}" limited="true" damping="{_f(damp)}" frictionloss="{_f(fric)}" armature="{_f(arm)}"/>
        <geom name="neck" type="box" size="{_f(p('neck_d') / 2)} {_f(p('neck_w') / 2)} {_f(pitch_rel / 2)}" pos="0 0 {_f(pitch_rel / 2)}" mass="{_f(p('mass_neck'))}" contype="0" conaffinity="0"/>
        <body name="pitch_link" pos="0 0 {_f(pitch_rel)}">
          <joint name="{pitch['name']}" type="hinge" axis="{ax(pitch)}" range="{_f(math.radians(pr[0]))} {_f(math.radians(pr[1]))}" limited="true" damping="{_f(damp)}" frictionloss="{_f(fric)}" armature="{_f(arm)}"/>
          <geom name="head" type="box" size="{_f(p('head_d') / 2)} {_f(p('head_w') / 2)} {_f(p('head_h') / 2)}" pos="{_f(p('head_center_x'))} 0 0" mass="{_f(p('mass_head'))}" friction="{fr}" contype="2" conaffinity="2"/>
          <site name="imu" pos="{_f(p('head_center_x'))} 0 0" size="0.002"/>
        </body>
      </body>
    </body>
  </worldbody>
  <actuator>
    <position name="{yaw['name']}_servo" joint="{yaw['name']}" kp="{_f(p(yaw['kp']))}" kv="{_f(p(yaw['kv']))}" forcerange="{_f(-tl)} {_f(tl)}"/>
    <position name="{pitch['name']}_servo" joint="{pitch['name']}" kp="{_f(p(pitch['kp']))}" kv="{_f(p(pitch['kv']))}" forcerange="{_f(-tl)} {_f(tl)}"/>
  </actuator>
  <sensor>
    <accelerometer name="imu_accel" site="imu"/>
    <gyro name="imu_gyro" site="imu"/>
    <jointpos name="yaw_pos" joint="{yaw['name']}"/>
    <jointpos name="pitch_pos" joint="{pitch['name']}"/>
    <actuatorfrc name="yaw_force" actuator="{yaw['name']}_servo"/>
    <actuatorfrc name="pitch_force" actuator="{pitch['name']}_servo"/>
    <accelerometer name="base_accel" site="base_imu"/>
  </sensor>
</mujoco>
"""


def total_mass(desc: dict) -> float:
    return sum(value(desc, k) for k in ("mass_base", "mass_neck", "mass_head"))
