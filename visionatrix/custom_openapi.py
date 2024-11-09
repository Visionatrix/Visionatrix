import hashlib
import re
from typing import Annotated

from fastapi import FastAPI, Form, UploadFile
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute, BaseRoute
from pydantic import BaseModel, Field, create_model

from . import _version
from .flows import (
    SUPPORTED_FILE_TYPES_INPUTS,
    SUPPORTED_TEXT_TYPES_INPUTS,
    get_available_flows,
    get_installed_flows,
)
from .pydantic_models import (
    Flow,
    TaskCreationBasicParams,
    TaskCreationWithCountAndSeedParams,
    TaskCreationWithCountParam,
    TaskCreationWithFullParams,
    TaskCreationWithSeedParam,
    TaskCreationWithTranslateAndCountParams,
    TaskCreationWithTranslateAndSeedParams,
    TaskCreationWithTranslateParam,
    TaskRunResults,
)

TASK_CREATE_ROUTE = "/api/tasks/create/"
INTEGRATIONS_TASKS_PATTERN = re.compile(rf"^{TASK_CREATE_ROUTE}(?P<name>[\w\-]+)$")


def update_tasks_integrations_routes(app: FastAPI, flows_definitions: dict[str, Flow]) -> bool:
    existing_routes = set()
    routes_to_remove = []
    updated = False

    for route in app.routes:
        if isinstance(route, APIRoute):
            match = INTEGRATIONS_TASKS_PATTERN.match(route.path)
            if match:
                flow_name = match.group("name")
                if flow_name in flows_definitions:
                    existing_routes.add(flow_name)
                else:
                    routes_to_remove.append(route)

    for route in routes_to_remove:
        app.routes.remove(route)
        updated = True

    for flow_name, flow_definition in flows_definitions.items():
        if flow_name not in existing_routes:
            app.add_api_route(
                f"{TASK_CREATE_ROUTE}{flow_name}",
                create_dynamic_route(flow_definition),
                methods=["PUT"],
                name=f"run_{flow_name}",
                tags=["integrations"],
            )
            updated = True
    return updated


def create_dynamic_model(flow_definition: Flow) -> type[BaseModel]:
    model_fields = {}
    for param in flow_definition.input_params:
        d_name = param["display_name"]
        if param.get("default"):
            default = param["default"]
        elif param["optional"]:
            default = None
        else:
            default = ...
        if param["type"] == "bool":
            model_field = (bool, Field(default, description=d_name))
        elif param["type"] == "list":
            model_field = (str, Field(default, description=d_name, json_schema_extra={"enum": list(param["options"])}))
        elif param["type"] == "range":
            model_field = (
                float,
                Field(default, description=d_name, ge=param["min"], le=param["max"], multiple_of=param["step"]),
            )
        elif param["type"] in SUPPORTED_TEXT_TYPES_INPUTS:
            model_field = (str, Field(default, description=d_name))
        elif param["type"] in SUPPORTED_FILE_TYPES_INPUTS:
            if param["type"] in ("image", "image-mask"):
                model_field = (
                    UploadFile | str,
                    Field(default, description=d_name, json_schema_extra={"contentMediaType": "image/*"}),
                )
            elif param["type"] == "video":
                model_field = (
                    UploadFile | str,
                    Field(default, description=d_name, json_schema_extra={"contentMediaType": "video/*"}),
                )
            else:
                model_field = (UploadFile | str, Field(default, description=d_name))
        else:
            raise RuntimeError(
                f"Flow {flow_definition.name}: unsupported input type '{param['type']}' for {param['name']} parameter"
            )
        model_fields[param["name"]] = model_field

    if (
        flow_definition.is_count_supported
        and flow_definition.is_translations_supported
        and flow_definition.is_seed_supported
    ):
        base_model = TaskCreationWithFullParams
    elif flow_definition.is_count_supported and flow_definition.is_seed_supported:
        base_model = TaskCreationWithCountAndSeedParams
    elif flow_definition.is_count_supported and flow_definition.is_translations_supported:
        base_model = TaskCreationWithTranslateAndCountParams
    elif flow_definition.is_translations_supported and flow_definition.is_seed_supported:
        base_model = TaskCreationWithTranslateAndSeedParams
    elif flow_definition.is_translations_supported:
        base_model = TaskCreationWithTranslateParam
    elif flow_definition.is_count_supported:
        base_model = TaskCreationWithCountParam
    elif flow_definition.is_seed_supported:
        base_model = TaskCreationWithSeedParam
    else:
        base_model = TaskCreationBasicParams

    return create_model(f"TaskRun_{flow_definition.name}", **model_fields, __base__=base_model)


def create_dynamic_route(flow_definition: Flow):
    route_data_model = create_dynamic_model(flow_definition)

    async def dynamic_route(_data: Annotated[route_data_model, Form()]) -> TaskRunResults:
        pass

    return dynamic_route


def generate_openapi(app: FastAPI, available: bool, installed: bool, only_flows: bool = False):
    flows_definitions = {}
    if available:
        flows_definitions.update(get_available_flows())
    if installed:
        flows_definitions.update(get_installed_flows())
    update_tasks_integrations_routes(app, flows_definitions)

    if only_flows:
        filtered_routes = []
        for route in app.routes:
            if (
                isinstance(route, APIRoute)
                and route.path.startswith(TASK_CREATE_ROUTE)
                and not route.path.endswith("{name}")
            ):
                filtered_routes.append(route)
    else:
        filtered_routes = app.routes

    routes_signature = compute_routes_signature(filtered_routes)
    cache_key = (routes_signature, only_flows)

    if not hasattr(app, "openapi_schemas"):
        app.openapi_schemas = {}

    if cache_key in app.openapi_schemas:
        return app.openapi_schemas[cache_key]

    openapi_schema = get_openapi(
        title="visionatrix",
        version=_version.__version__,
        routes=filtered_routes,
    )

    openapi_schema["servers"] = [{"url": "http://localhost:8288", "description": "Default server running Visionatrix"}]

    for path, methods in openapi_schema["paths"].items():
        if not str(path).startswith(TASK_CREATE_ROUTE):
            continue
        for method, details in methods.items():
            if str(method).lower() in ("post", "put") and "requestBody" in details:
                content_type = details["requestBody"]["content"]
                if "application/x-www-form-urlencoded" in content_type and "multipart/form-data" not in content_type:
                    form_data_schema = content_type["application/x-www-form-urlencoded"]["schema"]
                    content_type.pop("application/x-www-form-urlencoded")
                    content_type["multipart/form-data"] = {"schema": form_data_schema}

    app.openapi_schemas[cache_key] = openapi_schema
    if not only_flows:
        app.openapi_schema = openapi_schema
    return openapi_schema


def compute_routes_signature(routes: list[BaseRoute]) -> str:
    route_ids = []
    for route in routes:
        if isinstance(route, APIRoute):
            methods = ",".join(sorted(route.methods or []))
            route_ids.append(f"{route.path}:{methods}")
    route_ids_str = ";".join(route_ids)
    return hashlib.md5(route_ids_str.encode("utf-8")).hexdigest()
