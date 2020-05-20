#!/usr/bin/env python3
import sys
from argparse import ArgumentParser, Namespace

import yaml

from utils import ConfigItem, add_common_args, load_config


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Compile software projects according to config file"
    )
    add_common_args(parser, config=True)

    parser.add_argument("--target", default=".github/workflows/main.yml")

    return parser.parse_args()


def main(args: Namespace) -> int:
    idx, lines = find_in_config(args.target)
    replacement = yaml.dump(
        [item["dir"] for item in load_config(args)], default_flow_style=True
    ).strip()
    with open(args.target, "w") as f:
        indent = 0
        while lines[idx][indent] == " ":
            indent += 1

        lines[idx] = " " * indent + "config_targets: " + replacement + "\n"
        print("".join(lines), file=f)

    return 0


def find_in_config(fname):
    with open(fname) as f:
        lines = [line for line in f]
    for idx, line in enumerate(map(str.strip, lines)):
        if line.startswith("config_targets: ["):
            return idx, lines
    raise RuntimeError("Could not find config_targets")


if __name__ == "__main__":
    sys.exit(main(parse_args()))
