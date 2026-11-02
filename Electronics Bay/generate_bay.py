"""Generate a two-piece Mercury electronics bay, in millimetres.

Run with Python 3.12+, cadquery 2.8, trimesh, manifold3d, vtk, scipy.
Original CargoBay frame: print coordinates = original coordinates + (0, 0, 60.15).
STLs are independently oriented for printing; STEP preserves assembly coordinates.
"""
from pathlib import Path
import json
import math

import cadquery as cq
import numpy as np
import trimesh

OUT = Path(__file__).resolve().parent
SOURCE = OUT.parent / "STL Files" / "CargoBay - Base.stl"
W, L = 164.8, 201.2
WALL, FLOOR = 3.0, 3.0
SPLIT, GAP, TOP = 45.0, 0.3, 60.3
CORNER = 8.0
# Eight original horizontal frame holes: (Y, Z in original frame).
FRAME_HOLES = [(-97.1, -48.65), (-26.0, -48.15),
               (26.0, -48.15), (97.1, -48.65)]
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
    # Six-mm sealing land; the 2-mm silicone cord sits in a 2.4 x 1.3 groove.
    lower = lower.union(ring(W, L, CORNER, W - 12, L - 12, 2, 41, 4))
    groove = ring(W - 3.6, L - 3.6, 6.2,
                  W - 8.4, L - 8.4, 3.8, SPLIT - 1.3, 1.5)
    lower = lower.cut(groove)

    # External dry mounting pads: no frame fastener penetrates the wet boundary.
    for side in (-1, 1):
        for y, original_z in FRAME_HOLES:
            z = original_z + 60.15
            lower = lower.union(box(12, 7, z + 7.5, side * 84.4, y, 0))
            # M3 insert: OD 4.2 x 5 mm. Pilot retains a blind inner wall.
            lower = lower.cut(cylinder(2.1, 5.2,
                              (side * 90.4, y, z), (-side, 0, 0)))
            lower = lower.cut(cylinder(1.6, 9,
                              (side * 90.4, y, z), (-side, 0, 0)))

    upper = rounded(W, L, CORNER, SPLIT + GAP, TOP - SPLIT - GAP)
    upper = upper.cut(rounded(W - 6, L - 6, 5,
                             SPLIT + GAP - 0.1, TOP - 3 - (SPLIT + GAP) + 0.1))
    # Lid flange and registration skirt; 0.30 mm per-side clearance.
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
        # Recess 5.8-mm socket head, 3.2 mm deep; use M3 x 20 screws.
        upper = upper.cut(cylinder(2.9, 3.3, (x, y, TOP - 3.2)))

    # Internal blind M2.5 pilots. Pi 5: 58 x 49; generic FC: 30.5 x 30.5.
    pcb_holes = [(x, y - 45) for x in (-29, 29) for y in (-24.5, 24.5)]
    pcb_holes += [(x, y + 40) for x in (-15.25, 15.25)
                 for y in (-15.25, 15.25)]
    for x, y in pcb_holes:
        lower = lower.union(cylinder(3.5, 6, (x, y, FLOOR)))
        lower = lower.cut(cylinder(1.1, 4.2, (x, y, FLOOR + 6), (0, 0, -1)))

    # Two M12 clearance ports. Fit sealed glands or sealed blanking plugs.
    for x in (-35, 35):
        lower = lower.union(cylinder(11, 6, (x, L / 2 - 6, 25), (0, 1, 0)))
        lower = lower.cut(cylinder(6.1, 7, (x, L / 2 - 6.5, 25), (0, 1, 0)))

    lower, upper = lower.clean(), upper.clean()
    for name, part in (("lower", lower), ("upper", upper)):
        if not part.val().isValid() or len(part.solids().vals()) != 1:
            raise ValueError(f"{name}: invalid BRep or disconnected geometry")
    interference = lower.intersect(upper).val().Volume()
    if interference > 1e-5:
        raise ValueError(f"Assembly interference: {interference} mm^3")
    return lower, upper, interference


def verify_original_mounts():
    """Measure original bore loops, not filenames or assumed blueprint scale."""
    original = trimesh.load(SOURCE, force="mesh")
    observed = []
    for side in (-1, 1):
        section = original.section(plane_origin=[side * 89, 0, 0],
                                   plane_normal=[1, 0, 0])
        holes = []
        for loop in section.discrete:
            yz = loop[:, 1:]
            extent = np.ptp(yz, axis=0)
            if np.all(np.abs(extent - 3) < 0.03):
                holes.append((yz.min(axis=0) + yz.max(axis=0)) / 2)
        holes = np.array(sorted(holes, key=lambda a: a[0]))
        if holes.shape != (4, 2) or not np.allclose(holes, FRAME_HOLES, atol=0.01):
            raise ValueError(f"Original mount measurements changed: {holes}")
        observed.append({"x_section_mm": side * 89, "hole_yz_mm": holes.tolist()})
    return observed


