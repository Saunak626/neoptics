from __future__ import annotations

import numpy as np
import pytest

from neoptics import build_prop_table, load_optical_properties


def test_load_optical_properties_supports_all_wavelengths() -> None:
    props = load_optical_properties(530)
    assert props["arterial_blood"]["mua"] == pytest.approx(24.24)
    assert props["venous_blood_optional"]["mus"] == pytest.approx(92.08)


def test_build_prop_table_has_fixed_label_order() -> None:
    prop = build_prop_table(660)
    assert prop.shape == (7, 4)
    assert np.allclose(prop[5], np.array([0.247, 92.29, 0.985, 1.40]))
    assert np.allclose(prop[6], np.array([0.723, 81.45, 0.986, 1.40]))


def test_invalid_wavelength_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported wavelength"):
        build_prop_table(700)
