Vix Workflows
=============

Introduction
""""""""""""

ComfyUI workflows are designed for developers and those interested in diffusion processes.

Visionatrix workflows are created on top of ComfyUI workflows for easy deployment and straightforward use.

Currently, there are two main issues with using ComfyUI flows for the general public:

    1. It's unclear where to get the model from and how to deploy/install it – a **deployment/installation issue**
    2. Without some experience, it's unclear how to just provide inputs to simple get results - a **usability issue**

Automatic models mapping
""""""""""""""""""""""""

To address the first issue with model mapping, Visionatrix includes a `models_catalog.json <https://github.com/Visionatrix/Visionatrix/blob/main/flows/models_catalog.json>`_ file.

By default, it is taken and updated from the Visionatrix repository on GitHub, in case you add a new flow and need to add new model mappings you can change its path using an environment variable to a local file path.

.. note::

    We hope that after you add something locally, you will open a pull request so that the community can benefit from it.

The file structure consists of a set of objects, each describing a ComfyUI Node class that loads or uses a model.

.. code-block:: python

    "InstantID-ControlNet": {
        "regexes": [
        {
          "class_name": "ControlNetLoader",
          "input_value": "^(?=.*(?i:instantid)).*"
        }
      ],
      "save_path": "controlnet/instantid-controlnet.safetensors",
      "url": "https://huggingface.co/InstantX/InstantID/resolve/main/ControlNetModel/diffusion_pytorch_model.safetensors",
      "homepage": "https://huggingface.co/InstantX/InstantID",
      "hash": "c8127be9f174101ebdafee9964d856b49b634435cf6daa396d3f593cf0bbbb05"
      }

"regexes"
'''''''''

Regexes are used to understand the if this record related to the specified model from the ComfyUI workflow.

``"input_name"``, ``"class_name"``, and ``"input_value"`` are supported, both together and separately.

.. note::

    If these conditions prove insufficient, please create an issue and we will find a solution together.

"save_path"
'''''''''''

Specifies where the model will be saved.
Default paths are relative to the root of the external models folder specified in the ComfyUI file `"extra_model_paths.yaml"`

By default in Visionatrix, this is the path to the `"vix_models"` folder.

If a Node does not support ComfyUI's model placement configurations and requires them to be located only in the ComfyUI folder, the entry may take the form:

.. code-block::

    save_path="{root}models/insightface/models/antelopev2.zip"

"url"
'''''

Indicates where to download the model from if it is not already present.

It is preferable for the model to be hosted on Hugging Face, but "civitai.com" is also supported.

"homepage"
''''''''''

An optional field with a link to the model's home page where you can view the license.

"hash"
''''''

The SHA256 hash of the model. Used to verify the integrity of the model and check for download errors.

Vix workflow overview
"""""""""""""""""""""

Visionatrix workflows consist of two files: ``flow.json`` and ``flow_comfy.json``

The main purpose of a Vix Flow is to specify how to map incoming parameters to the ComfyUI workflow for the creation endpoint of a ComfyUI task.

.. note::

    The main difference between Visionatrix and ComfyUI: A task is created with a single request, which includes both incoming text parameters and input files.

Consider the example of the VintagePortrait Vix flow:

.. code-block:: json

    {
      "name": "vintage_portrait",
      "display_name": "Vintage Portrait",
      "description": "Portrait photos in Vintage styles",
      "author": "bigcat88",
      "homepage": "https://github.com/bigcat88",
      "license": "",
      "documentation": "https://visionatrix.github.io/Visionatrix/Flows/VintagePortrait.html",
      "input_params": [
        {
          "name": "image",
          "display_name": "Person's face",
          "type": "image",
          "optional": false,
          "comfy_node_id": {
            "37": {
              "dest_field_name": ["inputs", "image"]
            }
          }
        },
        {
          "name": "prompt",
          "display_name": "Prompt",
          "type": "text",
          "optional": false,
          "advanced": false,
          "comfy_node_id": {
            "29": {
              "dest_field_name": ["inputs", "positive"]
            }
          }
        },
        {
          "name": "pose",
          "display_name": "Person's face pose",
          "type": "image",
          "optional": true,
          "advanced": true,
          "comfy_node_id": {
            "44": {
              "dest_field_name": ["inputs", "image"],
              "node_connect": {
                "node_id": "33",
                "dest_field_name": ["inputs", "image_kps"]
              }
            }
          }
        }
      ]
    }

"name"
''''''

The name of the workflow. It usually matches the name of the folder where the flow is stored.

"display_name"
''''''''''''''

Used in the UI to display the name of the flow.

"description"
'''''''''''''

A brief description of the flow for user display.

"author"
''''''''

The name of the ComfyUI flow author or the Visionatrix flow author.

"homepage"
''''''''''

A link that will open when clicking on the flow author's name.

"license"
'''''''''

The general license under which the flow can be used (to simplify understanding whether it can be used behind the API service, whether it can be used commercially, etc.)

"documentation"
'''''''''''''''

Link to additional information about the flow.

"input_params"
''''''''''''''

The most important part. Based on the information from this field, the Visionatrix UI dynamically displays the interface.

The backend part fills in the ComfyUI workflow based on these data.

Technically, this is a list of objects, where each object is one input parameter, which includes:

 * "name" - the key(used only when `"type"` is equal to `"text"`)
 * "display_name" - the name of the parameter displayed in the UI
 * "type" - a string that can have values: `"text"` or `"image"`

    .. note::
        `"video"` and `"audio"` types will be added as soon as there is the first Workflow requiring it.

 * "optional" - indicates whether the parameter is optional. If an optional field is not provided, the backend will fill it in automatically.
 * "advanced" - used only in the UI, shows whether the field should be hidden by default (we do not want to overload the interface for regular users)
 * "default" - the field value to initiate.

    .. note::
        Used for both UI and backend, but not mandatory even for optional fields (as in the ComfyUI flow, the Node value is still set)

 * "comfy_node_id" - a field only for the backend, which defines what to do with this value (where to use it in the ComfyUI Flow)


Create task based on Flow
"""""""""""""""""""""""""


.. code-block:: python

    @APP.post("/task")
    async def task_run(
        request: Request,
        name: str = Form(description="Name of the flow from which the task should be created"),
        count: int = Form(1, description="Number of tasks to be created"),
        input_params: str = Form(None, description="List of input parameters as an encoded json string"),
        files: list[UploadFile | str] = Form(None, description="List of input files for flow"),  # noqa
    ) -> TaskRunResults:
        """
        Endpoint to initiate the creation and execution of tasks within the Vix workflow environment,
        handling both file inputs and task-related parameters.
        """
        pass


.. warning::

    It's important to note that text parameters and files are passed in different parameters:

        * input_params - input parameters with "type" == "text"
        * files - list of input files (files should be in the order they are defined in the Vix Flow)

When this endpoint is called, a task will be created and queued for execution.

*To be continued...*
