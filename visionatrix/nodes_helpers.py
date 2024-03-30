def get_node_value(node: dict, path: list[str]) -> str | int | float:
    for key in path:
        node = node[key]
    return node


def set_node_value(node: dict, path: list[str], value: str | int | float | list) -> None:
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
