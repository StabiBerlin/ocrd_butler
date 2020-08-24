from flask_nav import Nav
from flask_nav.elements import Navbar, View, Subgroup, Separator, Link

nav = Nav()

# registers the "top" menubar
nav.register_element('frontend_top', Navbar(
    View('Home', 'frontend.index'),
    View('Processors', 'processors_blueprint.processors'),
    View('Chains', 'chains_blueprint.chains'),
    View('Tasks', 'frontend.tasks'),
    Link('API', dest='/api'),
    Link('Queue Backend', dest='/flower/'),
))
