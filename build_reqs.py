#!/usr/bin/env python3
from argparse import ArgumentParser, Namespace

from utils import add_common_args, config_logging, load_config, logger


def main(args: Namespace):
    config_logging(args)
    logger.debug(args)

    if args.assume_supported:
        logger.info("Skipping /etc/lsb-release check")
    else:
        if not check_ubuntu():
            logger.error("Unsupported system")
            return 1

    for item in load_config(args):
        logger.debug(item)
        requirements = item.get("requirements")
        if requirements is None:
            logger.warning("Skipping {} as it has no 'requirements'", item["dir"])
            continue
        if isinstance(requirements, list):
            if requirements:
                print("apt-get install -qq", " ".join(requirements))
        else:
            for k, v in requirements.items():
                if k == "build-dep":
                    print("apt-get build-dep -qq", " ".join(v))
                elif k == "packages":
                    print("apt-get install -qq", " ".join(v))
                else:
                    logger.warning("Unknown key '{}' in requirements", k)

    return 0


def parse_args():
    parser = ArgumentParser(description="Print build requirements from config file")
    add_common_args(parser, config=True)
    parser.add_argument(
        "--assume-supported", help="Skip distro check", action="store_true",
    )

    return parser.parse_args()


def check_ubuntu() -> bool:
    try:
        with open("/etc/lsb-release") as f:
            has_id = False
            has_release = False
            for line in f:
                logger.debug(line)
                var, value = line.lower().strip().split("=", 1)
                if var == "distrib_id":
                    if value != "ubuntu":
                        logger.error("Unknown DISTRIB_ID {}", value)
                        return False
                    has_id = True
                elif var == "distrib_release":
                    major, _ = value.split(".", 1)
                    if int(major) < 18:
                        logger.error("Major release {} is too old", major)
                        return False
                    has_release = True
                if has_id and has_release:
                    return True
    except FileNotFoundError:
        logger.exception("/etc/lsb-release missing")
        return False


if __name__ == "__main__":
    import sys

    sys.exit(main(parse_args()))
