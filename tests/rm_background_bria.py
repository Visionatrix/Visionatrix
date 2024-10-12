import os
import subprocess
import tempfile
import time
import httpx
import sys
from PIL import Image, ImageMath

# URLs to download images
IMAGE_URLS = [
    "https://github.com/Visionatrix/VixFlowsDocs/blob/main/tests_data/source-cube_rm_background.png?raw=true",
    "https://github.com/Visionatrix/VixFlowsDocs/blob/main/tests_data/result-cube_rm_background.png?raw=true"
]

# Visionatrix details
VISIONATRIX_HOST = "http://127.0.0.1:8288"
CREATE_TASK_ENDPOINT = "/api/tasks/create"
GET_TASK_PROGRESS_ENDPOINT = "/api/tasks/progress"
GET_TASK_RESULTS_ENDPOINT = "/api/tasks/results"
WHOAMI_ENDPOINT = "/api/other/whoami"
FLOW_NAME = "remove_background_bria"
POLLING_INTERVAL = 3  # Poll every 3 seconds
MAX_WAIT_TIME = 300  # Wait up to 5 minutes for the server to be ready


def download_images(temp_dir):
    """Download the source and result images to the temporary directory."""
    downloaded_files = []
    for url in IMAGE_URLS:
        file_name = os.path.join(temp_dir, url.split("/")[-1].split("?")[0])
        print(f"Downloading {url} to {file_name}")
        with httpx.stream("GET", url, follow_redirects=True) as r:
            r.raise_for_status()
            with open(file_name, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
        downloaded_files.append(file_name)
    return downloaded_files


def install_flow():
    """Install the specified flow in Visionatrix."""
    print("Installing flow...")
    result = subprocess.run(
        [sys.executable, "-m", "visionatrix", "install-flow", f"--name={FLOW_NAME}"],
        check=False,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise Exception(f"Flow installation failed: {result.stderr}")
    print("Flow installation output:", result.stdout)


def run_visionatrix():
    """Start Visionatrix in the background and wait until it's ready to accept requests."""
    print("Starting Visionatrix...")
    subprocess.Popen([sys.executable, "-m", "visionatrix", "run", "--cpu"])

    # Poll the "whoami" endpoint to check if the server is ready
    wait_until_server_ready()


def wait_until_server_ready():
    """Poll the whoami endpoint until the server is ready, or timeout after MAX_WAIT_TIME."""
    print("Waiting for Visionatrix server to be ready...")
    whoami_url = f"{VISIONATRIX_HOST}{WHOAMI_ENDPOINT}"
    start_time = time.time()

    while time.time() - start_time < MAX_WAIT_TIME:
        try:
            response = httpx.get(whoami_url)
            if response.status_code == 200:
                print("Visionatrix server is ready!")
                return
        except httpx.RequestError:
            pass  # Ignore errors and continue polling
        time.sleep(POLLING_INTERVAL)

    raise Exception("Visionatrix server did not become ready within the maximum wait time.")


def create_task(image_file):
    """Call the create_task endpoint to process the image and return the task ID."""
    print("Creating task...")
    task_url = f"{VISIONATRIX_HOST}{CREATE_TASK_ENDPOINT}"
    files = {"files": (os.path.basename(image_file), open(image_file, "rb"))}  # noqa
    data = {
        "name": FLOW_NAME
    }
    response = httpx.put(task_url, data=data, files=files)
    if response.status_code != 200:
        raise Exception(f"Failed to create task: {response.status_code}, {response.text}")
    result = response.json()
    task_id = result["tasks_ids"][0]
    print(f"Task created with ID: {task_id}")
    return task_id


def get_task_progress(task_id):
    """Poll the get_tasks_progress endpoint and return the task's progress and node_id."""
    print(f"Checking progress for task ID: {task_id}")
    progress_url = f"{VISIONATRIX_HOST}{GET_TASK_PROGRESS_ENDPOINT}/{task_id}"
    response = httpx.get(progress_url)
    if response.status_code != 200:
        raise Exception(f"Failed to get task progress: {response.status_code}, {response.text}")

    result = response.json()
    if result.get("error"):
        raise Exception(f"Task {task_id} failed with error: {result['error']}")

    progress = result["progress"]
    node_id = result["outputs"][0]["comfy_node_id"]  # Assuming the first output node is the one we need
    print(f"Task {task_id} progress: {progress}% (node_id: {node_id})")
    return progress, node_id


def wait_for_task_completion(task_id):
    """Wait until the task progress reaches 100% or timeout after MAX_WAIT_TIME. Returns node_id."""
    print(f"Waiting for task {task_id} to complete (Max wait time: {MAX_WAIT_TIME} seconds)...")
    start_time = time.time()

    while time.time() - start_time < MAX_WAIT_TIME:
        try:
            progress, node_id = get_task_progress(task_id)
            if progress >= 100:
                print(f"Task {task_id} completed!")
                return node_id
        except Exception as e:
            print(f"Error encountered: {e}")
            raise e  # Raise the error after printing

        time.sleep(POLLING_INTERVAL)

    raise Exception(f"Task {task_id} did not complete within the maximum wait time of {MAX_WAIT_TIME} seconds.")


def download_result(task_id, node_id, temp_dir):
    """Download the result file for the completed task using the specified node_id."""
    print(f"Downloading result for task ID: {task_id}, node_id: {node_id}")
    result_url = f"{VISIONATRIX_HOST}{GET_TASK_RESULTS_ENDPOINT}"
    params = {"task_id": task_id, "node_id": node_id, "batch_index": 0}
    response = httpx.get(result_url, params=params)
    if response.status_code != 200:
        raise Exception(f"Failed to download task result: {response.status_code}, {response.text}")

    result_path = os.path.join(temp_dir, f"result_task_{task_id}_node_{node_id}.png")
    with open(result_path, "wb") as f:
        f.write(response.content)
    print(f"Result saved to {result_path}")
    return result_path


def compare_images(result_path, reference_path):
    """Compare the result image with the reference image."""
    print("Comparing images...")
    result_image = Image.open(result_path)
    reference_image = Image.open(reference_path)
    assert_image_similar(result_image, reference_image, epsilon=0.000012)
    print("Test passed!")


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Step 1: Download images
        downloaded_files = download_images(temp_dir)
        source_image = downloaded_files[0]  # Use the first image as source
        reference_image = downloaded_files[1]  # Use the second image for comparison

        # Step 2: Install the flow
        install_flow()

        # Step 3: Start Visionatrix and wait for it to be ready
        run_visionatrix()

        # Step 4: Create the task
        task_id = create_task(source_image)

        # Step 5: Wait for task completion and get node_id
        node_id = wait_for_task_completion(task_id)

        # Step 6: Download result and compare with reference
        result_path = download_result(task_id, node_id, temp_dir)
        compare_images(result_path, reference_image)


"""Helpers functions"""


def convert_to_comparable(a, b):
    new_a, new_b = a, b
    if a.mode == "P":
        new_a = Image.new("L", a.size)
        new_b = Image.new("L", b.size)
        new_a.putdata(a.getdata())
        new_b.putdata(b.getdata())
    elif a.mode == "I;16":
        new_a = a.convert("I")
        new_b = b.convert("I")
    return new_a, new_b


def assert_image_similar(a, b, epsilon=0.0):
    assert a.mode == b.mode
    assert a.size == b.size
    a, b = convert_to_comparable(a, b)
    diff = 0
    for ach, bch in zip(a.split(), b.split(), strict=False):
        ch_diff = ImageMath.eval("abs(a - b)", a=ach, b=bch).convert("L")
        diff += sum(i * num for i, num in enumerate(ch_diff.histogram()))
    ave_diff = diff / (a.size[0] * a.size[1])
    print(f"epsilon={epsilon}, ave_diff={ave_diff}")
    assert epsilon >= ave_diff


if __name__ == "__main__":
    main()
