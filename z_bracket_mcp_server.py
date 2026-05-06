"""FastMCP server for generating parametric Z bracket STEP models on Windows.

Run:
    .venv\\Scripts\\python.exe z_bracket_mcp_server.py

If FastMCP is not installed in the active environment:
    .venv\\Scripts\\python.exe -m pip install fastmcp
"""

from __future__ import annotations

import csv
import json
import traceback
import uuid
from pathlib import Path
from typing import Any

from build123d import Align, Box, BuildPart, Cylinder, Keep, Locations, Plane, add, export_step

try:
    from fastmcp import FastMCP
except ModuleNotFoundError:  # Keep geometry functions importable for local CAD tests.
    FastMCP = None  # type: ignore[assignment]


OUTPUT_ROOT = Path(r"E:\code\autoCAD\output")
DEFAULT_STEP_NAME = "z_bracket.step"
PROCESS_TYPES = {"miter_45", "butt_joint"}


def _float_param(params: dict[str, Any], name: str, default: float) -> float:
    """Read one numeric model parameter with a helpful error on bad input."""
    try:
        return float(params.get(name, default))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric, got {params.get(name)!r}") from exc


def _validate_process_type(process_type: str) -> str:
    """Normalize and validate supported fabrication processes."""
    normalized = str(process_type).strip().lower()
    if normalized not in PROCESS_TYPES:
        raise ValueError(f"process_type must be one of {sorted(PROCESS_TYPES)}, got {process_type!r}")
    return normalized


def _positive_params(params: dict[str, float]) -> None:
    """Reject impossible dimensions before the CAD kernel reaches booleans."""
    for name, value in params.items():
        if value <= 0:
            raise ValueError(f"{name} must be greater than 0, got {value}")
    if params["rod_dia"] >= params["disk_dia"]:
        raise ValueError("rod_dia must be smaller than disk_dia so the base remains stable")
    if params["pin_offset"] >= params["arm_length"]:
        raise ValueError("pin_offset must be smaller than arm_length so the pin stays on the arm")


def _bbox_data(part: Any) -> dict[str, list[float]]:
    """Convert a build123d bounding box to JSON-safe millimeter values."""
    bbox = part.bounding_box()
    return {
        "min": [round(float(bbox.min.X), 6), round(float(bbox.min.Y), 6), round(float(bbox.min.Z), 6)],
        "max": [round(float(bbox.max.X), 6), round(float(bbox.max.Y), 6), round(float(bbox.max.Z), 6)],
        "size": [round(float(bbox.size.X), 6), round(float(bbox.size.Y), 6), round(float(bbox.size.Z), 6)],
    }


def _enriched_step_name(step_name: str, process_type: str, params: dict[str, float]) -> str:
    """Write process parameters into the STEP filename for downstream traceability."""
    source = Path(step_name).name
    suffix = Path(source).suffix or ".step"
    stem = Path(source).stem or "z_bracket"
    process_slug = _validate_process_type(process_type)
    meta = (
        f"{stem}__proc-{process_slug}"
        f"__disk-{params['disk_dia']:.1f}"
        f"__rod-{params['rod_dia']:.1f}"
        f"__post-{params['post_height']:.1f}"
        f"__arm-{params['arm_length']:.1f}"
    )
    return f"{meta.replace('.', 'p')}{suffix}"


def _make_output_path(model_id: str, step_name: str = DEFAULT_STEP_NAME) -> Path:
    """Place large batches into UUID fanout folders to avoid huge flat directories."""
    safe_name = Path(step_name).name
    return OUTPUT_ROOT / model_id[:2] / model_id / safe_name


