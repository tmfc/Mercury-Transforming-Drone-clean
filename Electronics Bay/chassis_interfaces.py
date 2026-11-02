"""从原始矢量 PDF 恢复肩座配准位置，不依赖 STL 原点。

装配尺寸均以毫米计。PDF 反推间距仅为设计参考，
不是带尺寸标注的制造图，也不是实物测量值。
"""
from functools import lru_cache
from pathlib import Path
import itertools

import numpy as np
import trimesh

from localization import configure_chinese_font

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
SHOULDER_SPACING = 252.2
SHOULDER_Z = 45.0
INNER_HOLE_Y = SHOULDER_SPACING / 2 - 21.0
MOUNT_Z = (SHOULDER_Z - 25.5, SHOULDER_Z + 25.5)
RAIL_END = INNER_HOLE_Y + 3.0
RAIL_INNER_X = 90.6
RAIL_OUTER_X = 96.6
PAD_OUTER_X = 100.6


@lru_cache(maxsize=1)
def pdf_registration():
    import pymupdf

    with pymupdf.open(ROOT / "STL Files" / "Frame Side Blueprint.pdf") as doc:
        page = doc[0]
        circles = []
        for path in page.get_drawings():
            r = path["rect"]
            if (len(path["items"]) == 4 and all(item[0] == "c" for item in path["items"])
                    and r.y1 < 580 and abs(r.width * 25.4 / 72 - 3.5) < .08
                    and abs(r.height * 25.4 / 72 - 3.5) < .08):
                circles.append(np.array([(r.x0+r.x1)/2, (r.y0+r.y1)/2]))
        patterns = []
        for indices in itertools.combinations(range(len(circles)), 4):
            points = np.array([circles[i] for i in indices])
            if not np.allclose(np.ptp(points, axis=0) * 25.4 / 72, [42, 51], atol=.04):
                continue
            # 必须是矩形孔阵列，不能只是四个包围框尺寸相符的无关圆孔。
            if any(min(abs(pt[k]-points[:, k].min()), abs(pt[k]-points[:, k].max())) > .08
                   for pt in points for k in (0, 1)):
                continue
            patterns.append(points)
        patterns.sort(key=lambda p: p[:, 0].mean())
        if len(patterns) != 2:
            raise ValueError("PDF 应有两组与 STL 的 42 × 51 mm 孔距匹配的肩座孔阵列")
        centers = [p.mean(axis=0) for p in patterns]
        scale_x = 42 / np.mean([np.ptp(p[:, 0]) for p in patterns])
        distance = float((centers[1][0] - centers[0][0]) * scale_x)
        if abs(distance - SHOULDER_SPACING) > .05:
            raise ValueError(f"PDF 配准结果发生变化，反推间距为：{distance}")
        return {"source": "STL Files/Frame Side Blueprint.pdf", "page": 1,
                "method": "读取矢量圆孔中心，并以肩座 STL 测得的 42 mm 孔距标定。",
                "pdf_pattern_centres_points": [c.tolist() for c in centers],
                "pdf_pattern_pitch_at_1to1_mm": [(np.ptp(p, axis=0) * 25.4 / 72).tolist() for p in patterns],
                "pdf_calibrated_spacing_mm": distance,
                "design_shoulder_spacing_mm": SHOULDER_SPACING,
                "design_inner_row_spacing_mm": 2 * INNER_HOLE_Y,
                "limitation": "PDF 未明确标注肩座间距；此值为图纸反推的设计参考，不是已认证的实机测量。"}


@lru_cache(maxsize=1)
def measured_shoulders():
    result = []
    for name in ("Front", "Rear"):
        mesh = trimesh.load(ROOT / "STL Files" / f"ShoulderMount - {name}.stl", force="mesh")
        sides = []
        for x in (-89, 89):
            section = mesh.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
            centers = []
            for loop in section.discrete:
                yz = loop[:, 1:]
                if np.all(np.abs(np.ptp(yz, axis=0) - 3) < .03):
                    centers.append((yz.min(0) + yz.max(0)) / 2)
            centers = np.array(sorted(centers, key=lambda p: (p[0], p[1])))
            if centers.shape != (4, 2) or not np.allclose(np.ptp(centers, axis=0), (42, 51), atol=.03):
                raise ValueError(f"{name} 肩座侧面孔阵列不符合预期")
            sides.append({"x_section_mm": x, "original_yz_centres_mm": centers.tolist()})
        result.append({"part": f"ShoulderMount - {name}.stl", "side_patterns": sides})
    return result


