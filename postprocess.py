#!/usr/bin/env python3
import os
import sys
from argparse import ArgumentParser, ArgumentTypeError, Namespace, RawTextHelpFormatter
from functools import wraps
from operator import itemgetter

from utils import (
    add_common_args,
    arg_type_list,
    base_dir,
    call,
    check_exists,
    config_logging,
    logger,
    parallel,
    rglob,
)

STEP_MAP = {}


def main(args: Namespace) -> int:
    config_logging(args)
    logger.debug(args)

    os.chdir(args.build_dir)
    if args.bc_list is None:
        args.bc_list = rglob(".")
        args.bc_list = list(filter_bc_list(args))

    for step in args.steps:
        ret = STEP_MAP[step]["cb"](args)
        if ret > 0 and args.exit_on_error:
            return ret

    return 0


def filter_bc_list(args: Namespace):
    if args.whitelist:
        return filter(lambda x: base_dir(x) in args.whitelist, args.bc_list)
    if args.blacklist:
        return filter(lambda x: base_dir(x) not in args.blacklist, args.bc_list)
    return args.bc_list


def parse_args() -> Namespace:
    def check_steps(x):
        d = check_steps.__dict__
        prev = d.get("prev")
        if (x == "all" and prev) or (prev == "all"):
            raise ArgumentTypeError("No other steps possible if 'all' is specified")
        d["prev"] = x
        return x

    parser = ArgumentParser(
        description="Process bitcode files after compilation step",
        formatter_class=RawTextHelpFormatter,
    )
    add_common_args(parser)
    parser.add_argument(
        "steps",
        metavar="STEP",
        help="Steps to execute. Available options:\n"
        + "\n".join(
            [
                f"* {k:<7}: {v['help']}"
                for k, v in sorted(STEP_MAP.items(), key=itemgetter(0))
            ]
        ),
        nargs="+",
        choices=STEP_MAP.keys(),
        type=check_steps,
    )
    parser.add_argument(
        "--opt-levels",
        "-O",
        help="List of comma-separated optimization levels to use with 'opt' step. "
        "See clang/gcc -O option.",
        type=arg_type_list,
    )
    parser.add_argument("--opt-flags", default="", help="Extra flags to pass to opt")
    parser.add_argument(
        "--bc-list",
        nargs="+",
        help="List of bitcode files to post-process. "
        "If not specified, the script will run recursively on all bitcode files on the build dir.",
    )
    parser.add_argument("--postfix", help="Archive name postfix", default="")
    args = parser.parse_args()

    return args


def register_step(help_msg, requires=tuple()):
    def register(f):
        @wraps(f)
        def wrapper(args):
            # Check executable requirements
            for req in requires:
                assert check_exists(req), f"'{req}' is required for {name} step"

            # Save previous steps for 'archive' step's postfix
            if "prev_steps" not in args:
                args.prev_steps = args.postfix

            ret = f(args)
            args.prev_steps += f"-{name}"
            return ret

        name = f.__name__
        assert name.startswith("step_")
        name = name.replace("step_", "", 1)
        STEP_MAP[name] = {"cb": wrapper, "help": help_msg}
        return wrapper

    return register


@register_step("Put current state in archive", requires=["tar"])
def step_archive(args: Namespace) -> int:
    return call(
        ["tar", "czf", f"results{args.prev_steps}.tar.gz"]
        + sorted(set(base_dir(x) for x in args.bc_list)),
        shell=False,
    )


@register_step("Run 'opt -strip' on all .bc files", requires=["opt"])
def step_strip(args: Namespace) -> int:
    ret = parallel(f"opt {{}} -strip-debug -strip -o {{.}}-strip.bc", args.bc_list)
    if ret > 0 and args.exit_on_error:
        return ret
    args.bc_list = [os.path.splitext(x)[0] + "-strip.bc" for x in args.bc_list]
    return 0


@register_step("Run 'llvm-dis' on all .bc files", requires=["llvm-dis"])
def step_dis(args: Namespace) -> int:
    return parallel("llvm-dis", args.bc_list) + parallel("llvm-dis", args.opt_bc_list)


@register_step(
    "Run google/souper on all .bc files to get potential candidates",
    requires=["souper"],
)
def step_souper(args: Namespace) -> int:
    return parallel("souper {} > {.}.souper", args.bc_list)


@register_step(
    "Run optimizer for each optimization level. See --opt-levels.", requires=["opt"]
)
def step_opt(args: Namespace) -> int:
    args.opt_bc_list = []
    for opt in args.opt_levels or ["0"]:
        ret = parallel(
            f"timeout 1m opt {{}} -O{opt} {args.opt_flags} -o {{.}}-O{opt}.bc",
            args.bc_list,
        )
        if ret > 0 and args.exit_on_error:
            return ret
        args.opt_bc_list.extend(
            [os.path.splitext(x)[0] + f"-O{opt}.bc" for x in args.bc_list]
        )
    return 0


@register_step("Run all steps once")
def step_all(args: Namespace) -> int:
    for step in [step_strip, step_opt, step_dis, step_souper, step_archive]:
        ret = step(args)
        if ret > 0 and args.exit_on_error:
            return ret
    return 0


if __name__ == "__main__":
    sys.exit(main(parse_args()))