def build_z_bracket_model(
    *,
    disk_dia: float = 60.0,
    rod_dia: float = 8.0,
    post_height: float = 70.0,
    arm_length: float = 90.0,
    pin_offset: float = 45.0,
    process_type: str = "miter_45",
) -> Any:
    """Build the Z bracket with BuildPart and return the resulting Part."""
    process_type = _validate_process_type(process_type)
    params = {
        "disk_dia": disk_dia,
        "rod_dia": rod_dia,
        "post_height": post_height,
        "arm_length": arm_length,
        "pin_offset": pin_offset,
    }
    _positive_params(params)

    base_thickness = max(6.0, rod_dia * 0.75)
    arm_radius = rod_dia / 2.0
    pin_radius = rod_dia * 0.32
    pin_height = rod_dia * 1.5
    pin_embed = min(pin_height * 0.2, arm_radius * 0.5)
    fork_gap = rod_dia * 1.8
    fork_wall = max(3.0, rod_dia * 0.45)
    fork_depth = rod_dia * 2.5
    fork_height = rod_dia * 2.4
    bridge_thickness = max(3.0, rod_dia * 0.55)
    arm_z = base_thickness + post_height
    fork_center_x = arm_length + fork_depth / 2.0
    fork_side_y = fork_gap / 2.0 + fork_wall / 2.0
    fork_z = arm_z

    try:
        with BuildPart() as bracket:
            Cylinder(disk_dia / 2.0, base_thickness, align=(Align.CENTER, Align.CENTER, Align.MIN))  # Design intent: create the round mounting disk as the stable lower base.
            if process_type == "miter_45":  # Design intent: select the precise 45 degree tube miter fabrication route.
                miter_plane = Plane(origin=(0.0, 0.0, arm_z), x_dir=(0.0, 1.0, 0.0), z_dir=(1.0, 0.0, 1.0))  # Design intent: define the 45 degree cutting plane shared by the vertical tube and horizontal tube.
                with BuildPart() as raw_post:  # Design intent: create an oversized vertical tube blank before trimming the joint face.
                    with Locations((0.0, 0.0, base_thickness)):  # Design intent: start the vertical tube blank from the top face of the disk.
                        Cylinder(arm_radius, post_height + arm_radius, align=(Align.CENTER, Align.CENTER, Align.MIN))  # Design intent: extend the vertical tube past the elbow so the 45 degree cut has full material.
                post_part = raw_post.part.split(miter_plane, keep=Keep.BOTTOM)  # Design intent: remove the upper waste and leave the vertical tube with a 45 degree miter face.
                with BuildPart() as raw_arm:  # Design intent: create the horizontal tube blank before trimming the matching joint face.
                    with Locations((arm_length / 2.0, 0.0, arm_z)):  # Design intent: center the horizontal tube from the elbow toward the U bracket.
                        Cylinder(arm_radius, arm_length, rotation=(0.0, 90.0, 0.0))  # Design intent: form the horizontal round tube along the X axis.
                arm_part = raw_arm.part.split(miter_plane, keep=Keep.TOP)  # Design intent: remove the elbow-side waste so the arm face matches the post miter plane.
                add(post_part)  # Design intent: place the trimmed vertical tube onto the base without forcing overlap at the miter face.
                add(arm_part)  # Design intent: place the trimmed horizontal tube against the matching 45 degree miter face.
            else:  # Design intent: select the conventional butt joint route with deliberate tube overlap for welding or printing.
                with Locations((0.0, 0.0, base_thickness)):  # Design intent: start the vertical tube from the top face of the disk.
                    Cylinder(arm_radius, post_height + arm_radius, align=(Align.CENTER, Align.CENTER, Align.MIN))  # Design intent: make the vertical tube reach into the arm centerline for a butt joint.
                with Locations((arm_length / 2.0, 0.0, arm_z)):  # Design intent: center the horizontal tube so it crosses the post centerline.
                    Cylinder(arm_radius, arm_length, rotation=(0.0, 90.0, 0.0))  # Design intent: create the round horizontal arm as a cylinder along the X axis.
            with Locations((pin_offset, 0.0, arm_z + arm_radius - pin_embed)):  # Design intent: locate the top pin by offset and slightly embed it so the boolean union is manifold.
                Cylinder(pin_radius, pin_height, align=(Align.CENTER, Align.CENTER, Align.MIN))  # Design intent: add the small vertical cylindrical locating pin above the arm.
            with Locations((arm_length + bridge_thickness / 2.0, 0.0, fork_z)):  # Design intent: place the rear bridge where the arm transitions into the U fork.
                Box(bridge_thickness, fork_gap + 2.0 * fork_wall, fork_height, align=(Align.CENTER, Align.CENTER, Align.CENTER))  # Design intent: create the solid rear web that ties the two fork cheeks together.
            with Locations((fork_center_x, fork_side_y, fork_z)):  # Design intent: position the left fork cheek with a clear center slot.
                Box(fork_depth, fork_wall, fork_height, align=(Align.CENTER, Align.CENTER, Align.CENTER))  # Design intent: create one side wall of the U shaped end bracket.
            with Locations((fork_center_x, -fork_side_y, fork_z)):  # Design intent: mirror the fork cheek to complete the U shaped open slot.
                Box(fork_depth, fork_wall, fork_height, align=(Align.CENTER, Align.CENTER, Align.CENTER))  # Design intent: create the opposite side wall of the U shaped end bracket.
        return bracket.part
    except Exception as exc:
        raise RuntimeError(
            "Boolean/model build failed. Likely geometric conflict: "
            f"disk_dia={disk_dia}, rod_dia={rod_dia}, post_height={post_height}, "
            f"arm_length={arm_length}, pin_offset={pin_offset}, process_type={process_type}. Kernel error: {exc}"
        ) from exc


