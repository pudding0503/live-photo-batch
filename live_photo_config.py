"""Small, explicit configuration surface for the Live Photo batch tool."""

from dataclasses import dataclass


PACKAGE_MODES = ("wallpaper", "album")
DEFAULT_MODE = "wallpaper"


@dataclass(frozen=True)
class IPhoneModel:
    key: str
    label: str
    device_verified: bool = False


# Keep this list easy to extend when a model-specific device experiment exists.
IPHONE_MODELS = (
    IPhoneModel("target", "Target iPhone (device-verified)", True),
    IPhoneModel("iphone-11", "iPhone 11"),
    IPhoneModel("iphone-12", "iPhone 12"),
    IPhoneModel("iphone-13", "iPhone 13"),
    IPhoneModel("iphone-14", "iPhone 14"),
    IPhoneModel("iphone-15", "iPhone 15"),
    IPhoneModel("iphone-16", "iPhone 16"),
    IPhoneModel("other", "Other iPhone"),
)
DEFAULT_TARGET_DEVICE = "target"
