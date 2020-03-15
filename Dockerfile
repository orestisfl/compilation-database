from ubuntu:18.04

env DEBIAN_FRONTEND=noninteractive
run sed -i -e 's/# deb-src/deb-src/' /etc/apt/sources.list \
    && apt-get update -qq \
    && apt-get full-upgrade -qq \
    && apt-get install -qq wget software-properties-common build-essential cmake git autotools-dev autoconf ninja-build python3 python3-pip bear

# Install llvm 10.x
# See https://apt.llvm.org/
add https://apt.llvm.org/llvm-snapshot.gpg.key llvm.key
run apt-key add llvm.key \
    && echo 'deb http://apt.llvm.org/bionic/ llvm-toolchain-bionic-10 main' >> /etc/apt/sources.list \
    && echo 'deb-src http://apt.llvm.org/bionic/ llvm-toolchain-bionic-10 main' >> /etc/apt/sources.list \
    && apt-get update -qq \
    && apt-get install -qq clang-10 lldb-10 lld-10 llvm-10 llvm-10-dev llvm-10-runtime

# Split the following space to minimize rebuilding:
# 1. pip requirements
add requirements.txt /tmp/requirements.txt
run pip3 install -U -r /tmp/requirements.txt
# 2. config requirements
add utils.py build_reqs.py config.yaml database/
workdir database
run python3 build_reqs.py | sh
# 3. Actual build
add *.py *.sh ./
run ls -l \
    && MAKEFLAGS=-j python3 compile.py -ev
