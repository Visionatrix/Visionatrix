from .pydantic_models import AIResourceModel

BASIC_NODE_LIST = {
    "ComfyUI-Impact-Pack": {
        "main_branch": "Main",
    },
    "ComfyUI_UltimateSDUpscale": {
        "git_flags": "--recursive",
    },
    "ComfyUI_InstantID": {
        "requirements": {
            "insightface": {},
            "onnxruntime": {},
        },
        "models": [
            AIResourceModel(
                name="antelopev2",
                save_path="{root}models/insightface/models/antelopev2.zip",
                url="https://huggingface.co/MonsterMMORPG/tools/resolve/main/antelopev2.zip",
                homepage="https://github.com/deepinsight/insightface",
                hash="8e182f14fc6e80b3bfa375b33eb6cff7ee05d8ef7633e738d1c89021dcf0c5c5",
                hashes={
                    "1k3d68.onnx": "df5c06b8a0c12e422b2ed8947b8869faa4105387f199c477af038aa01f9a45cc",
                    "2d106det.onnx": "f001b856447c413801ef5c42091ed0cd516fcd21f2d6b79635b1e733a7109dbf",
                    "genderage.onnx": "4fde69b1c810857b88c64a335084f1c3fe8f01246c9a191b48c7bb756d6652fb",
                    "glintr100.onnx": "4ab1d6435d639628a6f3e5008dd4f929edf4c4124b1a7169e1048f9fef534cdf",
                    "scrfd_10g_bnkps.onnx": "5838f7fe053675b1c7a08b633df49e7af5495cee0493c7dcf6697200b85b5b91",
                },
            ),
        ],
    },
    "ComfyUI-BRIA_AI-RMBG": {
        "models": [
            AIResourceModel(
                name="RMGB-1.4",
                save_path="{root}custom_nodes/ComfyUI-BRIA_AI-RMBG/RMBG-1.4/model.pth",
                url="https://huggingface.co/andrey18106/vix_models/resolve/main/RMBG-1.4/model.pth",
                homepage="https://huggingface.co/briaai/RMBG-1.4",
                hash="893c16c340b1ddafc93e78457a4d94190da9b7179149f8574284c83caebf5e8c",
            ),
        ],
    },
    "efficiency-nodes-comfyui": {
        "requirements": {
            "simpleeval": {},
        }
    },
    "ComfyUI-WD14-Tagger": {},
    "ComfyUI-SUPIR": {},
    "ComfyUI_essentials": {},
    "rgthree-comfy": {},
    "ComfyUI-Custom-Scripts": {},
    "ComfyUI_IPAdapter_plus": {},
    "comfyui_controlnet_aux": {},
    "Skimmed_CFG": {},
    "comfyui-art-venture": {},
    "was-node-suite-comfyui": {},
    "ComfyUI-Visionatrix": {},
    "comfyui-ollama": {},
    "ComfyUI-AutoCropFaces": {},
    "PuLID_ComfyUI": {
        "before_install": {
            "python": "-m pip install --use-pep517 facexlib",
        },
        "requirements": {
            "facexlib": {},
            "insightface": {},
            "onnxruntime": {},
            "ftfy": {},
            "timm": {},
        },
    },
    "ComfyUI_FizzNodes": {},
    "style_aligned_comfy": {
        "main_branch": "master",
    },
    "ComfyUI_Gemini_Flash": {},
}