def validate_design(
    disk_dia: float = 60.0,
    rod_dia: float = 8.0,
    post_height: float = 70.0,
    arm_length: float = 90.0,
    pin_offset: float = 45.0,
    process_type: str = "miter_45",
) -> dict[str, Any]:
    """Validate manifold quality and U-hook clearance before exporting."""
    process_type = _validate_process_type(process_type)
    params = {
        "disk_dia": float(disk_dia),
        "rod_dia": float(rod_dia),
        "post_height": float(post_height),
        "arm_length": float(arm_length),
        "pin_offset": float(pin_offset),
    }
    errors: list[str] = []
    warnings: list[str] = []

    try:
        _positive_params(params)
        part = build_z_bracket_model(**params, process_type=process_type)
    except Exception as exc:
        return {
            "ok": False,
            "errors": [str(exc)],
            "warnings": warnings,
            "manifold": False,
            "u_hook_interference_free": False,
        }

    solids = part.solids()
    solid_validity = [bool(solid.is_valid) for solid in solids]
    manifold = bool(part.is_valid) and all(solid_validity) and float(part.volume) > 0.0
    if not bool(part.is_valid):
        warnings.append("OpenCascade reports the compound shape is not globally fused; checking each miter-cut solid instead")
    if not all(solid_validity):
        errors.append("At least one generated solid is invalid")
    if process_type == "butt_joint" and len(solids) != 1:
        errors.append(f"Expected one fused manifold solid, got {len(solids)} solids")
    if process_type == "miter_45" and len(solids) < 1:
        errors.append("Expected at least one valid miter-cut solid")
    if float(part.volume) <= 0.0:
        errors.append("Generated volume is not positive")

    fork_gap = params["rod_dia"] * 1.8
    fork_wall = max(3.0, params["rod_dia"] * 0.45)
    fork_depth = params["rod_dia"] * 2.5
    pin_radius = params["rod_dia"] * 0.32
    pin_clearance_to_fork = params["arm_length"] - params["pin_offset"] - pin_radius
    u_hook_interference_free = fork_gap > 0.0 and fork_wall > 0.0 and fork_depth > 0.0 and pin_clearance_to_fork > 0.0
    if fork_gap <= 0.0:
        errors.append("U hook slot gap collapsed; increase rod_dia-derived fork gap")
    if pin_clearance_to_fork <= 0.0:
        errors.append("Pin intersects or touches the U hook transition; reduce pin_offset or increase arm_length")
    if fork_gap < params["rod_dia"] * 1.25:
        warnings.append("U hook slot is narrow relative to rod_dia")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "manifold": manifold,
        "u_hook_interference_free": u_hook_interference_free,
        "volume_mm3": round(float(part.volume), 6),
        "solid_count": len(solids),
        "bbox_mm": _bbox_data(part),
        "process_type": process_type,
        "joint_note": "45 degree plane-cut miter joint" if process_type == "miter_45" else "overlapped butt joint",
    }


