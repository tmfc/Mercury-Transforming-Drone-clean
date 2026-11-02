"""实测平面板件布局、矮定位挡及物料清单覆盖情况。

板件轮廓不等于已装配元件与线束的包络。位置以装配坐标系毫米值明确给定，
重新生成时不需要求解装箱问题。
"""
from pathlib import Path
import csv
import itertools
import json
import math
import re

import numpy as np
from shapely.affinity import rotate, translate
from shapely.geometry import LineString, Polygon, box
from shapely.ops import polygonize, unary_union

from chassis_interfaces import (
    INNER_HOLE_Y, MOUNT_Z, RAIL_END, RAIL_INNER_X, SHOULDER_SPACING, connection_report,
)
from localization import configure_chinese_font
from actuator_interfaces import (
    EAR_OUTER_Y, EAR_RADIUS, EAR_THICKNESS, PIVOT_X, PIVOT_Z, TAIL_GAP, actuator_report,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
PI_DRAWING = "https://pip.raspberrypi.com/documents/RP-008347-DS-1-raspberry-pi-5-mechanical-drawing.pdf"
CUBE_DRAWING = "https://docs.cubepilot.org/carrier-boards/standard-carrier-board-footprint-and-dimensions"
RX_SPEC = "https://www.radiolink.com/en/r8xm_specifications"
BATTERY_SPEC = "https://us.ovonicshop.com/products/ovonic-3s-50c-11-1v-2200mah-lipo-battery-pack-with-deans-t-plug-for-rc-airplane-helicopter-quadcopter-rc-car-truck-boat"

# 先绕原始轮廓原点旋转，再平移到所给左下角位置。
PLACEMENTS = {
    "RX": (180, 55.5, -95.5),
    "MAIN2": (90, -77.5, -95.5),
    "ACT1": (270, 5.621, -74.5),
    "PI": (270, -77.5, -43.62097),
    "MAIN1": (270, -16.49777, 17.48619),
    "CUBE": (0, -77.5, 48.21),
}
LABELS = {"PI": "树莓派 5", "CUBE": "Cube 飞控及标准载板", "RX": "Radiolink R8XM 接收机", "MAIN1": "主模块板外形 A", "MAIN2": "空白外形占位（非功能板）", "ACT1": "执行控制电路板"}
# （X 中心、Y 中心、X 长度、Y 长度）；均厚 2 mm、高 6 mm。
# 分段定位挡而非封闭隔舱，保留走线通道。
DIVIDERS = [
    (-51.5, -45.62097, 43, 2),
    (-19.5, -21.5, 2, 19),
    (-19.5, 12, 2, 24),
    (-49, 44.5, 42, 2),
    (27.5, 15.5, 35, 2),
    (3.621, -61, 2, 18),
    (66, -76.5, 16, 2),
    (1, 46.1, 22, 2),
]
DIVIDER_HEIGHT = 6.0


def gerber_outlines(path):
    """读取仓库中的 G01 直线轮廓，包括逐边使用 D02 移动的情况。"""
    text = path.read_text()
    if "%FSLAX45Y45*%" not in text or "%MOMM*%" not in text:
        raise ValueError(f"不支持的 Gerber 坐标格式：{path}")
    if re.search(r"G0[23](?:\*|X|Y)", text):
        raise ValueError(f"圆弧轮廓需要支持 Gerber 圆弧的读取器：{path}")
    segments, previous = [], None
    for x, y, operation in re.findall(r"X(-?\d+)Y(-?\d+)D0([12])", text):
        point = (int(x) / 100000, int(y) / 100000)
        if operation == "1":
            if previous is None:
                raise ValueError(f"轮廓绘制前缺少初始移动：{path}")
            segments.append(LineString([previous, point]))
        previous = point
    polygons = list(polygonize(unary_union(segments)))
    if not polygons or not unary_union(segments).difference(
            unary_union([p.boundary for p in polygons])).is_empty:
        raise ValueError(f"板件轮廓未闭合或存在歧义：{path}")
    # 固定身份：面积较大的轮廓为 A，不能依赖图遍历的任意顺序。
    return sorted(polygons, key=lambda p: -p.area)


def footprints():
    boards = {}
    for module, prefix, expected in [("MainModule", "MAIN", 2),
                                     ("ActuationModule", "ACT", 1)]:
        paths = sorted((ROOT / "PCB Files").glob(f"*{module}*/Gerber_BoardOutlineLayer.GKO"))
        if len(paths) != 1:
            raise ValueError(f"应有一个 {module} 外形文件，实际为：{paths}")
        polys = gerber_outlines(paths[0])
        if len(polys) != expected:
            raise ValueError(f"板件轮廓数量不符合预期：{paths[0]}")
        for i, poly in enumerate(polys, 1):
            x, y, _, _ = poly.bounds
            boards[f"{prefix}{i}"] = (translate(poly, -x, -y), str(paths[0].relative_to(ROOT)))
    boards.update(PI=(box(0, 0, 85, 56), PI_DRAWING),
                  CUBE=(box(0, 0, 94.46, 44.29), CUBE_DRAWING),
                  RX=(box(0, 0, 22, 17), RX_SPEC))
    return boards


def placed_boards():
    result = {}
    for name, (poly, source) in footprints().items():
        angle, x, y = PLACEMENTS[name]
        rotated = rotate(poly, angle, origin=(0, 0))
        min_x, min_y, _, _ = rotated.bounds
        result[name] = {"shape": translate(rotated, x - min_x, y - min_y),
                        "source": source, "original_shape": poly}
    return result


def pcb_mounts():
    # 树莓派安装孔并非相对 85 mm 板边居中：两端位置为 3.5 和 61.5 mm。
    local = {"PI": [(x, y) for x in (3.5, 61.5) for y in (3.5, 52.5)],
             "CUBE": [(47.23 + x, 22.145 + y) for x in (-42.5, 42.5)
                      for y in (-17.2, 17.2)]}
    all_boards, result = footprints(), []
    for name, points in local.items():
        angle, x, y = PLACEMENTS[name]
        rotated = rotate(all_boards[name][0], angle, origin=(0, 0))
        min_x, min_y, _, _ = rotated.bounds
        c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        result.extend((c * px - s * py + x - min_x,
                       s * px + c * py + y - min_y) for px, py in points)
    return result


def divider_shapes():
    return [box(x - w / 2, y - length / 2, x + w / 2, y + length / 2)
            for x, y, w, length in DIVIDERS]


def check_layout():
    boards = placed_boards()
    # 在实际圆角舱腔及后壁接口凸台以内取保守矩形区域。
    allowed = box(-77.5, -95.5, 77.5, 92.5)
    gaps = []
    for name, board in boards.items():
        if not allowed.buffer(1e-7).covers(board["shape"]):
            raise ValueError(f"{name}：板件轮廓超出允许舱腔")
    for (a, first), (b, second) in itertools.combinations(boards.items(), 2):
        gap = first["shape"].distance(second["shape"])
        if gap < 3.98:
            raise ValueError(f"板边净距小于 3.98 mm：{a}/{b}：{gap}")
        gaps.append(gap)
    stop_gaps = []
    for i, stop in enumerate(divider_shapes(), 1):
        for name, board in boards.items():
            gap = stop.distance(board["shape"])
            if gap < 0.98:
                raise ValueError(f"定位挡 {i} 距 {name} 过近：{gap}")
            stop_gaps.append(gap)
    return {"all_bom_components_fit": None,
            "conclusion": "已知平面轮廓可排入；装配后高度及整套物料尚未验证能否容纳。",
            "minimum_board_edge_gap_mm": min(gaps),
            "minimum_board_to_stop_gap_mm": min(stop_gaps),
            "divider_height_above_floor_mm": DIVIDER_HEIGHT,
            "divider_count": len(DIVIDERS),
            "board_outlines": [{"id": name, "label": LABELS[name],
                                "unrotated_size_xy_mm": list(np.ptp(np.array(b["original_shape"].exterior.coords), axis=0)),
                                "placed_bounds_xy_mm": list(b["shape"].bounds),
                                "height_mm": 31.42 if name == "CUBE" else None,
                                "height_note": "仅为标准载板参考，需核对实际 Orange+ 套装。" if name == "CUBE" else "尚无已装配元件的可靠高度。",
                                "source": b["source"]} for name, b in boards.items()]}


def bom_coverage():
    known = {"Raspberry Pi 5": ["PI"], "Radiolink R8XM": ["RX"],
             "Cube + Flight Controller": ["CUBE"],
             "Custom PCBS": ["MAIN1", "MAIN2", "ACT1"]}
    external = {"TOF Camera", "USB Webcam", "Optical Flow MTF-01", "Thermal Camera"}
    mechanical = {"120N Linear Actuator 1.2\"", "8 inch propellers", "BLDC Motor (A2812 2812 900KV)",
                  "CF  30 cm x 30 cm (for frame)", "BLDC Motor 140kv (for driving)"}
    result = []
    with (ROOT / "Mercury BOM.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            name = row["Hardware"]
            if name in known:
                status, note = "outline_only", "图中仅展示板件轮廓；装配后的元件及接插件尚未验证。"
            elif name in external:
                status, note = "external_optical_interface", "需要朝向外部的有效光路及独立密封安装接口；该器件并未从整机需求中删除。"
            elif name in mechanical or name.startswith("Screws"):
                status, note = "outside_electronics_cavity", "机架、执行器、动力或装配五金，位于电子舱之外。"
            else:
                status, note = "not_allocated", "尚无已验证的装配包络及位置，不能认定整套物料均可容纳。"
            if name == "Lipo Battery (3S 2200mah)":
                note = "共 2 块；厂家同系列参考尺寸为 105 × 33 × 14 mm，公差 ±3 mm，不含引线。需核对实际电池及装配包络；本模型未提供电池约束结构。" + BATTERY_SPEC
            elif name == "Custom PCBS":
                note = "主模块 Gerber 中有两条独立外形，但较小的 MAIN2 没有铜线、丝印或焊盘，仅保留外形占位；执行模块有一条外形。不能据此确认原清单的三块功能板已全部识别；不假定降压、ESP32 或 DRV 模块已包含在板上。"
            elif name == "Optical Flow MTF-01":
                note += "；原清单链接指向 Ewing H7 飞控，并非 MTF-01 尺寸图。"
            elif name == "120N Linear Actuator 1.2\"":
                note = "原清单为 2 个推杆。新版下舱一体尾耳接口按用户淘宝图的 8 mm 尾耳与 Ø4.2 mm 孔设计，局部包络采用 30 mm 行程、87.5/117.5 mm 孔距；不代表原采购链接规格、整机运动或电气载荷已核实。"
            elif name == "CF  30 cm x 30 cm (for frame)":
                note = "本无碳板改型不使用碳纤维侧板；保留原清单和原图作为尺寸输入。"
            result.append({"item": name, "name_zh": row["名称（中文）"], "quantity": int(row["Units"]),
                           "status": status, "layout_ids": known.get(name, []),
                           "note": note, "bom_url": row["Link"]})
    return result




def render_diagrams():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as PatchPolygon, Rectangle, FancyBboxPatch
    configure_chinese_font()

    boards = placed_boards()
    colors = dict(zip(PLACEMENTS, ["#8b62b2", "#398caa", "#d58538", "#539c5a", "#be705f", "#5c7eb0"]))
    fig, (ax, legend) = plt.subplots(1, 2, figsize=(13, 9), gridspec_kw={"width_ratios": [1.15, 1]})
    for x in (-96.6, 90.6):
        ax.add_patch(Rectangle((x, -RAIL_END), 6, 2 * RAIL_END,
                               fc="#d9e1e6", ec="#536775"))
    for side in (-1, 1):
        x_min = RAIL_INNER_X if side == 1 else -PIVOT_X - EAR_RADIUS
        for y in (-EAR_OUTER_Y, TAIL_GAP / 2):
            ax.add_patch(Rectangle((x_min, y), PIVOT_X + EAR_RADIUS - RAIL_INNER_X,
                                   EAR_THICKNESS, fc="#dfa65a", ec="#805b2d"))
    ax.add_patch(FancyBboxPatch((-82.4, -100.6), 164.8, 201.2,
                              boxstyle="round,pad=0,rounding_size=8", fc="#ecf0f2", ec="#263541", lw=2))
    ax.add_patch(FancyBboxPatch((-79.4, -97.6), 158.8, 195.2,
                              boxstyle="round,pad=0,rounding_size=5", fc="white", ec="#81909c"))
    for name, board in boards.items():
        poly = board["shape"]
        ax.add_patch(PatchPolygon(list(poly.exterior.coords), fc=colors[name], ec="#253442", alpha=.65))
        p = poly.representative_point()
        ax.text(p.x, p.y, name, ha="center", va="center", weight="bold", fontsize=11)
    for x, y in pcb_mounts():
        ax.plot(x, y, "o", ms=3, color="#263541")
    for stop in divider_shapes():
        ax.add_patch(PatchPolygon(list(stop.exterior.coords), fc="#34414d", ec="none"))
    ax.set(xlim=(-126, 126), ylim=(118, -118), xlabel="X 轴 / mm", ylabel="Y 轴 / mm",
           title="已知板件轮廓布局（俯视图）\n前方为 -Y；后壁格兰头接口位于 +Y")
    ax.set_aspect("equal"); ax.grid(alpha=.15)
    legend.axis("off")
    legend.text(0, .98, "平面排得下，不等于整套器件装得下", fontsize=16, weight="bold", color="#a33a2e")
    legend.text(0, .93, "依据真实 Gerber 外形及厂家板件尺寸绘制。\n未将元件高度、插头、散热器和引线计入装配包络。", fontsize=10, va="top")
    for i, name in enumerate(PLACEMENTS):
        y = .82 - i * .085
        original = boards[name]["original_shape"]
        _, _, w, h = original.bounds
        legend.add_patch(Rectangle((0, y-.015), .035, .03, fc=colors[name]))
        legend.text(.055, y, f"{name}：{LABELS[name]}\n{w:.2f} × {h:.2f} mm；依据见 Layout.json", fontsize=10, va="center")
    legend.text(0, .26, "深色为矮挡：厚 2 mm，高出舱底 6 mm。\n分段留出走线缺口；矮挡不能代替紧固件。\n橙色为舱外一体式推杆尾耳座，孔轴沿 Y。\n树莓派孔距 58 × 49 mm（已旋转）；Cube 为 85 × 34.4 mm。\n图中飞控位置并非已验证的整机重心位置。", fontsize=10, va="top")
    legend.text(0, .13, "尚未分配位置，需核对装配尺寸：\n2 块电池、3 个降压模块、2 个 DRV8871、ESP32-S3、\n四合一电调、2 个行驶电调、通信模块、2 个 IMU 及线束。\n摄像头和光流需要朝外的光学接口。\n不假定这些模块能够放进电路板凹口。", fontsize=10, va="top", color="#a33a2e")
    fig.tight_layout(); fig.savefig(OUT / "Electronics_Layout.png", dpi=170); plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.add_patch(Rectangle((-RAIL_END, 0), 2 * RAIL_END, 78,
                           fc="#d9e7eb", ec="#31566a", lw=2))
    ax.add_patch(Rectangle((-100.6, 4), 201.2, 74,
                           fc="#edf3f5", ec="#81949d"))
    ax.text(0, 39, "一体式承力下舱\n带开窗的箱形侧梁\n不使用碳纤维侧板", ha="center", va="center", fontsize=12)
    for y in (-EAR_OUTER_Y, TAIL_GAP / 2):
        ax.add_patch(Rectangle((y, 0), EAR_THICKNESS, PIVOT_Z + EAR_RADIUS,
                               fc="#dfa65a", ec="#805b2d"))
    ax.plot([-EAR_OUTER_Y, EAR_OUTER_Y], [PIVOT_Z, PIVOT_Z], color="#a43d32", lw=2)
    ax.text(0, 20, "推杆尾耳座（左右重合投影）", ha="center", fontsize=9)
    for end, name in ((-1, "Front"), (1, "Rear")):
        center = end * SHOULDER_SPACING / 2
        ax.add_patch(Rectangle((center - 24.5, 12.5), 49, 65,
                               fc="#e6cfa7", ec="#755a32", alpha=.7))
        ax.text(center, 84, f"{'前' if name == 'Front' else '后'}肩部\n安装座", ha="center", fontsize=10)
        for z in MOUNT_Z:
            ax.plot(end * INNER_HOLE_Y, z, "o", ms=8, color="#b64d35")
        ax.axvline(center, ymin=.07, ymax=.9, color="#9e8460", ls=":", lw=1)
    ax.annotate("", (-SHOULDER_SPACING/2, 111), (SHOULDER_SPACING/2, 111),
                arrowprops={"arrowstyle":"<->", "color":"#31566a"})
    ax.text(0, 114, "按 PDF 反推的前后肩座中心距：252.2 mm", ha="center", fontsize=11)
    ax.annotate("", (-INNER_HOLE_Y, 97), (INNER_HOLE_Y, 97),
                arrowprops={"arrowstyle":"<->", "color":"#b64d35"})
    ax.text(0, 99, "采用内侧孔排连接，间距 210.2 mm", ha="center", color="#b64d35", fontsize=10)
    ax.text(0, -13, "使用配套 Direct 肩座，先从侧面装入 M3 螺母，再对接下舱。\n红色孔在另一侧对称设置，共用 8 颗 M3×25 螺栓及螺母；外侧孔排不用。\n仅完成静态几何配合检查，未认证承载、疲劳或完整运动行程。",
            ha="center", va="top", fontsize=10)
    ax.set(xlim=(-165, 165), ylim=(-38, 127), xlabel="装配 Y 轴 / mm", ylabel="Z 轴 / mm",
           title="肩座与承力下舱连接示意（含推杆接口侧视投影）")
    ax.set_aspect("equal"); ax.grid(alpha=.1)
    fig.tight_layout(); fig.savefig(OUT / "ShoulderMount_Connection.png", dpi=170); plt.close(fig)


def generate_layout():
    report = check_layout()
    report["bom_coverage"] = bom_coverage()
    report["connection"] = connection_report()
    report["actuator"] = actuator_report()
    render_diagrams()
    (OUT / "Layout.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    result = generate_layout()
    print(json.dumps({k: v for k, v in result.items() if k not in ("bom_coverage", "connection")}, ensure_ascii=False, indent=2))
