"""This file describes information for Visionatrix for which ComfyUI Classes to take or set values."""

CLASS_INFO: dict[str, tuple[str, list[str]]] = {
    # class_name -> (type for UI, [path to value])
    "SDXLAspectRatioSelector": ("list", ["inputs", "aspect_ratio"]),
    "LoadImage": ("image", ["inputs", "image"]),
    "VixUiCheckbox": ("bool", ["inputs", "state"]),
    "VixUiCheckboxLogic": ("bool", ["inputs", "state"]),
    "VixUiRangeFloat": ("range", ["inputs", "value"]),
    "VixUiRangeScaleFloat": ("range_scale", ["inputs", "value"]),
    "VixUiRangeInt": ("range", ["inputs", "value"]),
    "VixUiPrompt": ("text", ["inputs", "text"]),
    "VixUiList": ("list", ["inputs", "default_value"]),
    "VixUiListLogic": ("list", ["inputs", "default_value"]),
}
