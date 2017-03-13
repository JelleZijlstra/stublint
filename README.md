# stublint

`stublint` is a linter for [PEP 484](http://www.python.org/dev/peps/pep-0484/)
Python stub files. It is intended for use on [typeshed](http://www.github.com/python/typeshed).

`stublint` works only on Python 3.6.

## Usage
```
(.venv3)$ git clone https://www.github.com/JelleZijlstra/stublint.git
(.venv3)$ cd stublint
(.venv3)$ pip install .
(.venv3)$ cd /path/to/typeshed
(.venv3)$ python3 -m stublint .
```

## Functionality

`stublint` is only intended for logical problems and works at the AST level. `typeshed` uses
`flake8` for formatting.

`stublint` currently checks for the following:
- Function bodies must be empty (allowed self assignments and raise for now)
- Strict constraints on sys.version_info and sys.platform checks.
- TypeVars defined in stub modules must be private to the module.

In strict mode (using the `--strict` argument to stublint), the following are also enabled:
- All arguments must have a type annotations.
- All functions must have a return type annotation.

Much more can be added.
