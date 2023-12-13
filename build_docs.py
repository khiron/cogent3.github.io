#!/usr/bin/env python3
from fnmatch import fnmatch
import os
import subprocess
import sys
import click
import pathlib
import shutil
from contextlib import contextmanager

@contextmanager
def cwd(path):
    oldpwd=os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldpwd)

WEB_REPO = pathlib.Path("~/repos/cogent3org").expanduser()
SRC_REPO = pathlib.Path("~/repos/Cogent3").expanduser()

WEB_DIR = pathlib.Path("c3org")
SRC_DIR = pathlib.Path("c3src")


def exec_command(cmnd, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    """executes shell command and returns stdout if completes exit code 0

    Parameters
    ----------

    cmnd : str
      shell command to be executed
    stdout, stderr : streams
      Default value (PIPE) intercepts process output, setting to None
      blocks this."""
    proc = subprocess.Popen(cmnd, shell=True, stderr=stderr)
    out, err = proc.communicate()
    if proc.returncode != 0:
        msg = err
        sys.stderr.writelines("FAILED: %s\n%s" % (cmnd, msg))
        sys.exit(proc.returncode)

    if out is not None:
        r = out.decode("utf8")
    else:
        r = None

    return r


def remove_old_repos():
    for p in (WEB_DIR, SRC_DIR):
        if pathlib.Path(p).exists():
            shutil.rmtree(p)

def bookmark_org_repo():
    # need to make sure the org repo is bookmarked as develop
    with cwd(WEB_REPO):
        r = exec_command("hg bookmark develop -f")


def clone_repos():
    """clones the repos and moves src docs into place, plus the working directory"""
    bookmark_org_repo()
    r = exec_command(f"hg clone {SRC_REPO} {SRC_DIR}")
    r = exec_command(f"hg clone {WEB_REPO} {WEB_DIR}")
    dest_docs = (WEB_DIR / "doc" / "doc").absolute()
    src_docs = (SRC_DIR / "doc").absolute()
    assert src_docs.exists()
    dest_docs.symlink_to(src_docs)
    dest_script = (WEB_DIR / "doc" / "set_working_directory.py").absolute()
    src_script = (SRC_DIR / "doc" / "set_working_directory.py").absolute()
    src_script.rename(dest_script)
    dest_bib = (WEB_DIR / "doc" / "cogent3.bib").absolute()
    src_bib = (SRC_DIR / "doc" / "cogent3.bib").absolute()
    src_bib.rename(dest_bib)


def path_matches(path, patterns):
    return any(fnmatch(path, pattern) for pattern in patterns)


def reduce_draw_examples():
    """make these much simpler by deleting all but the simplest"""
    patterns = "*gaps-per-seq*", "*-square.py", "*README*"
    draw_root = WEB_DIR / "doc/doc/draw_examples"
    for path in draw_root.glob("**/*"):
        match = path_matches(path, patterns)
        if match or path.is_dir():
            continue

        path.unlink()


def remove_docs(pattern):
    """removes all files that don't match pattern, except index docs"""
    doc_root = WEB_DIR / "doc/doc"
    patterns = pattern, "*index.rst", "*template*", "*draw_exa*"
    for path in doc_root.glob("**/*.rst"):
        match = path_matches(path, patterns)
        if match or path.is_dir():
            continue

        if "template" in str(path):
            print(path)
        path.unlink()


def build_docs():
    """builds the docs"""
    os.chdir(WEB_DIR)
    exec_command("hg up develop")
    exec_command("ls")
    os.chdir("doc")
    exec_command("make github")



@click.group()
def main():
    """build docs from cloning the cogent3org and cogent3 source repro"""
    ...

@main.command()
def build_all():
    """builds all docs"""
    remove_old_repos()
    clone_repos()
    build_docs()


@main.command(no_args_is_help=True)
@click.option("-p", "--pattern", help="is a glob pattern matching a directory, or doc file to match")
@click.option("-s", "--simplify_draw", is_flag=True, help="removes all drawing examples except simple ones")
def build_just(pattern: str = None, simplify_draw: bool = False):
    """builds a subset of docs
    """
    remove_old_repos()
    clone_repos()
    if simplify_draw:
        reduce_draw_examples()

    if pattern:
        remove_docs(pattern)

    build_docs()


if __name__ == "__main__":
    main()
