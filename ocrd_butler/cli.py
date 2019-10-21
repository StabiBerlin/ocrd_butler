# -*- coding: utf-8 -*-

"""Console script for ocrd_butler."""
import sys
import click


@click.command()
def main(args=None):
    """Console script for ocrd_butler."""
    click.echo("Replace this message by putting your code into "
               "ocrd_butler.cli.main")
    click.echo("See click documentation at http://click.pocoo.org/")
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