@lru_cache(maxsize=1)
def aligned_shoulders():
    result = {}
    for name, target_y, measured in zip(("Front", "Rear"),
                                      (-SHOULDER_SPACING / 2, SHOULDER_SPACING / 2),
                                      measured_shoulders()):
        centers = np.array(measured["side_patterns"][0]["original_yz_centres_mm"])
        original_y, original_z = np.round(centers.mean(axis=0), 1)
        mesh = trimesh.load(ROOT / "STL Files" / measured["part"], force="mesh")
        mesh.apply_translation([0, target_y - original_y, SHOULDER_Z - original_z])
        # 原始孔背筋会与普通螺母干涉，需增加侧向送入的六角螺母槽，
        # 不能假设螺母可以直接压在原筋板上拧紧。
        end = -1 if name == "Front" else 1
        cutters = []
        rotation = (trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]) @
                    trimesh.transformations.rotation_matrix(np.pi / 6, [0, 0, 1]))
        for side in (-1, 1):
            for z in MOUNT_Z:
                transform = rotation.copy()
                transform[:3, 3] = [side * 82.3, end * INNER_HOLE_Y, z]
                cutters.append(trimesh.creation.cylinder(
                    radius=5.8 / np.sqrt(3), height=4.2, sections=6, transform=transform))
                slot = trimesh.creation.box(extents=[4.2, 4.5, 5.8])
                slot.apply_translation([side * 82.3, end * (INNER_HOLE_Y - 2.25), z])
                cutters.append(slot)
                transform = rotation.copy()
                transform[:3, 3] = [side * 83.0, end * INNER_HOLE_Y, z]
                cutters.append(trimesh.creation.cylinder(
                    radius=1.6, height=15, sections=48, transform=transform))
        mesh = trimesh.boolean.difference([mesh, *cutters], engine="manifold")
        if not mesh.is_volume or len(mesh.split()) != 1:
            raise ValueError(f"{name}：螺母槽导致肩座实体断开")
        result[name] = mesh
    return result


def connection_report():
    return {"direct_shoulder_mount": True, "carbon_plates_required": False,
            "load_path": "前后肩座内侧孔排 → 一体式外置连接耳与箱形侧梁 → 承力下舱。",
            "pdf_registration": pdf_registration(),
            "shoulder_center_z_mm": SHOULDER_Z,
            "used_bolts": 8, "used_hole_rows_y_mm": [-INNER_HOLE_Y, INNER_HOLE_Y],
            "used_hole_levels_z_mm": list(MOUNT_Z),
            "printed_hole_diameter_mm": 3.2,
            "nominal_side_mating_gap_mm": RAIL_INNER_X - 90.4,
            "hole_selection": "每个肩座每侧采用内排两孔，外排孔不使用。应使用生成的 Direct 改版肩座，不能混用原始输入 STL。",
            "shoulder_modification": {"nut_pocket_across_flats_mm": 5.8,
                                      "nut_pocket_depth_mm": 4.2,
                                      "nut_max_across_flats_mm": 5.5,
                                      "nut_max_height_mm": 4,
                                      "side_feed": "开口朝电子舱一侧；对接下舱前先装入螺母。"},
            "strength_status": "仅验证几何；未进行承载、疲劳、冲击或整套机构全行程验证。",
            "measurements": measured_shoulders()}


def export_registered_assembly(lower, upper):
    """导出在统一坐标系中配准的可打印壳体与改版肩座网格装配。"""
    scene = trimesh.Scene()
    for name, mesh in {"Lower": lower, "Upper": upper, **aligned_shoulders()}.items():
        scene.add_geometry(mesh, node_name=name, geom_name=name)
    path = OUT / "Electronics_Bay_With_Shoulders.3mf"
    scene.export(path)
    restored = trimesh.load(path, force="scene")
    if len(restored.geometry) != 4 or not np.allclose(restored.bounds, scene.bounds, atol=.001):
        raise ValueError("已配准的 3MF 装配导出后重新读取校验失败")
    return scene


def export_print_shoulders():
    reports = []
    for name, mesh in aligned_shoulders().items():
        printable = mesh.copy()
        printable.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 4, [0, 0, 1]))
        center = (printable.bounds[0] + printable.bounds[1]) / 2
        printable.apply_translation([-center[0], -center[1], -printable.bounds[0, 2]])
        if np.any(printable.extents[:2] + 10 > 256):
            raise ValueError(f"{name}：旋转后的肩座加上 5 mm 裙边，超出 256 mm 打印平台")
        path = OUT / f"ShoulderMount_{name}_Direct.stl"
        printable.export(path)
        restored = trimesh.load(path, force="mesh")
        if not restored.is_volume or len(restored.split()) != 1:
            raise ValueError(f"{name}：导出的改版肩座实体无效")
        reports.append({"file": path.name, "size_mm": restored.extents.tolist(),
                        "watertight": bool(restored.is_watertight), "connected_solids": 1})
    return reports


