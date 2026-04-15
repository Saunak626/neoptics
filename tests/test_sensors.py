from __future__ import annotations

import pytest

from neoptics import build_reflectance_sensor, build_transmittance_sensor, build_wrist_volume


def test_reflectance_sensor_separation_is_mapped_to_voxels() -> None:
    _, metadata = build_wrist_volume("preterm_wrist", voxel_size_mm=0.2)
    sensor = build_reflectance_sensor(
        "preterm_wrist",
        660,
        metadata,
        overrides={"separation_mm": 4.0},
    )
    assert sensor["detpos"][0][0] - sensor["srcpos"][0] == pytest.approx(20.0)
    assert sensor["srcdir"] == [0.0, 1.0, 0.0]


def test_transmittance_sensor_offset_is_mapped_to_detector_position() -> None:
    _, metadata = build_wrist_volume("term_wrist", voxel_size_mm=0.2)
    sensor = build_transmittance_sensor(
        "term_wrist",
        940,
        metadata,
        overrides={"lateral_offset_mm": 2.0},
    )
    assert sensor["detpos"][0][0] - sensor["srcpos"][0] == pytest.approx(10.0)
    assert sensor["detpos"][0][1] > sensor["srcpos"][1]
