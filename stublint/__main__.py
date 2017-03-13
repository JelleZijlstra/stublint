"""stublint entry point.

Responsible for finding files to run on and invoking the linter.

"""
import argparse
import ast
import os
from pathlib import Path
import sys
from typing import Iterable

from .linter import LintVisitor


class StubLintError(Exception):
    pass


def extract_files(args: Iterable[str]) -> Iterable[Path]:
    """Yields files to run on given file or directory inputs."""
    for arg in args:
        path = Path(arg)
        if not path.exists():
            raise StubLintError(f'path does not exist: {arg}')
        elif path.is_dir():
            for dirname, _, filenames in os.walk(path):
                for filename in filenames:
                    if filename.endswith('.pyi'):
                        yield Path(dirname) / filename
        else:
            if path.suffix != '.pyi':
                raise StubLintError(f'stublint works only on stub files: {arg}')
            else:
                yield path


def lint_file(path: Path) -> bool:
    try:
        contents = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        raise StubLintError(f'could not decode contents of {path} as UTF-8')
    try:
        tree = ast.parse(contents)
    except SyntaxError:
        raise StubLintError(f'syntax error in {path}')

    visitor = LintVisitor(path)
    visitor.visit(tree)
    return not visitor.saw_error


def run(args: Iterable[str]) -> bool:
    return all([lint_file(path) for path in extract_files(args)])


if __name__ == '__main__':
    parser = argparse.ArgumentParser('stublint')
    parser.add_argument('dirs_or_files', nargs='+', help='Files to run stublint on')
    args = parser.parse_args()
    try:
        sys.exit(0 if run(args.dirs_or_files) else 0)
    except StubLintError as e:
        print(f'stublint: {e}', file=sys.stderr)
        sys.exit(1)
