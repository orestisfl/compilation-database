import os
import re
import shutil
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from subprocess import PIPE, Popen, run
from typing import Any, Dict, Hashable, Iterable, List, Type, Union

import yaml
from loguru import logger

ConfigItem = Dict[Hashable, Any]


def add_common_args(argument_parser: ArgumentParser, config=False):
    log_group = argument_parser.add_mutually_exclusive_group()
    log_group.add_argument(
        "--verbose", "-v", help="Verbose log level", action="store_true"
    )
    log_group.add_argument("--quiet", "-q", help="Quiet log level", action="store_true")
    argument_parser.add_argument(
        "--build-dir",
        "-d",
        help="Where cloned projects and build files are stored",
        metavar="DIR",
        default="build/",
    )
    argument_parser.add_argument(
        "-e",
        "--exit-on-error",
        help="If any step fails, exit immediately",
        action="store_true",
    )
    black_white_group = argument_parser.add_mutually_exclusive_group()
    black_white_group.add_argument(
        "--whitelist", type=arg_type_list, help="Only process specifically these items"
    )
    black_white_group.add_argument(
        "--blacklist", type=arg_type_list, help="Exclude processing these items"
    )
    if config:
        argument_parser.add_argument(
            "--config",
            "-c",
            help="Config file to use",
            metavar="YAML_FILE",
            default="config.yaml",
        )


def arg_type_list(s: str, element_type: Type = str) -> List[Any]:
    return list(map(element_type, s.split(",")))


def config_logging(args: Namespace):
    level = "INFO"
    if args.verbose:
        level = "DEBUG"
    elif args.quiet:
        level = "WARNING"
    logger.remove()
    logger.add(sys.stderr, level=level)
    logger.debug("Logging configuration done")


def load_config(args: Namespace, skip_urls=tuple()) -> List[ConfigItem]:
    return list(
        filter(
            lambda d: (d["url"] not in skip_urls)
            and (not args.whitelist or d["dir"] in args.whitelist)
            and (not args.blacklist or d["dir"] not in args.blacklist),
            map(complete_item_defaults, _yaml_load(args.config)),
        ),
    )


def complete_item_defaults(d: ConfigItem) -> ConfigItem:
    assert all(key in d for key in ["url", "build"])

    if "dir" not in d:
        d["dir"] = _get_dirname(d["url"])

    d.setdefault("clean", "git reset --hard && git clean -fdx .")

    return d


GITHUB_REGEXPS = [
    re.compile(r"github.com/(.+)/(.+)(?:\.git)"),
    re.compile(r"github.com/(.+)/(.+)"),
    re.compile(r"github.com:(.+)/(.+).git"),
]


def _get_dirname(url: str) -> str:
    result = None
    for pattern in GITHUB_REGEXPS:
        result = pattern.search(url)
        if result:
            return result.groups()[1].rstrip("/")
    assert result, "URL matches GitHub patterns"


def rglob(dirname: str, pattern: str = "*.bc") -> List[str]:
    return list(map(str, Path(dirname).rglob(pattern)))


def bash_call(script, e=True, x=True, **kwargs):
    assert isinstance(script, str)

    cmd = ["bash"]
    if e:
        cmd += ["-e"]
    if x:
        cmd += ["-x"]
    cmd += ["-c", script]

    return call(cmd, shell=False, **kwargs)


def call(cmd, echo: bool = False, log: str = None, **kwargs) -> int:
    if echo:
        print(cmd, kwargs)
        return 0

    kwargs.setdefault("shell", True)
    if kwargs["shell"]:
        kwargs.setdefault("executable", "/bin/bash")

    a = b = None
    if log:
        a = kwargs["stdout"] = open(f"{log}.stdout.log", "w")
        b = kwargs["stderr"] = open(f"{log}.stderr.log", "w")

    logger.debug(cmd)
    ret = run(cmd, **kwargs).returncode

    if log:
        a.close()
        b.close()

    return ret


def parallel(cmd: str, file_list: Union[str, Iterable], **kwargs):
    if not isinstance(file_list, str):
        file_list = "\n".join(file_list)

    logger.opt(lazy=True).debug(
        "Parallel '{}' with {} files", cmd.__str__, lambda: file_list.count("\n") + 1
    )

    p = Popen(["parallel", cmd], stdin=PIPE, **kwargs)
    # noinspection PyTypeChecker
    p.communicate(bytes(file_list, "utf-8"))
    return p.returncode


def check_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def base_dir(file_name: os.PathLike) -> str:
    return str(os.path.normpath(file_name)).split(os.path.sep, 1)[0]


def _yaml_load(file_name: os.PathLike) -> List[ConfigItem]:
    with open(file_name) as f:
        return yaml.load(f, Loader=yaml.FullLoader)