def mesh_interference_volume(first, second):
    collision = trimesh.boolean.intersection([first, second], engine="manifold")
    triangles = collision.triangles
    return abs(float(np.einsum("ij,ij->i", triangles[:, 0],
                              np.cross(triangles[:, 1], triangles[:, 2])).sum()) / 6)


def verify_shoulder_fit(lower, upper):
    report = {}
    expected = np.array([(y, z) for y in (-INNER_HOLE_Y, INNER_HOLE_Y) for z in MOUNT_Z])
    for side in (-1, 1):
        section = lower.section(plane_origin=[side * 95.5, 0, 0], plane_normal=[1, 0, 0])
        centers = []
        for loop in section.discrete:
            yz = loop[:, 1:]
            if np.all(np.abs(np.ptp(yz, axis=0) - 3.2) < .03):
                centers.append((yz.min(0) + yz.max(0)) / 2)
        centers = np.array(sorted(centers, key=lambda p: (p[0], p[1])))
        if centers.shape != (4, 2) or not np.allclose(centers, expected, atol=.02):
            raise ValueError(f"打印件直接连接孔轴线发生变化：{centers}")
    for name, shoulder in aligned_shoulders().items():
        volumes = {part: mesh_interference_volume(mesh, shoulder)
                   for part, mesh in (("Lower", lower), ("Upper", upper))}
        if max(volumes.values()) > .01:
            raise ValueError(f"{name} 肩座与舱体干涉：{volumes}")
        end = -1 if name == "Front" else 1
        nut_max = 0.0
        bolt_max = 0.0
        for side in (-1, 1):
            for z in MOUNT_Z:
                transform = (trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]) @
                             trimesh.transformations.rotation_matrix(np.pi / 6, [0, 0, 1]))
                transform[:3, 3] = [side * 82.3, end * INNER_HOLE_Y, z]
                nut = trimesh.creation.cylinder(radius=5.5 / np.sqrt(3),
                                                height=4, sections=6, transform=transform)
                for target in (lower, shoulder):
                    nut_max = max(nut_max, mesh_interference_volume(nut, target))
                transform[:3, 3] = [side * 88.6, end * INNER_HOLE_Y, z]
                shaft = trimesh.creation.cylinder(radius=1.5, height=25,
                                                  sections=48, transform=transform)
                transform[:3, 3] = [side * 102.6, end * INNER_HOLE_Y, z]
                head = trimesh.creation.cylinder(radius=2.75, height=3,
                                                 sections=48, transform=transform)
                for target in (lower, shoulder):
                    bolt_max = max(bolt_max, mesh_interference_volume(shaft, target),
                                   mesh_interference_volume(head, target))
        if nut_max > .01:
            raise ValueError(f"{name}：指定 M3 螺母无法放入槽中：{nut_max}")
        volumes["nut_envelope"] = nut_max
        if bolt_max > .01:
            raise ValueError(f"{name}：M3×25 螺栓杆部或头部与打印件干涉：{bolt_max}")
        volumes["M3x25_bolt_envelope"] = bolt_max
        report[name] = volumes
    return report


def render_pdf_registration():
    import pymupdf
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    configure_chinese_font()

    registration = pdf_registration()
    with pymupdf.open(ROOT / "STL Files" / "Frame Side Blueprint.pdf") as doc:
        pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5))
        image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.imshow(image)
    centers = np.array(registration["pdf_pattern_centres_points"]) * 1.5
    for x, y in centers:
        ax.plot(x, y, "+", color="#bd392b", ms=20, mew=2)
        ax.plot([x, x], [y, 110], color="#bd392b", lw=1)
    ax.annotate("", (centers[0, 0], 115), (centers[1, 0], 115),
                arrowprops={"arrowstyle": "<->", "color": "#bd392b", "lw": 2})
    ax.text(centers[:, 0].mean(), 90, "反推肩座中心距：252.2 mm；内侧孔排间距：210.2 mm",
            ha="center", color="#bd392b", fontsize=11, bbox={"facecolor":"white", "edgecolor":"none"})
    ax.set_title("原始矢量图纸与 STL 的 42 × 51 mm 孔距交叉核对\n所示间距为反推设计参考，并非原图明确标注的制造尺寸")
    ax.axis("off"); fig.tight_layout()
    fig.savefig(OUT / "Frame_PDF_Registration.png", dpi=160)
    plt.close(fig)
