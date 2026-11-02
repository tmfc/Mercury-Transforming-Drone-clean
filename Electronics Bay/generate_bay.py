"""生成上下两件式 Mercury 承力电子舱，尺寸单位为毫米。

依赖：cadquery 2.8、trimesh、manifold3d、vtk、scipy、shapely、
matplotlib、pymupdf、lxml；肩座位置由原始矢量 PDF 反推。
各 STL 已独立调整打印朝向；STEP 保留上下壳的装配位置。
"""
from pathlib import Path
import json
import math

import cadquery as cq
import numpy as np
import trimesh

from bay_layout import DIVIDERS, DIVIDER_HEIGHT, generate_layout, pcb_mounts
from chassis_interfaces import (
    INNER_HOLE_Y, MOUNT_Z, PAD_OUTER_X, RAIL_END, RAIL_INNER_X, RAIL_OUTER_X,
    aligned_shoulders, connection_report, export_print_shoulders, export_registered_assembly,
    mesh_interference_volume, render_pdf_registration, verify_shoulder_fit,
)
from localization import chinese_font_path

OUT = Path(__file__).resolve().parent
W, L = 164.8, 201.2
WALL, FLOOR = 3.0, 4.0
SPLIT, GAP, TOP = 78.0, 0.3, 93.3
CORNER = 8.0
LID_HOLES = [(x, y) for x in (-85.4, 85.4)
             for y in (-70.0, -42.0, 42.0, 70.0)]


def rounded(w, length, radius, z, height):
    return (cq.Workplane("XY", origin=(0, 0, z))
            .sketch().rect(w, length).vertices().fillet(radius)
            .finalize().extrude(height))


def ring(w, length, radius, inner_w, inner_l, inner_r, z, height):
    return rounded(w, length, radius, z, height).cut(
        rounded(inner_w, inner_l, inner_r, z - 0.1, height + 0.2))


def cylinder(radius, height, base, direction=(0, 0, 1)):
    return cq.Workplane(obj=cq.Solid.makeCylinder(
        radius, height, cq.Vector(*base), cq.Vector(*direction)))


def box(w, length, height, x, y, z):
    return cq.Workplane("XY", origin=(x, y, z)).box(
        w, length, height, centered=(True, True, False))


