from .pydantic_models import AIResourceModel

BASIC_NODE_LIST = {
    "ComfyUI-Impact-Pack": {
        "main_branch": "Main",
        "models": [
            AIResourceModel(
                name="sam_vit_b_01ec64",
                save_path="{root}models/sams/sam_vit_b_01ec64.pth",
                url="https://huggingface.co/andrey18106/visionatrix_models/resolve/main/sams/sam_vit_b_01ec64.pth",
                homepage="https://github.com/facebookresearch/segment-anything",
                hash="ec2df62732614e57411cdcf32a23ffdf28910380d03139ee0f4fcbe91eb8c912",
            ),
        ],
    },
    "ComfyUI_UltimateSDUpscale": {
        "git_flags": "--recursive",
    },
    "ComfyUI_InstantID": {
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
                url="https://huggingface.co/andrey18106/visionatrix_models/resolve/main/RMBG-1.4/model.pth",
                homepage="https://huggingface.co/briaai/RMBG-1.4",
                hash="893c16c340b1ddafc93e78457a4d94190da9b7179149f8574284c83caebf5e8c",
            ),
        ],
    },
    "ComfyUI-BiRefNet": {
        "models": [
            AIResourceModel(
                name="ComfyUI-BiRefNet-EP480",
                save_path="{root}models/BiRefNet/BiRefNet-ep480.pth",
                url="https://huggingface.co/ViperYX/BiRefNet/resolve/main/BiRefNet-ep480.pth",
                homepage="https://huggingface.co/ViperYX/BiRefNet",
                hash="367a738b27e0556e703991e8160fe6b5217bec6c158a72a890d131dd11ba74f6",
            ),
            AIResourceModel(
                name="ComfyUI-BiRefNet-Swin-Large",
                save_path="{root}models/BiRefNet/swin_large_patch4_window12_384_22kto1k.pth",
                url="https://huggingface.co/ViperYX/BiRefNet/resolve/main/swin_large_patch4_window12_384_22kto1k.pth",
                homepage="https://huggingface.co/ViperYX/BiRefNet",
                hash="30762928cd6ee9229e24e26e200951b8fe635799b67db016ba747fa653b64db9",
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
    },
    "ComfyUI_FizzNodes": {},
    "style_aligned_comfy": {
        "main_branch": "master",
    },
    "ComfyUI_Gemini_Flash": {},
    "ComfyUI-Inpaint-CropAndStitch": {},
    "ComfyUI-PhotoMaker-Plus": {
        "models": [
            AIResourceModel(
                name="buffalo_l",
                save_path="{root}models/insightface/models/buffalo_l.zip",
                url="https://huggingface.co/andrey18106/visionatrix_models/resolve/main/insightface/buffalo_l.zip",
                homepage="https://github.com/deepinsight/insightface",
                hash="80ffe37d8a5940d59a7384c201a2a38d4741f2f3c51eef46ebb28218a7b0ca2f",
                hashes={
                    "1k3d68.onnx": "df5c06b8a0c12e422b2ed8947b8869faa4105387f199c477af038aa01f9a45cc",
                    "2d106det.onnx": "f001b856447c413801ef5c42091ed0cd516fcd21f2d6b79635b1e733a7109dbf",
                    "genderage.onnx": "4fde69b1c810857b88c64a335084f1c3fe8f01246c9a191b48c7bb756d6652fb",
                    "det_10g.onnx": "5838f7fe053675b1c7a08b633df49e7af5495cee0493c7dcf6697200b85b5b91",
                    "w600k_r50.onnx": "4c06341c33c2ca1f86781dab0e829f88ad5b64be9fba56e56bc9ebdefc619e43",
                },
            ),
        ],
        "requirements": {},  # https://github.com/shiimizu/ComfyUI-PhotoMaker-Plus/pull/41
    },
}
