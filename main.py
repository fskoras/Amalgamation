import os
import sys
import logging
from typing import Dict
from pathlib import Path
from argparse import ArgumentParser

from clang.cindex import TranslationUnit, SourceLocation
from clang.cindex import Cursor, CursorKind
from clang.cindex import Type, TypeKind


logging.basicConfig()
_log = logging.getLogger(__name__)


class Symbol:
    def __init__(self, cursor: Cursor):
        self.cursor = cursor


class Variable(Symbol):
    def __init__(self, cursor: Cursor):
        super().__init__(cursor)


class Function(Symbol):
    def __init__(self, cursor: Cursor):
        super().__init__(cursor)


class Amalgamation:
    content: str = ""
    symbols: Dict[str, Symbol] = {}

    @staticmethod
    def __produce_location_str(cursor: Cursor) -> str:
        loc = cursor.location
        return f"{loc.file.name}:{loc.line}:{loc.column}"

    @staticmethod
    def __produce_declaration_str( cursor: Cursor) -> str:
        return f"{cursor.type.spelling} {cursor.spelling}"

    def _variable_declaration_str(self, cursor: Cursor, with_location: bool = True):
        loc: SourceLocation = cursor.location
        location_str = f"  // {self.__produce_location_str(cursor)}" if with_location else ""
        return f"extern {cursor.result_type.spelling} {cursor.spelling};{location_str}"

    def _function_declaration_str(self, cursor: Cursor, with_location: bool = True):
        args = ", ".join([self.__produce_declaration_str(d) for d in cursor.get_arguments()])
        location_str = f"  // {self.__produce_location_str(cursor)}" if with_location else ""
        return f"{self.__produce_declaration_str(cursor)}({args});{location_str}"

    def _add_symbol(self, cursor):
        usr = cursor.get_usr()
        if usr in self.symbols.keys():
            _log.debug(f"Symbol duplicate: {cursor.spelling}")

        if cursor.kind == CursorKind.VAR_DECL:
            self.symbols[usr] = Variable(cursor)
            self.content += self._variable_declaration_str(cursor) + "\n"

        if cursor.kind == CursorKind.FUNCTION_DECL:
            self.symbols[usr] = Function(cursor)
            self.content += self._function_declaration_str(cursor) + "\n"

    def _symbol_visitor(self, cursor: Cursor, parent: Cursor = None, level=0):
        """visit nodes and """
        if parent:
            if parent.kind.is_translation_unit():
                if cursor.kind == CursorKind.VAR_DECL or cursor.kind == CursorKind.FUNCTION_DECL:
                    self._add_symbol(cursor)

        for child in cursor.get_children():
            self._symbol_visitor(child, cursor, level + 1)

    def parse(self, source):
        tu = TranslationUnit.from_source(source, None)

        for diagnostic in tu.diagnostics:
            _log.error(f"Error occurred while parsing: {source}")
            _log.error(diagnostic)

        self._symbol_visitor(tu.cursor)

    def get_content(self):
        if not self.content:
            _log.warning("Empty content. Did you forgot to parse it?")

        return self.content

    def dump(self, output):
        with open(output, mode="w+") as fp:
            fp.write(self.get_content())

    def print(self):
        print(self.get_content())


if __name__ == '__main__':
    ap = ArgumentParser(description="Create source code amalgamation ")
    ap.add_argument("-o", "--output", type=Path, help="specify a file to dump the generated content")
    ap.add_argument("SOURCE", nargs='?')
    args = ap.parse_args()

    source = args.SOURCE
    output = args.output

    amalgamation = Amalgamation()
    amalgamation.parse(source=source)
    amalgamation.dump(output=output)