def build():
    lower = rounded(W, L, CORNER, 0, SPLIT)
    lower = lower.cut(rounded(W - 6, L - 6, 5, FLOOR, SPLIT + 1))
    # 密封接触面宽 6 mm；2 mm 硅胶密封条置于 2.4 × 1.3 mm 槽内。
    lower = lower.union(ring(W, L, CORNER, W - 12, L - 12, 2, SPLIT - 4, 4))
    groove = ring(W - 3.6, L - 3.6, 6.2,
                  W - 8.4, L - 8.4, 3.8, SPLIT - 1.3, 1.5)
    lower = lower.cut(groove)

    # 一体式承力箱形侧梁，取代可拆卸碳纤维侧板。
    # 开窗使侧梁空腔可达，方便移除支撑。
    for side in (-1, 1):
        lower = lower.union(box(RAIL_OUTER_X - RAIL_INNER_X, 2 * RAIL_END, SPLIT,
                                side * ((RAIL_OUTER_X + RAIL_INNER_X) / 2), 0, 0))
        for z, height in ((0, 6), (SPLIT - 8, 8)):
            lower = lower.union(box(RAIL_OUTER_X - 78.4, L, height,
                                    side * ((RAIL_OUTER_X + 78.4) / 2), 0, z))
        for y in (-50, 0, 50):
            lower = lower.union(box(RAIL_OUTER_X - 82, 4, SPLIT - 14,
                                    side * ((RAIL_OUTER_X + 82) / 2), y, 6))
        for end in (-1, 1):
            lower = lower.union(box(PAD_OUTER_X - RAIL_OUTER_X, RAIL_END - 92, SPLIT,
                                    side * ((PAD_OUTER_X + RAIL_OUTER_X) / 2),
                                    end * ((RAIL_END + 92) / 2), 0))
            for z in MOUNT_Z:
                # M3 贯穿螺栓与防松螺母承力，不依赖热熔铜螺母承力。
                lower = lower.cut(cylinder(1.6, 12,
                                  (side * (PAD_OUTER_X + .1), end * INNER_HOLE_Y, z),
                                  (-side, 0, 0)))
        for y in (-75, -25, 25, 75):
            window = (cq.Workplane("YZ", origin=(side * 89.6, y, 39))
                      .sketch().rect(32, 44).vertices().fillet(6)
                      .finalize().extrude(side * 12))
            lower = lower.cut(window)

    upper = rounded(W, L, CORNER, SPLIT + GAP, TOP - SPLIT - GAP)
    upper = upper.cut(rounded(W - 6, L - 6, 5,
                             SPLIT + GAP - 0.1, TOP - 3 - (SPLIT + GAP) + 0.1))
    # 上盖法兰与定位裙边，单侧配合间隙为 0.30 mm。
    upper = upper.union(ring(W, L, CORNER, W - 17.4, L - 17.4, 1,
                             SPLIT + GAP, 3))
    upper = upper.union(ring(W - 12.6, L - 12.6, 1.7,
                             W - 17.4, L - 17.4, 1, SPLIT - 2.2, 2.8))

    for x, y in LID_HOLES:
        lower = lower.union(cylinder(5, SPLIT + GAP, (x, y, 0)))
        lower = lower.cut(cylinder(2.1, 5.2, (x, y, SPLIT + GAP), (0, 0, -1)))
        lower = lower.cut(cylinder(1.6, 8.5, (x, y, SPLIT + GAP), (0, 0, -1)))
        upper = upper.union(cylinder(5, TOP - SPLIT - GAP,
                                    (x, y, SPLIT + GAP)))
        upper = upper.cut(cylinder(1.7, 16, (x, y, SPLIT + GAP - 0.1)))
        # 直径 5.8 mm、深 3.2 mm 的内六角螺钉头沉孔，使用 M3×20 螺钉。
        upper = upper.cut(cylinder(2.9, 3.3, (x, y, TOP - 3.2)))

    # 实际布局对应的盲导孔：旋转后的树莓派 5 及标准 Cube 载板。
    for x, y in pcb_mounts():
        lower = lower.union(cylinder(3.5, 6, (x, y, FLOOR)))
        lower = lower.cut(cylinder(1.1, 4.2, (x, y, FLOOR + 6), (0, 0, -1)))

    # 圆角矮挡用于定位板件，不形成封闭线槽。
    for x, y, width, length in DIVIDERS:
        stop = box(width, length, DIVIDER_HEIGHT + 0.2, x, y, FLOOR - 0.2)
        lower = lower.union(stop.edges(">Z").fillet(0.6))

    # 两个 M12 间隙孔，必须安装密封格兰头或密封堵头。
    for x in (-35, 35):
        lower = lower.union(cylinder(11, 6, (x, L / 2 - 6, 25), (0, 1, 0)))
        lower = lower.cut(cylinder(6.1, 7, (x, L / 2 - 6.5, 25), (0, 1, 0)))

    lower, upper = lower.clean(), upper.clean()
    for name, part in (("lower", lower), ("upper", upper)):
        if not part.val().isValid() or len(part.solids().vals()) != 1:
            raise ValueError(f"{name}：BRep 无效或几何实体断开")
    interference = lower.intersect(upper).val().Volume()
    if interference > 1e-5:
        raise ValueError(f"上下壳装配干涉：{interference} mm³")
    return lower, upper, interference




def mesh_report(path):
    mesh = trimesh.load(path, force="mesh")
    if not mesh.is_volume or len(mesh.split()) != 1:
        raise ValueError(f"{path.name}：不是单个闭合且朝外定向的实体")
    # 实际截取切片，覆盖最窄裙边及热熔螺母所在高度。
    levels = [0.2, 4, 6, 9.8, 10.2, 19.5, 39, 70.5, 75, 78] if "Lower" in path.name else [0.2, 3.2, 10, 14.9, 16, 17]
    contours = []
    for z in levels:
        section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if section is None or not section.is_closed:
            raise ValueError(f"{path.name}：z={z} 处切片缺失或未闭合")
        contours.append({"z_mm": z, "closed_loops": len(section.discrete)})
    return {"file": path.name, "triangles": len(mesh.faces),
            "watertight": bool(mesh.is_watertight),
            "connected_solids": len(mesh.split()),
            "bounds_mm": mesh.bounds.tolist(), "size_mm": mesh.extents.tolist(),
            "solid_volume_cm3": mesh.volume / 1000,
            "slice_checks": contours}, mesh


