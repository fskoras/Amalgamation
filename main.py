import os
from pathlib import Path
from argparse import ArgumentParser

from clang.cindex import TranslationUnit, SourceLocation
from clang.cindex import Cursor, CursorKind
from clang.cindex import Type, TypeKind


def __produce_location_str(cursor: Cursor) -> str:
    loc = cursor.location
    return f"{loc.file.name}:{loc.line}:{loc.column}"


def __produce_declaration_str(cursor: Cursor) -> str:
    return f"{cursor.type.spelling} {cursor.spelling}"


def __print_variable_declaration(cursor: Cursor, with_location: bool = True):
    loc: SourceLocation = cursor.location
    location_str = f"  // {__produce_location_str(cursor)}" if with_location else ""
    print(f"extern {cursor.result_type.spelling} {cursor.spelling};{location_str}")


def __print_function_declaration(cursor: Cursor, with_location: bool = True):
    args = ", ".join([__produce_declaration_str(d) for d in cursor.get_arguments()])
    location_str = f"  // {__produce_location_str(cursor)}" if with_location else ""
    print(f"{__produce_declaration_str(cursor)}({args});{location_str}")


def visitor(cursor: Cursor, parent: Cursor = None, level=0):
    if parent:
        if parent.kind.is_translation_unit():
            if cursor.kind == CursorKind.VAR_DECL:
                __print_variable_declaration(cursor)
            if cursor.kind == CursorKind.FUNCTION_DECL:
                __print_function_declaration(cursor)
    for child in cursor.get_children():
        visitor(child, cursor, level+1)


if __name__ == '__main__':
    ap = ArgumentParser(description="Create source code amalgamation ")
    ap.add_argument("-Xargs", action="extend", nargs='*', help="additional compiler arguments")
    ap.add_argument("--compile-commands", help="path to the compile_commands.json")
    ap.add_argument("SOURCE", nargs='?')
    args = ap.parse_args()

    source = args.SOURCE
    args = args.Xargs

    tu = TranslationUnit.from_source(source, args)

    for diagnostic in tu.diagnostics:
        print(f"Error occurred while parsing: {source}")
        print(diagnostic)

    visitor(tu.cursor)
