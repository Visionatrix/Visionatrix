from .pydantic_models import UserInfo


def init_new_task_details(task_id: int, name: str, input_params: dict, user_info: UserInfo) -> dict:
    return {
        "task_id": task_id,
        "name": name,
        "input_params": input_params,
        "progress": 0.0,
        "error": "",
        "outputs": [],
        "input_files": [],
        "flow_comfy": {},
        "user_id": user_info.user_id,
        "execution_time": 0.0,
    }
