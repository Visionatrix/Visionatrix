# This a Dev script, to check if all built-in flows can be correctly installed using CLI command.

import subprocess


FLOWS = [
    "SDXL_Lighting_8",
    "Playground_2_5_aesthetic",
    "Photomaker_1",
    "Juggernaut_Lighting_LoRAs",
]

for i in FLOWS:
    param_template = f"install-flow --flow flows/{i}/flow.json --flow_comfy flows/{i}/flow_comfy.json"
    cmd = ["python3", "-m", "ai_media_wizard", *param_template.split()]
    print("Executing:", *cmd)
    subprocess.run(cmd, check=True)
