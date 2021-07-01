"""
Register the top menu for the frontend.
"""

from flask_nav import Nav
from flask_nav.elements import (
    Navbar,
    View,
    Link
)

nav = Nav()
nav.register_element('frontend_top', Navbar(
    View('Home', 'frontend_blueprint.index'),
    View('Processors', 'processors_blueprint.processors'),
    View('Workflows', 'workflows_blueprint.workflows'),
    View('Tasks', 'tasks_blueprint.tasks'),
    View('Compare', 'compare_blueprint.compare'),
    Link('API', dest='/api'),
    Link('Queue Backend', dest='/flower/'),
))
