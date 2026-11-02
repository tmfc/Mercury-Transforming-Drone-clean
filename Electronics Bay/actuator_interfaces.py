"""一体式推杆尾耳接口；原图反推高度与新设计横向位置明确区分。

候选尺寸来自用户提供的淘宝“无双耳款”图。包络扫描只检查下舱附近的局部净空，
不构成包含轮臂、齿轮、限位和线束的整机变形验证。
"""
from functools import lru_cache
import itertools

import numpy as np
import trimesh

from chassis_interfaces import (
    ROOT, OUT, RAIL_INNER_X, RAIL_OUTER_X, SHOULDER_Z,
    mesh_interference_volume, pdf_registration,
)
from localization import configure_chinese_font

PIVOT_X = 109.0
PIVOT_Z = 10.5
TAIL_GAP = 8.6
EAR_THICKNESS = 6.0
EAR_RADIUS = 7.0
PIN_DIAMETER = 4.2
EAR_OUTER_Y = TAIL_GAP / 2 + EAR_THICKNESS
CANDIDATE = {
    "source": "用户提供的淘宝无双耳款尺寸图；没有厂家三维实体或完整电气参数。",
    "stroke_mm": 30.0,
    "retracted_pitch_base_mm": 57.5,
    "rear_ear_thickness_mm": 8.0,
    "front_ear_thickness_mm": 6.1,
    "eye_diameter_mm": 4.2,
    "rear_eye_to_motor_mm": 9.2,
    "motor_length_mm": 41.7,
    "motor_width_in_motion_plane_mm": 20.5,
    "motor_thickness_along_pin_mm": 15.0,
    "front_eye_to_tube_mm": 5.6,
}


def _candidate_pitches():
    closed = CANDIDATE["retracted_pitch_base_mm"] + CANDIDATE["stroke_mm"]
    return closed, closed + CANDIDATE["stroke_mm"]


