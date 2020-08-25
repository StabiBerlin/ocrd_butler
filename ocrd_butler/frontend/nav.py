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
    View('Home', 'frontend.index'),
    View('Processors', 'processors_blueprint.processors'),
    View('Chains', 'chains_blueprint.chains'),
    View('Tasks', 'tasks_blueprint.tasks'),
    Link('API', dest='/api'),
    Link('Queue Backend', dest='/flower/'),
))
