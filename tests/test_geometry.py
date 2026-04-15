from __future__ import annotations

import pytest

from neoptics import build_wrist_volume


def test_build_wrist_volume_profiles_have_expected_shape() -> None:
    preterm_volume, preterm_metadata = build_wrist_volume("preterm_wrist", voxel_size_mm=0.2)
    term_volume, term_metadata = build_wrist_volume("term_wrist", voxel_size_mm=0.2)

    assert preterm_volume.shape == (160, 140, 80)
    assert term_volume.shape == (160, 140, 80)
    assert preterm_metadata["profile"] == "preterm_wrist"
    assert term_metadata["profile"] == "term_wrist"
    assert 5 in set(preterm_volume.flatten().tolist())


def test_build_wrist_volume_can_enable_vein() -> None:
    volume, metadata = build_wrist_volume("preterm_wrist", include_vein=True, voxel_size_mm=0.2)
    labels = set(volume.flatten().tolist())

    assert metadata["include_vein"] is True
    assert 6 in labels


def test_invalid_geometry_overlap_raises() -> None:
    with pytest.raises(ValueError, match="overlaps the bone"):
        build_wrist_volume(
            "preterm_wrist",
            overrides={"artery_center_x_mm": 3.0, "artery_center_y_mm": 2.0},
            voxel_size_mm=0.2,
        )


def test_invalid_geometry_layer_depth_raises() -> None:
    with pytest.raises(ValueError, match="skin \\+ fat|collapses the wrist profile"):
        build_wrist_volume(
            "preterm_wrist",
            overrides={"fat_thickness_mm": 7.0},
            voxel_size_mm=0.2,
        )
