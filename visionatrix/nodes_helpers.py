def get_node_value(node: dict, path: list[str]) -> str | int | float:
    for key in path:
        node = node[key]
    return node


def set_node_value(node: dict, path: list[str], value: str | int | float | list) -> None:
    for key in path[:-1]:
        node = node[key]
    if isinstance(path[-1], list):  # we need to set multiple values at once
        for i, k in enumerate(path[-1]):
            if isinstance(value, list | tuple):
                node[k] = value[i]
            else:
                node[k] = value
    else:
        node[path[-1]] = value
