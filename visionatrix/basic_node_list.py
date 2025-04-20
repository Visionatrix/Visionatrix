from .pydantic_models import AIResourceModel

COMFYUI_RELEASE_TAG = "v0.3.29"
COMFYUI_MANAGER_RELEASE_TAG = "3.31.8"

ANTELOPEV2 = AIResourceModel(
    name="antelopev2",
    filename="insightface/models/antelopev2.zip",
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
    file_size=360662982,
)

BASIC_NODE_LIST = {
    "comfyui-impact-pack@8.8.1": {
        "models": [
            AIResourceModel(
                name="mmdet_anime-face_yolov3",
                filename="mmdet/bbox/mmdet_anime-face_yolov3.pth",
                url="https://huggingface.co/andrey18106/visionatrix_models/resolve/main/mmdet/bbox/mmdet_anime-face_yolov3.pth",
                homepage="https://huggingface.co/Bingsu/adetailer",
                hash="38208bb6b8a4633193feba532e96ed9a7942129af8fe948b27bfcf8e9a30a12e",
                file_size=246462357,
            ),
            AIResourceModel(
                name="mmdet_anime-face_yolov3-config",
                filename="ultralytics/bbox/mmdet_anime-face_yolov3.py",
                url="https://huggingface.co/andrey18106/visionatrix_models/raw/main/mmdet/bbox/mmdet_anime-face_yolov3.py",
                homepage="https://huggingface.co/Bingsu/adetailer",
                hash="4deda4dde43497fd123d28b08bd1eaff12ab6dd5b1650de5cea41c95e812cd8c",
                file_size=5418,
            ),
            AIResourceModel(
                name="sam_vit_b_01ec64",
                url="https://huggingface.co/andrey18106/visionatrix_models/resolve/main/sams/sam_vit_b_01ec64.pth",
                homepage="https://github.com/facebookresearch/segment-anything",
                hash="ec2df62732614e57411cdcf32a23ffdf28910380d03139ee0f4fcbe91eb8c912",
                types=["sams"],
                file_size=375042383,
            ),
        ],
    },
    "comfyui-impact-subpack@1.2.9": {
        "models": [
            AIResourceModel(
                name="face_yolov8m",
                url="https://huggingface.co/andrey18106/visionatrix_models/resolve/main/ultralytics/bbox/face_yolov8m.pt",
                homepage="https://huggingface.co/Bingsu/adetailer",
                hash="f02b8a23e6f12bd2c1b1f6714f66f984c728fa41ed749d033e7d6dea511ef70c",
                types=["ultralytics_bbox"],
                file_size=52026019,
            ),
            AIResourceModel(
                name="hand_yolov8s",
                url="https://huggingface.co/andrey18106/visionatrix_models/resolve/main/ultralytics/bbox/hand_yolov8s.pt",
                homepage="https://huggingface.co/Bingsu/adetailer",
                hash="5c4faf8d17286ace2c3d3346c6d0d4a0c8d62404955263a7ae95c1dd7eb877af",
                types=["ultralytics_bbox"],
                file_size=22507707,
            ),
            AIResourceModel(
                name="person_yolov8m-seg",
                url="https://huggingface.co/andrey18106/visionatrix_models/resolve/main/ultralytics/segm/person_yolov8m-seg.pt",
                homepage="https://huggingface.co/Bingsu/adetailer",
                hash="9d881ec50b831f546e37977081b18f4e3bf65664aec163f97a311b0955499795",
                types=["ultralytics_segm"],
                file_size=54827683,
            ),
        ],
    },
    "comfyui_ultimatesdupscale@1.1.2": {},
    "comfyui_instantid@1.0.0": {
        "models": [ANTELOPEV2],
    },
    "efficiency-nodes-comfyui@1.0.6": {},
    "comfyui-wd14-tagger@1.0.0": {},
    "comfyui-supir@1.0.1": {},
    "comfyui_essentials@1.1.0": {},
    "rgthree-comfy@1.0.0": {},
    "comfyui-custom-scripts@1.2.3": {},
    "comfyui_ipadapter_plus@2.0.0": {},
    "comfyui_controlnet_aux@1.0.7": {},
    "skimmed_cfg@1.0.0": {},
    "was-node-suite-comfyui@1.0.2": {},
    "comfyui-visionatrix@1.2.1": {},
    "comfyui-remotevae@1.0.0": {},
    "comfyui-gemini@1.0.4": {},
    "comfyui-ollama@2.0.1": {},
    "pulid_comfyui@1.0.1": {},
    "comfyui_pulid_flux_ll@1.1.4": {},
    "comfyui-inpaint-cropandstitch@2.1.3": {},
    "comfyui-videohelpersuite@1.5.18": {},
    "https://github.com/Fannovel16/ComfyUI-Frame-Interpolation": {},
    "comfyui-kjnodes@1.0.8": {},
    "comfyui_layerstyle@1.0.90": {},
    "comfyui-easy-use@1.2.9": {},
    "comfyui_birefnet_ll@1.1.1": {},
    "https://github.com/shiimizu/ComfyUI-PhotoMaker-Plus": {
        "models": [
            AIResourceModel(
                name="buffalo_l",
                filename="insightface/models/buffalo_l.zip",
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
                file_size=288621354,
            ),
        ],
    },
    "https://github.com/liusida/ComfyUI-AutoCropFaces": {},
    "https://github.com/kaibioinfo/ComfyUI_AdvancedRefluxControl": {},
    "https://github.com/FizzleDorf/ComfyUI_FizzNodes": {},
    "https://github.com/ZenAI-Vietnam/ComfyUI_InfiniteYou": {
        "models": [ANTELOPEV2],
    },
}