@lru_cache(maxsize=1)
def actuator_registration():
    """以原底座内侧 52 mm 孔对和碳板中部孔对反推尾铰点高度。"""
    import pymupdf

    holder = trimesh.load(ROOT / "STL Files" / "Linear Actuator Holder.stl", force="mesh")
    section = holder.section(plane_origin=[0, -2, 0], plane_normal=[0, 1, 0])
    holes = []
    for loop in section.discrete:
        xz = loop[:, (0, 2)]
        if np.all(np.abs(np.ptp(xz, axis=0) - 3) < .03):
            holes.append((xz.min(0) + xz.max(0)) / 2)
    holes = np.array(sorted(holes, key=lambda p: p[1]))
    if holes.shape != (4, 2) or not np.allclose(holes[:, 0], 0, atol=.02):
        raise ValueError("原推杆底座安装孔发生变化")
    native_z = holes[1:3, 1]
    if abs(np.ptp(native_z) - 52) > .03:
        raise ValueError("原推杆底座内侧孔距不是预期的 52 mm")
    reference = pdf_registration()
    shoulder_centres = np.array(reference["pdf_pattern_centres_points"])
    mid = shoulder_centres.mean(0)
    scale = 42 / np.mean(np.array(reference["pdf_pattern_pitch_at_1to1_mm"])[:, 0]) * 25.4 / 72
    circles = []
    with pymupdf.open(ROOT / "STL Files" / "Frame Side Blueprint.pdf") as doc:
        for path in doc[0].get_drawings():
            r = path["rect"]
            if (len(path["items"]) == 4 and all(item[0] == "c" for item in path["items"])
                    and abs(r.width * 25.4 / 72 - 3) < .08
                    and abs(r.width - r.height) < .1):
                point = np.array([(r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2])
                if abs(point[0] - mid[0]) * scale < .1:
                    circles.append(point)
    pairs = [np.array(sorted(pair, key=lambda p: p[1]))
             for pair in itertools.combinations(circles, 2)
             if abs(abs(pair[1][1] - pair[0][1]) * scale - 52) < .05]
    if len(pairs) != 1:
        raise ValueError("未唯一识别出碳板中部的推杆底座 52 mm 孔对")
    pair = pairs[0]
    global_z = np.sort(SHOULDER_Z + (mid[1] - pair[:, 1]) * scale)
    recovered_z = float(np.mean(global_z - native_z))
    recovered_y = float((pair[:, 0].mean() - mid[0]) * scale)
    if abs(recovered_z - PIVOT_Z) > .1 or abs(recovered_y) > .05:
        raise ValueError("推杆底座反推基准发生变化，需要重新配准")
    return {
        "source": "STL Files/Frame Side Blueprint.pdf + STL Files/Linear Actuator Holder.stl",
        "native_inner_mount_z_mm": native_z.tolist(),
        "pdf_hole_centres_points": pair.tolist(),
        "pdf_hole_pitch_mm": float(np.ptp(pair[:, 1]) * scale),
        "recovered_pivot_z_mm": recovered_z,
        "recovered_longitudinal_y_mm": recovered_y,
        "design_pivot_z_mm": PIVOT_Z,
        "limitation": "原图没有尺寸标注；52 mm 孔对对应底座的判断为几何交叉核对，不是实机测量。",
    }


def add_actuator_mounts(lower):
    """耳座与下舱侧梁一体，底面为 Z=0，不额外增加打印件或密封壁通孔。"""
    import cadquery as cq

    for side in (-1, 1):
        for y in (-TAIL_GAP / 2, EAR_OUTER_Y):
            ear = (cq.Workplane("XZ", origin=(0, y, 0))
                   .moveTo(side * RAIL_INNER_X, 0)
                   .lineTo(side * (PIVOT_X + EAR_RADIUS), 0)
                   .lineTo(side * (PIVOT_X + EAR_RADIUS), PIVOT_Z)
                   .threePointArc((side * PIVOT_X, PIVOT_Z + EAR_RADIUS),
                                  (side * (PIVOT_X - EAR_RADIUS), PIVOT_Z))
                   .lineTo(side * RAIL_INNER_X, PIVOT_Z).close().extrude(EAR_THICKNESS))
            lower = lower.union(ear)
        bore = cq.Solid.makeCylinder(PIN_DIAMETER / 2, 2 * EAR_OUTER_Y + .2,
                                    cq.Vector(side * PIVOT_X, -EAR_OUTER_Y - .1, PIVOT_Z),
                                    cq.Vector(0, 1, 0))
        lower = lower.cut(cq.Workplane(obj=bore))
    return lower


def actuator_report():
    closed, opened = _candidate_pitches()
    return {
        "integral_tail_clevis": True,
        "separate_linear_actuator_holders_required": False,
        "pivot_centres_mm": [[side * PIVOT_X, 0, PIVOT_Z] for side in (-1, 1)],
        "pin_axis": "Y",
        "pin_hole_diameter_mm": PIN_DIAMETER,
        "tail_slot_width_mm": TAIL_GAP,
        "ear_thickness_mm": EAR_THICKNESS,
        "nominal_tail_side_clearance_total_mm": TAIL_GAP - CANDIDATE["rear_ear_thickness_mm"],
        "nominal_vertical_motor_to_rail_clearance_mm":
            PIVOT_X - CANDIDATE["motor_width_in_motion_plane_mm"] / 2 - RAIL_OUTER_X,
        "lateral_placement": f"X=±{PIVOT_X:g} mm 是新增设计值，向外避让 {CANDIDATE['motor_width_in_motion_plane_mm']:g} mm 电机壳；不是原机横向铰点复原。",
        "reference_registration": actuator_registration(),
        "candidate": {**CANDIDATE, "retracted_eye_pitch_mm": closed,
                      "extended_eye_pitch_mm": opened,
                      "previous_seller_reference_eye_pitch_mm": [85, 115],
                      "previous_seller_reference_is_verified_original": False},
        "hardware": {"bolts": "2 颗 M4×30 圆柱头螺栓，头径≤7 mm、头高≤4 mm",
                     "nuts": "2 个 M4 防松螺母，对边≤7 mm、高≤5 mm",
                     "washers": "耳座外侧各 0.5 mm 垫片，外径≤9 mm；内侧按实物配置薄垫片或轴套",
                     "assembly": "尾耳位于双耳中间，销轴沿 Y 插入；保留摆动，不得夹紧塑料耳座消除间隙。"},
        "mechanism_motion_verified": False,
        "limit": "仅交付尾耳接口。轮臂端仍使用原件；两端孔距与整机终点姿态尚未联动验证。",
    }


def _cylinder_y(radius, length, centre, sections=64):
    transform = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
    transform[:3, 3] = centre
    return trimesh.creation.cylinder(radius=radius, height=length, sections=sections, transform=transform)


def _box(extents, centre):
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(centre)
    return mesh


@lru_cache(maxsize=2)
def _candidate_envelope(pitch):
    """由尺寸图建立保守外形包络，不冒充厂家精确三维实体。"""
    start = CANDIDATE["rear_eye_to_motor_mm"]
    end = start + CANDIDATE["motor_length_mm"]
    tube_end = pitch - CANDIDATE["front_eye_to_tube_mm"]
    shapes = [
        _cylinder_y(5, CANDIDATE["rear_ear_thickness_mm"], [0, 0, 0]),
        _box([start, CANDIDATE["rear_ear_thickness_mm"], 10], [start / 2, 0, 0]),
        _box([end - start, CANDIDATE["motor_thickness_along_pin_mm"],
              CANDIDATE["motor_width_in_motion_plane_mm"]], [(start + end) / 2, 0, 0]),
        _box([tube_end - end, 12, 20], [(end + tube_end) / 2, 0, 0]),
        _box([pitch - tube_end, CANDIDATE["front_ear_thickness_mm"], 9], [(tube_end + pitch) / 2, 0, 0]),
        _cylinder_y(4.5, CANDIDATE["front_ear_thickness_mm"], [pitch, 0, 0]),
    ]
    combined = trimesh.boolean.union(shapes, engine="manifold")
    return trimesh.boolean.difference(
        [combined, _cylinder_y(CANDIDATE["eye_diameter_mm"] / 2, 10, [0, 0, 0]),
         _cylinder_y(CANDIDATE["eye_diameter_mm"] / 2, 8, [pitch, 0, 0])],
        engine="manifold")


def verify_actuator_fit(lower, upper):
    expected = np.array([[-PIVOT_X, PIVOT_Z], [PIVOT_X, PIVOT_Z]])
    for y in (-TAIL_GAP / 2 - EAR_THICKNESS / 2, TAIL_GAP / 2 + EAR_THICKNESS / 2):
        section = lower.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
        centres = []
        for loop in section.discrete:
            xz = loop[:, (0, 2)]
            if np.all(np.abs(np.ptp(xz, axis=0) - PIN_DIAMETER) < .03):
                centres.append((xz.min(0) + xz.max(0)) / 2)
        centres = np.array(sorted(centres, key=lambda p: p[0]))
        if centres.shape != (2, 2) or not np.allclose(centres, expected, atol=.02):
            raise ValueError(f"推杆尾耳孔轴线不匹配：{centres}")
    maximum_hardware = 0.0
    maximum_sweep = 0.0
    samples = 0
    pitches = _candidate_pitches()
    bearing = EAR_OUTER_Y + .5
    for side in (-1, 1):
        pivot = [side * PIVOT_X, 0, PIVOT_Z]
        shaft = _cylinder_y(2, 30, [pivot[0], 15 - bearing, pivot[2]])
        head = _cylinder_y(3.5, 4, [pivot[0], -bearing - 2, pivot[2]])
        nut = _cylinder_y(7 / np.sqrt(3), 5, [pivot[0], bearing + 2.5, pivot[2]], sections=6)
        washers = [_cylinder_y(4.5, .5, [pivot[0], side_y * (EAR_OUTER_Y + .25), pivot[2]])
                   for side_y in (-1, 1)]
        for hardware in (shaft, head, nut, *washers):
            for target in (lower, upper):
                maximum_hardware = max(maximum_hardware, mesh_interference_volume(hardware, target))
        for pitch in pitches:
            for angle in range(0, 91, 5):
                radians = np.radians(angle)
                c, s = np.cos(radians), np.sin(radians)
                transform = np.eye(4)
                transform[:3, :3] = [[side * c, 0, -side * s], [0, 1, 0], [s, 0, c]]
                transform[:3, 3] = pivot
                envelope = _candidate_envelope(pitch).copy()
                envelope.apply_transform(transform)
                for target in (lower, upper):
                    maximum_sweep = max(maximum_sweep, mesh_interference_volume(envelope, target))
                samples += 1
    if maximum_hardware > .01 or maximum_sweep > .01:
        raise ValueError(f"推杆接口存在干涉：紧固件 {maximum_hardware}，局部包络 {maximum_sweep} mm³")
    return {"pin_axes_match": True, "maximum_hardware_interference_mm3": maximum_hardware,
            "maximum_candidate_envelope_interference_mm3": maximum_sweep,
            "candidate_pose_count": samples, "scanned_eye_pitch_mm": list(pitches),
            "outward_upward_scan_angle_deg": [0, 90], "scan_step_deg": 5,
            "scope": "两侧、两个长度、每 5° 的向外向上局部包络采样。未装配轮臂和齿轮，不是机构全行程或连续碰撞认证。",
            "mechanism_motion_verified": False}


def render_actuator_connection():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Rectangle

    configure_chinese_font()
    closed, opened = _candidate_pitches()
    fig, (front, detail) = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [1.5, 1]})
    front.add_patch(Rectangle((-82.4, 0), 164.8, 78, fc="#e4eef0", ec="#31566a"))
    for side in (-1, 1):
        front.add_patch(Rectangle((side * 93.6 - 3, 0), 6, 78, fc="#bed4db", ec="#31566a"))
        arc = [(side * (PIVOT_X + EAR_RADIUS * np.cos(a)), PIVOT_Z + EAR_RADIUS * np.sin(a))
               for a in np.linspace(0, np.pi, 40)]
        points = [(side * RAIL_INNER_X, 0), (side * (PIVOT_X + EAR_RADIUS), 0),
                  *arc, (side * RAIL_INNER_X, PIVOT_Z)]
        front.add_patch(Polygon(points, fc="#dfa65a", ec="#805b2d"))
        front.plot(side * PIVOT_X, PIVOT_Z, "o", color="#a43d32", ms=5)
    front.text(0, 42, "承力下舱\n耳座与侧梁一体打印\n不另装原推杆底座", ha="center", va="center", fontsize=12)
    front.annotate("", (-PIVOT_X, -8), (PIVOT_X, -8), arrowprops={"arrowstyle": "<->"})
    front.text(0, -14, f"左右尾铰点距 {2 * PIVOT_X:g} mm；孔轴沿 Y", ha="center", fontsize=10)
    front.text(0, 86, f"铰点 Z={PIVOT_Z:g} mm；通孔 Ø{PIN_DIAMETER:g} mm", ha="center", fontsize=11)
    front.set(xlim=(-130, 130), ylim=(-25, 95), xlabel="装配 X 轴 / mm", ylabel="Z 轴 / mm",
              title="前视投影：一体式推杆尾耳接口")
    front.set_aspect("equal"); front.grid(alpha=.12)
    for y in (-EAR_OUTER_Y, TAIL_GAP / 2):
        detail.add_patch(Rectangle((y, 0), EAR_THICKNESS, PIVOT_Z + EAR_RADIUS,
                                   fc="#dfa65a", ec="#805b2d"))
    tail_thickness = CANDIDATE["rear_ear_thickness_mm"]
    detail.add_patch(Rectangle((-tail_thickness / 2, PIVOT_Z - 5), tail_thickness, 10,
                               fc="#b9c0c6", ec="#49545e"))
    detail.plot([-15, 19], [PIVOT_Z, PIVOT_Z], color="#a43d32", lw=2)
    detail.annotate("", (-TAIL_GAP / 2, 22), (TAIL_GAP / 2, 22), arrowprops={"arrowstyle": "<->"})
    detail.text(0, 24, f"耳槽净宽 {TAIL_GAP:g} mm", ha="center", fontsize=11)
    detail.text(0, -4, f"尾耳厚 {CANDIDATE['rear_ear_thickness_mm']:g} mm；名义总间隙 {TAIL_GAP - CANDIDATE['rear_ear_thickness_mm']:.1f} mm\n每片打印耳厚 {EAR_THICKNESS:g} mm\n左右各用 1 颗 M4×30 螺栓及防松螺母",
                ha="center", va="top", fontsize=10)
    detail.set(xlim=(-21, 23), ylim=(-15, 30), xlabel="局部 Y 轴 / mm", ylabel="Z 轴 / mm",
               title="单侧耳座侧视：尾耳置于槽内")
    detail.set_aspect("equal"); detail.grid(alpha=.12)
    fig.text(.5, .035, f"候选推杆按 {CANDIDATE['stroke_mm']:g} mm 行程：缩回孔距 {closed:g} mm、伸出 {opened:g} mm；不是已验证的变形终点。\n外侧铰点位置为新设计值；0–90° 局部包络采样不代表包含轮臂、齿轮与线束的完整运动验证。",
             ha="center", va="bottom", fontsize=10, color="#a43d32")
    fig.tight_layout(rect=(0, .14, 1, .93))
    fig.savefig(OUT / "Actuator_Connection.png", dpi=170)
    plt.close(fig)