def preview():
    # 使用深度缓冲；仅按前后排序绘制三角形会错误显示凹形壳体。
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
    font_path = chinese_font_path()

    mappers = {}
    for name in ("Lower", "Upper"):
        reader = vtk.vtkSTLReader()
        reader.SetFileName(str(OUT / f"Electronics_Bay_{name}.stl"))
        reader.Update()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(reader.GetOutput())
        mappers[name] = mapper
    for name, mesh in aligned_shoulders().items():
        points = vtk.vtkPoints()
        points.SetData(numpy_to_vtk(mesh.vertices, deep=True))
        cells = vtk.vtkCellArray()
        cells.SetData(
            numpy_to_vtkIdTypeArray(np.arange(0, 3 * (len(mesh.faces) + 1), 3, dtype=np.int64), deep=True),
            numpy_to_vtkIdTypeArray(mesh.faces.ravel().astype(np.int64), deep=True))
        data = vtk.vtkPolyData()
        data.SetPoints(points)
        data.SetPolys(cells)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(data)
        mappers[name] = mapper
    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetSize(2100, 850)
    scenes = [
        ("一体式承力下舱与加强侧梁", None),
        ("上盖与承力下舱（分解视图）", 55),
        ("配套改版肩座装配（无碳板）", 0),
    ]
    for i, (title, separation) in enumerate(scenes):
        renderer = vtk.vtkRenderer()
        renderer.SetViewport(i / 3, 0, (i + 1) / 3, 1)
        renderer.SetBackground(1, 1, 1)
        window.AddRenderer(renderer)
        names = ("Lower",) if separation is None else ("Lower", "Upper")
        if i == 2:
            names += ("Front", "Rear")
        for name in names:
            actor = vtk.vtkActor()
            actor.SetMapper(mappers[name])
            color = {"Lower": (.18, .55, .65), "Upper": (.9, .6, .2),
                     "Front": (.38, .4, .44), "Rear": (.38, .4, .44)}[name]
            actor.GetProperty().SetColor(*color)
            if name == "Upper":
                actor.SetOrientation(180, 0, 0)
                actor.SetPosition(0, 0, TOP + separation)
            renderer.AddActor(actor)
        label = vtk.vtkTextActor()
        label.SetInput(title)
        label.SetPosition(20, 800)
        label.GetTextProperty().SetFontSize(20)
        label.GetTextProperty().SetFontFamily(vtk.VTK_FONT_FILE)
        label.GetTextProperty().SetFontFile(font_path)
        label.GetTextProperty().SetColor(0.15, 0.15, 0.15)
        renderer.AddViewProp(label)
        camera = renderer.GetActiveCamera()
        camera.SetPosition(280, -360, 310)
        camera.SetFocalPoint(0, 0, 50)
        camera.SetViewUp(0, 0, 1)
        camera.ParallelProjectionOn()
        camera.SetParallelScale((180, 205, 265)[i])
        renderer.ResetCameraClippingRange()
    window.Render()
    image = vtk.vtkWindowToImageFilter()
    image.SetInput(window)
    image.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(OUT / "Electronics_Bay_Preview.png"))
    writer.SetInputConnection(image.GetOutputPort())
    writer.Write()
    window.Finalize()


def main():
    registration = connection_report()
    layout = generate_layout()
    lower, upper, interference = build()
    # 上盖顶面贴打印平台，定位裙边朝上。
    upper_print = upper.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, TOP))
    files = [("Electronics_Bay_Lower.stl", lower),
             ("Electronics_Bay_Upper.stl", upper_print)]
    reports, meshes = [], []
    for name, shape in files:
        path = OUT / name
        cq.exporters.export(shape, str(path), tolerance=0.03, angularTolerance=0.1)
        report, mesh = mesh_report(path)
        reports.append(report); meshes.append(mesh)
    assembly = cq.Assembly(name="Mercury_Electronics_Bay")
    assembly.add(lower, name="Lower", color=cq.Color(0.15, 0.55, 0.65))
    assembly.add(upper, name="Upper", color=cq.Color(0.9, 0.6, 0.2))
    assembly.export(str(OUT / "Electronics_Bay_Assembly.step"))
    # 从导出的 STL 重建装配后，用另一几何内核交叉检查。
    upper_assembled = meshes[1].copy()
    upper_assembled.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
    upper_assembled.apply_translation([0, 0, TOP])
    collision_volume = mesh_interference_volume(meshes[0], upper_assembled)
    if collision_volume > 0.01:
        raise ValueError(f"导出网格装配干涉：{collision_volume}")
    shoulder_fit = verify_shoulder_fit(meshes[0], upper_assembled)
    shoulder_prints = export_print_shoulders()
    export_registered_assembly(meshes[0], upper_assembled)
    render_pdf_registration()
    preview()
    report = {"units": "mm", "assembly_coordinates": "PDF 前后肩座中点为 Y=0，舱底为 Z=0，肩座中心高度 Z=45 mm。",
              "assembly_interference_mm3": interference,
              "exported_mesh_interference_mm3": collision_volume,
              "registration_clearance_per_side_mm": 0.3,
              "gasket": {"cord_diameter_mm": 2, "groove_width_mm": 2.4,
                         "groove_depth_mm": 1.3, "closed_face_gap_mm": GAP,
                         "nominal_compression_percent": 20},
              "connection": registration, "shoulder_interference_mm3": shoulder_fit,
              "parts": reports, "adapted_shoulder_prints": shoulder_prints,
              "layout_check": {key: layout[key] for key in (
                  "all_bom_components_fit", "minimum_board_edge_gap_mm",
                  "minimum_board_to_stop_gap_mm", "divider_count",
                  "divider_height_above_floor_mm")}}
    (OUT / "Validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
