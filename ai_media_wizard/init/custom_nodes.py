import os
from pathlib import Path
from subprocess import run

BASIC_NODE_LIST = {
    "ComfyUI-Impact-Pack": {},
    "ComfyUI_UltimateSDUpscale": {
        "git_flags": "--recursive",
    },
}


def init_base_custom_nodes(custom_nodes_dir: str):
    for k, v in BASIC_NODE_LIST.items():
        print(f"Cloning `{k}`")
        git_flags = v.get("git_flags", "")
        run(
            f"git clone https://github.com/cloud-media-flows/{k}.git {git_flags} {os.path.join(custom_nodes_dir, k)}"
            .split(),
            check=True,
        )
        node_install_script = Path(os.path.join(custom_nodes_dir, k, "install.py"))
        if node_install_script.exists() is True:
            print(f"Running `{k}` install script")
            run(f"python {node_install_script}".split(), check=True)
