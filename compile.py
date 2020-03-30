#!/usr/bin/env python3
import os
import sys
from argparse import ArgumentParser, Namespace
from typing import Iterable, List

from utils import ConfigItem, add_common_args, bash_call, call, config_logging
from utils import load_config as utils_load_config
from utils import logger


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Compile software projects according to config file"
    )
    add_common_args(parser)
    # In / Out
    parser.add_argument(
        "--config",
        "-c",
        help="Config file to use",
        metavar="YAML_FILE",
        default="config.yaml",
    )
    parser.add_argument(
        "--logs-dir",
        help="Directory for logs of build commands",
        default="logs/",
        type=os.path.abspath,
    )
    parser.add_argument(
        "-r", "--rebuild", help="Clean & rebuild everything", action="store_true"
    )
    # Steps
    clone_group = parser.add_mutually_exclusive_group()
    clone_group.add_argument(
        "--no-clone", help="Skip cloning phase", action="store_false", dest="clone"
    )
    clone_group.add_argument(
        "--clone-only", help="Clone repositories and exit", action="store_true"
    )

    return parser.parse_args()


def main(args: Namespace) -> int:
    config_logging(args)
    logger.debug(args)

    args.items = load_config(args)
    logger.debug("Got items: {}", args.items)
    if not args.items:
        logger.info("Nothing to do!")
        return 0

    if args.build_dir:
        os.makedirs(args.build_dir, exist_ok=True)
        os.chdir(args.build_dir)

    if args.clone:
        if not clone_all(args.items):
            return 1
        if args.clone_only:
            return 0

    successful = list(build_iter(args))
    if successful:
        # Items that succeeded this time should always be in done.log
        successful_urls = set(d["url"] for d in successful)
        # This that failed should always be removed from done.log
        failed = set(d["url"] for d in args.items) - successful_urls
        # All other should be preserved
        successful_urls.update(set(get_done("done.log")))
        # Order of operations matters here: First add old and new successes and then remove new failures
        successful_urls.difference_update(failed)
        with open("done.log", "w") as f:
            print("\n".join(sorted(successful_urls)), file=f)

    failures = len(args.items) - len(successful)
    if failures > 0 and args.exit_on_error:
        return 1
    return failures


def load_config(args: Namespace) -> List[ConfigItem]:
    if args.rebuild:
        done = []
    else:
        done = get_done(os.path.join(args.build_dir, "done.log"))
    return utils_load_config(args, skip_urls=done)


def get_done(file_name: str) -> List[str]:
    try:
        with open(os.path.join(file_name)) as f:
            return f.read().strip().split("\n")
    except FileNotFoundError:
        logger.debug("{} not found", file_name)
        return []


def clone_all(items):
    return sum(call(clone_cmd(d)) for d in items) == 0


def clone_cmd(d):
    depth = d.get("depth", 1)
    depth_s = f" --depth {depth}" if depth >= 1 else ""
    branch = d.get("branch")
    branch = f" --branch {branch} " if branch else ""

    return f"[[ -d {d['dir']} ]] || git clone {d['url']}{depth_s}{branch} {d['dir']}"


def build_iter(args: Namespace) -> Iterable[ConfigItem]:
    for d in args.items:
        ret = build(d, args)
        if ret == 0:
            logger.info("{} build success", d["dir"])
            yield d
        else:
            logger.error("Build failed: {} with code {}", d["dir"], ret)
            if args.exit_on_error:
                break


def build(d: ConfigItem, args: Namespace) -> int:
    logger.info("Building {}", d["dir"])

    cwd = d["dir"]
    if d["clean"]:
        call(d["clean"], cwd=cwd)

    log_dir = os.path.join(args.logs_dir, d["dir"], "")
    os.makedirs(log_dir, exist_ok=True)
    os.environ["LOG_DIR"] = log_dir
    return bash_call(d["build"], cwd=cwd, log=os.path.join(log_dir, "log"))


if __name__ == "__main__":
    sys.exit(main(parse_args()))
