# Script and compilation database for popular C software

## Installation

For the python scripts, you need to run `pip -r requirements.txt`.
Then, you need to install all the dependencies needed by the config file.

## Usage

Please see [config.yaml](config.yaml) for example configuration.
Currently, each item supports these keys:

- `url`: *(Required)* Repository location
- `build`: *(Required)* Commands used to build the repository.
- `depth`: Clone argument to be passed to `git clone`.
By default, all repositories are cloned with `--depth=1`.
If equal to `0`, the `--depth` argument is not passed at all.
- `dir`: What name to use for the cloned directory.
By default, it is inferred from the `url`.
- `clean`: Commands used to clean the repository before building.
- `requirements`: What this item requires to be successfully built
    - `build-dep`: Packages to be installed with `apt-get build-dep`
    - `packages`: Packages to be installed with normal `apt-get install`

### Examples

#### use `-j` for parallel make build

```shell script
MAKEFLAGS=-j ./compile.py
```

### All options

```text
usage: compile.py [-h] [--verbose | --quiet] [--build-dir DIR]
                  [--whitelist WHITELIST | --blacklist BLACKLIST]
                  [--config YAML_FILE] [--logs-dir LOGS_DIR] [-r] [-e]
                  [--no-clone | --clone-only]

Compile software projects according to config file

optional arguments:
  -h, --help            show this help message and exit
  --verbose, -v         Verbose log level
  --quiet, -q           Quiet log level
  --build-dir DIR, -d DIR
                        Where cloned projects and build files are stored
  --whitelist WHITELIST
                        Only process specifically these items
  --blacklist BLACKLIST
                        Exclude processing these items
  --config YAML_FILE, -c YAML_FILE
                        Config file to use
  --logs-dir LOGS_DIR   Directory for logs of build commands
  -r, --rebuild         Clean & rebuild everything
  -e, --exit-on-error   If any build fails, exit immediately
  --no-clone            Skip cloning phase
  --clone-only          Clone repositories and exit
```

```text
usage: postprocess.py [-h] [--verbose | --quiet] [--build-dir DIR]
                      [--whitelist WHITELIST | --blacklist BLACKLIST]
                      [--opt-levels OPT_LEVELS] [--opt-flags OPT_FLAGS]
                      [--bc-list BC_LIST [BC_LIST ...]] [--postfix POSTFIX]
                      STEP [STEP ...]

Process bitcode files after compilation step

positional arguments:
  STEP                  Steps to execute. Available options:
                        * all    : Run all steps once
                        * archive: Put current state in archive
                        * dis    : Run 'llvm-dis' on all .bc files
                        * opt    : Run optimizer for each optimization level. See --opt-levels.
                        * souper : Run google/souper on all .bc files to get potential candidates
                        * strip  : Run 'opt -strip' on all .bc files

optional arguments:
  -h, --help            show this help message and exit
  --verbose, -v         Verbose log level
  --quiet, -q           Quiet log level
  --build-dir DIR, -d DIR
                        Where cloned projects and build files are stored
  --whitelist WHITELIST
                        Only process specifically these items
  --blacklist BLACKLIST
                        Exclude processing these items
  --opt-levels OPT_LEVELS, -O OPT_LEVELS
                        List of comma-separated optimization levels to use with 'opt' step. See clang/gcc -O option.
  --opt-flags OPT_FLAGS
                        Extra flags to pass to opt
  --bc-list BC_LIST [BC_LIST ...]
                        List of bitcode files to post-process. If not specified, the script will run recursively on all bitcode files on the build dir.
  --postfix POSTFIX     Archive name postfix
```

```text
usage: build_reqs.py [-h] [--verbose | --quiet] [--build-dir DIR]
                     [--whitelist WHITELIST | --blacklist BLACKLIST]
                     [--assume-supported]
                     [YAML_FILE]

Print build requirements from config file

positional arguments:
  YAML_FILE             Config file to parse

optional arguments:
  -h, --help            show this help message and exit
  --verbose, -v         Verbose log level
  --quiet, -q           Quiet log level
  --build-dir DIR, -d DIR
                        Where cloned projects and build files are stored
  --whitelist WHITELIST
                        Only process specifically these items
  --blacklist BLACKLIST
                        Exclude processing these items
  --assume-supported    Skip distro check
```
