import argparse
import sys
import configparser
from lndlnurl import LndLnurl

config = configparser.ConfigParser()


def main():
    argument_parser = get_argument_parser()
    arguments = argument_parser.parse_args()
    try:
        with open(arguments.configfile) as f:
            config.read_file(f)
    except IOError:
        raise ValueError('No configuration found')
    return LndLnurl(config, arguments).run()

def get_argument_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        dest="LNURL",
        help="The LNURL to parse",
    )
    parser.add_argument(
        "--config",
        "-c",
        default="lndlnurl.conf",
        dest="configfile",
        help="location of configuration file"
    )
    return parser

try:
    success = main()
except Exception as e:
    print("Error: %s" % e)
