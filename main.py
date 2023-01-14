import os
from pathlib import Path
from argparse import ArgumentParser

from clang.cindex import TranslationUnit
from clang.cindex import Cursor, CursorKind
from clang.cindex import Type, TypeKind


def __produce_declaration_str(cursor: Cursor) -> str:
    return f"{cursor.type.spelling} {cursor.spelling}"


def __print_function_declaration(cursor: Cursor):
    args = ", ".join([__produce_declaration_str(d) for d in cursor.get_arguments()])
    print(f"{cursor.result_type.spelling} {cursor.spelling}({args});")


def visitor(cursor: Cursor, parent: Cursor = None, level=0):
    if parent:
        if parent.kind.is_translation_unit():
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
