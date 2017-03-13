"""Linter implementation, containing the lint rules.

Ideas for things to add:
- default argument must be ...
- all return and argument types must be given (probably will require a lot of changes in typeshed)

"""

import ast
from pathlib import Path
import sys
from typing import Iterable, Optional

_MUST_HAVE_SYS = 'Conditional expression must have sys.version_info or sys.platform as its left operand'
_BAD_VERSION_SLICE = 'Unrecognized sys.version_info subscript'
_VERSION_COMPARE_NUMBER = 'sys.version_info comparison must be against an int or tuple of ints'


class LintVisitor(ast.NodeVisitor):
    def __init__(self, filename: Path, strict: bool=False) -> None:
        self.saw_error = False
        self.filename = filename
        self.strict = strict

    def visit_arguments(self, node: ast.arguments) -> None:
        self.generic_visit(node)
        if self.strict:
            for default in node.kw_defaults + node.defaults:
                if not isinstance(default, ast.Ellipsis) and default is not None:
                    self.error(default, 'default value must be ... in a stub')

            def get_args() -> Iterable[ast.arg]:
                if node.args:
                    if node.args[0].arg not in ('self', 'cls'):
                        yield node.args[0]
                    yield from node.args[1:]
                if node.vararg is not None:
                    yield node.vararg
                yield from node.kwonlyargs
                if node.kwarg is not None:
                    yield node.kwarg

            for arg in get_args():
                if arg.annotation is None:
                    self.error(arg, 'Argument is missing a type annotation')

    def visit_Assign(self, node: ast.Assign) -> None:
        self.generic_visit(node)
        # attempt to find assignments to type helpers (typevars and aliases), which should be private
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == 'TypeVar':
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    self.error(target, 'TypeVar must be assigned to a name')
                elif not target.id.startswith('_'):
                    # avoid catching AnyStr in typing
                    if self.filename.name != 'typing.pyi':
                        self.error(target, 'Name of private TypeVar must start with _')

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.generic_visit(node)
        if self.strict and node.returns is None:
            self.error(node, 'Function is missing a return type annotation')

        for i, statement in enumerate(node.body):
            if i == 0:
                # normally, the body will just be "pass" or "..."
                if isinstance(statement, ast.Pass):
                    continue
                elif isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Ellipsis):
                    continue
            # allow "raise", a number of stubs have this
            if isinstance(statement, ast.Raise):
                continue
            # allow assignments in constructor
            # (though these should probably be changed)
            if node.name == '__init__' and isinstance(statement, ast.Assign) and \
                    isinstance(statement.targets[0], ast.Attribute) and \
                    isinstance(statement.targets[0].value, ast.Name) and \
                    statement.targets[0].value.id == 'self':
                continue
            self.error(statement, 'Function body must contain only ... or pass')

    def visit_If(self, node: ast.If) -> None:
        self.generic_visit(node)
        test = node.test
        if isinstance(test, ast.BoolOp):
            for expr in test.values:
                self._check_if_expr(expr)
        else:
            self._check_if_expr(test)

    def _check_if_expr(self, node: ast.expr) -> None:
        if not isinstance(node, ast.Compare):
            self.error(node, 'Conditional expression must be a simple comparison')
            return
        if len(node.comparators) != 1:
            # mypy doesn't support chained comparisons
            self.error(node, 'Conditional expression must be a simple comparison')
            return
        if isinstance(node.left, ast.Subscript):
            self._check_version_check(node)
        elif isinstance(node.left, ast.Attribute):
            if isinstance(node.left.value, ast.Name) and node.left.value.id == 'sys':
                if node.left.attr == 'platform':
                    self._check_platform_check(node)
                elif node.left.attr == 'version_info':
                    self._check_version_check(node)
                else:
                    self.error(node, _MUST_HAVE_SYS)
            else:
                self.error(node, _MUST_HAVE_SYS)
        else:
            self.error(node, _MUST_HAVE_SYS)

    def _check_version_check(self, node: ast.Compare) -> None:
        must_be_single = False
        can_have_strict_equals: Optional[int] = None
        version_info = node.left
        if isinstance(version_info, ast.Subscript):
            slc = version_info.slice
            if isinstance(slc, ast.Index):
                # anything other than the integer 0 doesn't make much sense
                # (things that are in 2.7 and 3.7 but not 3.6?)
                if isinstance(slc.value, ast.Num) and slc.value.n == 0:
                    must_be_single = True
                else:
                    self.error(node, _BAD_VERSION_SLICE)
            elif isinstance(slc, ast.Slice):
                # allow only [:1] and [:2]
                if slc.lower is not None or slc.step is not None:
                    self.error(node, _BAD_VERSION_SLICE)
                elif isinstance(slc.upper, ast.Num) and slc.upper.n in (1, 2):
                    can_have_strict_equals = slc.upper.n
                else:
                    self.error(node, _BAD_VERSION_SLICE)
            else:
                # extended slicing
                self.error(node, _BAD_VERSION_SLICE)

        comparator = node.comparators[0]
        if must_be_single:
            if not isinstance(comparator, ast.Num):
                self.error(node, _VERSION_COMPARE_NUMBER)
        else:
            if not isinstance(comparator, ast.Tuple):
                self.error(node, _VERSION_COMPARE_NUMBER)
            elif not all(isinstance(elt, ast.Num) for elt in comparator.elts):
                self.error(node, _VERSION_COMPARE_NUMBER)
            elif len(comparator.elts) > 2:
                # mypy only supports major and minor version checks
                self.error(node, 'version comparison must use only major and minor version')

            cmpop = node.ops[0]
            if isinstance(cmpop, (ast.Lt, ast.GtE)):
                pass
            elif isinstance(cmpop, (ast.Eq, ast.NotEq)):
                if can_have_strict_equals is not None:
                    if len(comparator.elts) != can_have_strict_equals:
                        self.error(node, f'version comparison must be against a length-{can_have_strict_equals} tuple')
                else:
                    self.error(node, 'Do not use strict equality for version checks')
            else:
                self.error(node, 'Use only < and >= for version comparisons')

    def _check_platform_check(self, node: ast.Compare) -> None:
        cmpop = node.ops[0]
        # "in" might also make sense but we don't currently have one
        if not isinstance(cmpop, (ast.Eq, ast.NotEq)):
            self.error(node, 'sys.platform check only supports == and !=')
        comparator = node.comparators[0]
        if isinstance(comparator, ast.Str):
            # other values are possible but we don't need them right now
            # this protects against typos
            if comparator.s not in ('linux', 'win32', 'cygwin', 'darwin'):
                self.error(node, f'unrecognized platform "{comparator.s}"')
        else:
            self.error(node, 'sys.platform check must be against a single string')

    def error(self, node: ast.AST, msg: str) -> None:
        self.saw_error = True
        print(f'{self.filename}:{node.lineno}: {msg}', file=sys.stderr)
