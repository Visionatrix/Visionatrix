import os
import sys
from datetime import datetime

import sphinx_rtd_theme

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.abspath(dir_path + "/_ext"))
sys.path.insert(0, os.path.abspath("../."))

import visionatrix  # noqa

now = datetime.now()

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_inline_tabs",
    "sphinx_issues",
    "sphinx_rtd_theme",
    "sphinxcontrib.autodoc_pydantic",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

autodoc_pydantic_model_show_json = False

# General information about the project.
project = "Visionatrix"
copyright = str(now.year) + f" {project} Authors"  # noqa

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = visionatrix.__version__
release = version

html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

html_logo = "resources/logo.svg"

html_theme_options = {
    "display_version": True,
    "logo_only": True,
}

# If true, `todos` produce output. Else they produce nothing.
todo_include_todos = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# If true, Sphinx will warn about all references where the target cannot be found.
# Default is False. You can activate this mode temporarily using the -n command-line
# switch.
nitpicky = True
nitpick_ignore_regex = [
    (r"py:class", r"starlette\.requests\.Request"),
    (r"py:class", r"starlette\.requests\.HTTPConnection"),
    (r"py:class", r"ComputedFieldInfo"),
    (r"py:.*", r"httpx.*"),
]

autodoc_member_order = "bysource"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["resources"]


def setup(app):
    app.add_js_file("js/script.js")
    app.add_css_file("css/styles.css")
    app.add_css_file("css/dark.css")
    app.add_css_file("css/light.css")


issues_github_path = "Visionatrix/Visionatrix"
