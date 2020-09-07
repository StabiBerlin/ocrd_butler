#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys

import click
import yaml

from jinja2 import Environment, FileSystemLoader
from jinja2.runtime import Undefined


def is_base_pathname(path_args):
    """
    Check if its the base of a namespace.
    """
    return path_args.count("/") == 1


def get_namespace(path_args):
    """
    Return base name of the routes collection.
    """
    namespace = path_args[1:]
    if "/" in namespace:
        namespace = namespace[:namespace.find("/")]
    return "{0}".format(namespace)


def has_parameters(pathname):
    return "{" in pathname


def get_parameters(path_args):
    """
    Get the parameters in the given path.
    Replace "-" with "_" in parameters.
    """
    parameters = re.findall(r"\{(.*?)\}", path_args)
    return [p.replace("-", "_") for p in parameters]


def get_route(pathname):
    """
    /processor/{executable}/{job-id} -> "/<string:executable>/<string:job_id>"
    """
    if has_parameters(pathname):
        route = pathname[:pathname.find(("{"))][:-1]
        parameters = get_parameters(pathname)
        for parameter in parameters:
            route += "/<string:{0}>".format(parameter)
    else:
        route = pathname
    return route


def render_responses(responses):
    """
    Render the responses for the given path.
    TODO: Currently used for api doc, maybe rename.
    """
    result = {}
    if not isinstance(responses, Undefined):
        for code, response in responses.items():
            result[int(code)] = response["description"]
    return result.__str__()


def get_tag(tags, pathname):
    for tag in tags:
        if tag["name"] == get_namespace(pathname):
            return tag


@click.command()
@click.option("-y", "--yaml_file", default="openapi.yml",
              help="yaml file, default=openapi.yml")
@click.option("-t", "--template", default="./template.j2",
              help="template file, default=./template.j2")
@click.option("-f", "--filename", default="openapi.py",
              help="output filename, default=openapi.py")
@click.option("-d", "--dirname", default=".",
              help="output directory, default=.")
def main(yaml_file, template, filename, dirname):
    """
    Command line interface.
    """
    print("Render boilerplate from {0} to {1}/{2}".format(
        yaml_file, dirname, filename))

    if os.path.exists(dirname) is False:
        os.makedirs(dirname)

    WORKING_DIR = os.path.dirname(os.path.abspath(template))
    TEMPLATE_FILE = os.path.basename(template)
    print("* Template directory: " + WORKING_DIR)
    print("* Template Filename: " + TEMPLATE_FILE)

    # YAML file.
    with open(yaml_file, "r") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    # pp = pprint.PrettyPrinter(indent=1)
    # pp.pprint(data)

    with open(template) as t_fh:
        print("* Opening template file")
        content = t_fh.read()

    print("* Generate config from template " + template)

    env = Environment(loader=FileSystemLoader(WORKING_DIR),
                      trim_blocks=True,
                      lstrip_blocks=True)
    template = env.get_template(TEMPLATE_FILE)
    template.globals["render_responses"] = render_responses
    template.globals["get_namespace"] = get_namespace
    template.globals["is_base_pathname"] = is_base_pathname
    template.globals["get_route"] = get_route
    template.globals["get_parameters"] = get_parameters
    template.globals["has_parameters"] = has_parameters
    template.globals["get_tag"] = get_tag

    # Save output
    result_file = "{0}/{1}".format(dirname, filename)
    print("* Save output to " + result_file)
    with open(result_file, "w") as r_file:
        r_file.write(template.render(data))


if __name__ == "__main__":
    sys.exit(main())
