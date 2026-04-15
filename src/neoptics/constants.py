LABELS = {
    "air": 0,
    "skin": 1,
    "fat": 2,
    "soft_tissue_or_muscle": 3,
    "bone": 4,
    "arterial_blood": 5,
    "venous_blood_optional": 6,
}

LABEL_ORDER = [name for name, _ in sorted(LABELS.items(), key=lambda item: item[1])]

SUPPORTED_WAVELENGTHS = (530, 660, 940)

SUPPORTED_MODES = ("reflectance", "transmittance")
