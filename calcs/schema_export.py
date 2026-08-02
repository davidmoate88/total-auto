"""
Machine-readable schema export for calc modules -- the canonical source of
truth for any tool (notably the "fill-calc-inputs-from-drawings" Claude Code
skill, see .claude/skills/) that needs a calc module's exact input field
names/types/defaults without re-deriving them by hand, or worse, working
from a written-down reference that's gone stale. Anything consuming this
should call it fresh each time rather than caching field names -- a
renamed/added/removed field is picked up immediately with nothing else to
keep in sync.

Run: python3 -m calcs.schema_export [--discipline "Electrical (LV)" ...] [--key <module_key> ...]
Prints one JSON object to stdout, keyed by module key. No arguments exports
every registered module.
"""

from __future__ import annotations

import argparse
import json
import typing

from pydantic_core import PydanticUndefined

from calcs.registry import CALC_REGISTRY
from core.calc_base import CalcModule


def _field_schema(field_info) -> dict:
    annotation = field_info.annotation
    origin = typing.get_origin(annotation)
    inner = annotation
    is_optional = False
    if origin is typing.Union:
        non_none = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(non_none) == 1:
            is_optional = True
            inner = non_none[0]
            origin = typing.get_origin(inner)

    allowed_values = None
    if origin is typing.Literal:
        type_name = "literal"
        allowed_values = list(typing.get_args(inner))
    elif inner is bool:
        type_name = "bool"
    elif inner is int:
        type_name = "int"
    elif inner is float:
        type_name = "float"
    else:
        type_name = "str"

    default = None if field_info.default is PydanticUndefined else field_info.default
    return {
        "type": type_name,
        "allowed_values": allowed_values,
        "required": field_info.default is PydanticUndefined,
        "optional_field": is_optional,  # Optional[...] -- may be omitted entirely to mean "not set"
        "default": default,
        "description": field_info.description or "",
    }


def export_schema(modules: list[CalcModule]) -> dict:
    schema: dict = {}
    for module in modules:
        schema[module.key] = {
            "name": module.name,
            "discipline": module.discipline,
            "description": module.description,
            "fields": {
                field_name: _field_schema(field_info)
                for field_name, field_info in module.input_model.model_fields.items()
            },
        }
    return schema


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discipline", action="append", default=[], help="Filter to one or more CalcModule.discipline values (repeatable). Combined with --key as AND, not OR -- a module must match both filters if both are given.")
    parser.add_argument("--key", action="append", default=[], help="Filter to one or more specific module keys (repeatable). Combined with --discipline as AND, not OR.")
    args = parser.parse_args()

    modules = CALC_REGISTRY
    if args.discipline:
        modules = [m for m in modules if m.discipline in args.discipline]
    if args.key:
        modules = [m for m in modules if m.key in args.key]

    print(json.dumps(export_schema(modules), indent=2))


if __name__ == "__main__":
    main()
