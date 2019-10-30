from flask_nav import Nav
from flask_nav.elements import Navbar, View, Subgroup, Separator, Link

nav = Nav()

# registers the "top" menubar
nav.register_element('frontend_top', Navbar(
    View('Home', 'frontend.index'),
    View('Processors', 'frontend.processors'),
    View('Chains', 'frontend.chains'),
    # Subgroup(
    #     'Products',
    #     View('Wg240-Series', 'products', product='wg240'),
    #     View('Wg250-Series', 'products', product='wg250'),
    #     Separator(),
    #     View('Wg10X', 'products', product='wg10x'),
    # ),
    # Link('Tech Support', dest='http://techsupport.invalid/widgits_inc'),
))