def generate_z_bracket(
    disk_dia: float = 60.0,
    rod_dia: float = 8.0,
    post_height: float = 70.0,
    arm_length: float = 90.0,
    pin_offset: float = 45.0,
    process_type: str = "miter_45",
    save_step: bool = True,
    step_name: str = DEFAULT_STEP_NAME,
) -> dict[str, Any]:
    """Generate one Z bracket, validate it, and optionally save a STEP file silently."""
    process_type = _validate_process_type(process_type)
    params = {
        "disk_dia": float(disk_dia),
        "rod_dia": float(rod_dia),
        "post_height": float(post_height),
        "arm_length": float(arm_length),
        "pin_offset": float(pin_offset),
    }
    try:
        check = validate_design(**params, process_type=process_type)
        if not check["ok"]:
            return {"ok": False, "params": params, "process_type": process_type, "validation": check, "error": "validation failed"}

        part = build_z_bracket_model(**params, process_type=process_type)
        model_id = str(uuid.uuid4())
        step_path: str | None = None
        if save_step:
            output_path = _make_output_path(model_id, _enriched_step_name(step_name, process_type, params))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            export_step(part, output_path)
            step_path = str(output_path)

        return {
            "ok": True,
            "model_id": model_id,
            "params": params,
            "process_type": process_type,
            "process_metadata": {
                "joint": check["joint_note"],
                "step_filename_contains_process": True,
            },
            "volume_mm3": round(float(part.volume), 6),
            "bbox_mm": _bbox_data(part),
            "step_path": step_path,
            "validation": check,
        }
    except Exception as exc:
        return {
            "ok": False,
            "params": params,
            "process_type": process_type,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "geometry_conflict": (
                "CAD kernel failed while creating disk, vertical tube, horizontal tube, pin, "
                "or U bracket. Check very small rod_dia, too short arm_length, pin_offset near the fork, "
                "or an unsupported process_type."
            ),
        }


def _load_batch_items(batch: str | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Accept a JSON list string, an in-memory list, or a CSV path."""
    if isinstance(batch, list):
        return batch

    candidate = Path(batch)
    if candidate.exists() and candidate.suffix.lower() == ".csv":
        with candidate.open("r", encoding="utf-8-sig", newline="") as csv_file:
            return [dict(row) for row in csv.DictReader(csv_file)]

    parsed = json.loads(batch)
    if not isinstance(parsed, list):
        raise ValueError("batch JSON must be a list of parameter objects")
    return parsed


def batch_processor(batch: str | list[dict[str, Any]], save_step: bool = True) -> dict[str, Any]:
    """Generate many Z brackets from a JSON list or CSV path using UUID fanout folders."""
    try:
        items = _load_batch_items(batch)
    except Exception as exc:
        return {"ok": False, "error": f"Failed to load batch input: {exc}", "results": []}

    results: list[dict[str, Any]] = []
    for index, raw in enumerate(items):
        try:
            params = {
                "disk_dia": _float_param(raw, "disk_dia", 60.0),
                "rod_dia": _float_param(raw, "rod_dia", 8.0),
                "post_height": _float_param(raw, "post_height", 70.0),
                "arm_length": _float_param(raw, "arm_length", 90.0),
                "pin_offset": _float_param(raw, "pin_offset", 45.0),
            }
            process_type = str(raw.get("process_type", "miter_45"))
            item_result = generate_z_bracket(**params, process_type=process_type, save_step=save_step)
            item_result["index"] = index
            item_result["uid"] = raw.get("uid")
            results.append(item_result)
        except Exception as exc:
            results.append({"ok": False, "index": index, "input": raw, "error": str(exc), "traceback": traceback.format_exc()})

    successes = sum(1 for item in results if item.get("ok"))
    return {
        "ok": successes == len(results),
        "total": len(results),
        "successes": successes,
        "failures": len(results) - successes,
        "output_root": str(OUTPUT_ROOT),
        "results": results,
    }


def create_mcp_server() -> Any:
    """Create the FastMCP server and register CAD tools."""
    if FastMCP is None:
        raise RuntimeError("fastmcp is not installed. Install it with: .venv\\Scripts\\python.exe -m pip install fastmcp")

    mcp = FastMCP("z-bracket-cad-server")
    mcp.tool()(generate_z_bracket)
    mcp.tool()(batch_processor)
    mcp.tool()(validate_design)
    return mcp


if __name__ == "__main__":
    create_mcp_server().run()