def mesh_report(path):
    mesh = trimesh.load(path, force="mesh")
    if not mesh.is_volume or len(mesh.split()) != 1:
        raise ValueError(f"{path.name}: not a single closed outward-oriented solid")
    # Exercise actual slicing, including the narrowest skirt and insert layers.
    levels = [0.2, 3, 8, 15, 25, 35, 42, 44, 45] if "Lower" in path.name else [0.2, 3.2, 10, 14.9, 16, 17]
    contours = []
    for z in levels:
        section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if section is None or not section.is_closed:
            raise ValueError(f"{path.name}: open/missing slice at z={z}")
        contours.append({"z_mm": z, "closed_loops": len(section.discrete)})
    return {"file": path.name, "triangles": len(mesh.faces),
            "watertight": bool(mesh.is_watertight),
            "connected_solids": len(mesh.split()),
            "bounds_mm": mesh.bounds.tolist(), "size_mm": mesh.extents.tolist(),
            "solid_volume_cm3": mesh.volume / 1000,
            "slice_checks": contours}, mesh


def preview():
    # Use a depth buffer: painter-sorted triangles misrender concave shells.
    import vtk

    mappers = {}
    for name in ("Lower", "Upper"):
        reader = vtk.vtkSTLReader()
        reader.SetFileName(str(OUT / f"Electronics_Bay_{name}.stl"))
        reader.Update()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(reader.GetOutput())
        mappers[name] = mapper
    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetSize(2100, 850)
    scenes = [
        ("Lower shell / electronics compartment", None),
        ("Two-piece assembly / exploded", 55),
        ("Assembled / 180.8 x 201.2 x 60.3 mm", 0),
    ]
    for i, (title, separation) in enumerate(scenes):
        renderer = vtk.vtkRenderer()
        renderer.SetViewport(i / 3, 0, (i + 1) / 3, 1)
        renderer.SetBackground(1, 1, 1)
        window.AddRenderer(renderer)
        for name in (("Lower",) if separation is None else ("Lower", "Upper")):
            actor = vtk.vtkActor()
            actor.SetMapper(mappers[name])
            actor.GetProperty().SetColor(
                *((0.18, 0.55, 0.65) if name == "Lower" else (0.9, 0.6, 0.2)))
            if name == "Upper":
                actor.SetOrientation(180, 0, 0)
                actor.SetPosition(0, 0, TOP + separation)
            renderer.AddActor(actor)
        label = vtk.vtkTextActor()
        label.SetInput(title)
        label.SetPosition(20, 800)
        label.GetTextProperty().SetFontSize(20)
        label.GetTextProperty().SetColor(0.15, 0.15, 0.15)
        renderer.AddViewProp(label)
        camera = renderer.GetActiveCamera()
        camera.SetPosition(280, -360, 310)
        camera.SetFocalPoint(0, 0, 40)
        camera.SetViewUp(0, 0, 1)
        camera.ParallelProjectionOn()
        camera.SetParallelScale(175)
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
    measured = verify_original_mounts()
    lower, upper, interference = build()
    # The upper roof rests on the bed; its registration skirt points upwards.
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
    # A second kernel checks exported meshes, after reconstructing STL assembly.
    upper_assembled = meshes[1].copy()
    upper_assembled.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
    upper_assembled.apply_translation([0, 0, TOP])
    collision = trimesh.boolean.intersection([meshes[0], upper_assembled], engine="manifold")
    # Touching stop faces have zero volume and no defined centre of mass.
    triangles = collision.triangles
    collision_volume = abs(float(np.einsum(
        "ij,ij->i", triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])
    ).sum()) / 6)
    if collision_volume > 0.01:
        raise ValueError(f"Exported mesh interference: {collision_volume}")
    preview()
    report = {"units": "mm", "original_to_assembly_translation_mm": [0, 0, 60.15],
              "assembly_interference_mm3": interference,
              "exported_mesh_interference_mm3": collision_volume,
              "registration_clearance_per_side_mm": 0.3,
              "gasket": {"cord_diameter_mm": 2, "groove_width_mm": 2.4,
                         "groove_depth_mm": 1.3, "closed_face_gap_mm": GAP,
                         "nominal_compression_percent": 20},
              "original_mount_measurements": measured, "parts": reports}
    (OUT / "Validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
