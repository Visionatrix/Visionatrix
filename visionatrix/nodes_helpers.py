import contextlib


def get_node_value(node: dict, path: list[str]) -> str | int | float | None:
    with contextlib.suppress(Exception):
        for key in path:
            node = node[key]
        return node
    return None


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


def remove_node_from_comfy_flow(node_id: str, flow_comfy: dict[str, dict]) -> None:
    """Removes a single node from the ComfyUI graph, re-linking its children to its parents so that
    the flow bypasses 'node_id'.

    The logic assumes at most one parent for each input name in 'node_id', and any number of children
    that reference 'node_id'. Each child input referencing 'node_id' is replaced with references
    to 'node_id's parent(s).

    If no child or parent is found, the node is simply removed.
    """

    if node_id not in flow_comfy:
        return

    # 1) Identify 'node_id's parents: for each input in 'node_id', we have something like:
    #    node_details["inputs"][some_input] == [parent_id, port_index]
    #    We'll store them in parent_map: {input_name: (parent_id, parent_port_index)}
    node_details = flow_comfy[node_id]
    parent_map = {}  # key=input_name, value=(parent_id, parent_port_index)
    for inp_name, inp_val in node_details.get("inputs", {}).items():
        if isinstance(inp_val, list) and len(inp_val) == 2 and isinstance(inp_val[0], str):
            # e.g. ["12", 0]
            parent_map[inp_name] = (inp_val[0], inp_val[1])

    # 2) Find children referencing 'node_id': i.e. any node in flow_comfy that has an input of the form:
    #    child_details["inputs"][some_input] == [node_id, port_index]
    #    We'll store them in a list for re-linking:  child_map -> list of (child_id, child_input_name, child_port_index)
    child_map = []
    for other_id, other_details in flow_comfy.items():
        if other_id == node_id:
            continue
        for inp_name, inp_val in other_details.get("inputs", {}).items():
            if isinstance(inp_val, list) and len(inp_val) == 2 and inp_val[0] == node_id:
                child_map.append((other_id, inp_name, inp_val[1]))

    # 3) For each child referencing node_id, we must re-link that child's input(s) to node_id's parents.
    #    If node_id has multiple parents, or if child references node_id for multiple inputs,
    #    you might decide how to handle that.  Here we do a simpler approach:
    #
    #    - We assume node_id typically has the same "port count" as the child's reference
    #    - We pick the relevant parent for the child's port index if it matches an input in node_id.
    for child_id, child_input_name, child_port_index in child_map:
        child_details = flow_comfy[child_id]

        # Attempt to find a matching parent by searching parent_map's port indexes.
        matched_parent_id = None
        matched_port_index = None
        for _, (p_id, p_port_index) in parent_map.items():
            if p_port_index == child_port_index:
                matched_parent_id = p_id
                matched_port_index = p_port_index
                break

        if matched_parent_id is None:
            # If we cannot match by port index, pick the first parent in parent_map or do nothing
            if parent_map:
                # Just take the first parent's ID/port
                matched_parent_id, matched_port_index = next(iter(parent_map.values()))
            else:
                # No parent found; child will end up disconnected from the graph
                child_details["inputs"][child_input_name] = None
                continue

        # Re-link the child's input to the matched parent's ID/port
        child_details["inputs"][child_input_name] = [matched_parent_id, matched_port_index]

    flow_comfy.pop(node_id, None)
