import os
import sys
import logging
from typing import List, Dict, Union
from pathlib import Path
from argparse import ArgumentParser

from clang.cindex import TranslationUnit
from clang.cindex import Cursor, CursorKind
from clang.cindex import Type, TypeKind

from amalgamation.graph import Graph


PathLike = Union[str, os.PathLike]

logging.basicConfig()
_log = logging.getLogger(__name__)


def _cursor_location_text(cursor: Cursor) -> str:
    loc = cursor.location
    if not loc.file:
        return ""
    return f"{loc.file.name}:{loc.line}:{loc.column}"


class Declaration:
    def get_declaration_text(self) -> str:
        raise NotImplementedError

    def get_location_text(self) -> str:
        raise NotImplementedError


class Symbol(Declaration):
    def __init__(self, cursor: Cursor):
        self.cursor = cursor

    def get_declaration_text(self) -> str:
        raise NotImplementedError

    def get_location_text(self) -> str:
        return _cursor_location_text(self.cursor)

    @property
    def name(self):
        return self.cursor.mangled_name

    @property
    def usr(self):
        """Unified Symbol Resolution"""
        return str(self.cursor.get_usr())

    def __hash__(self):
        return hash(self.usr)

    def __eq__(self, other: "Symbol"):
        if not isinstance(other, type(self)):
            return False

        return self.usr == other.usr

    def __repr__(self):
        return f"Symbol({self.name})"


def _declaration_text(cursor: Cursor) -> str:
    return f"{cursor.type.spelling} {cursor.spelling}"


class _Type(Declaration):
    def __init__(self, t: Type):
        self._type = t
        pass

    @property
    def is_basic(self) -> bool:
        """Is basic type (int, float, ...)"""
        kind = self._type.kind.value
        result = TypeKind.VOID.value <= kind <= TypeKind.NULLPTR.value
        return result

    @property
    def cursor(self) -> Cursor:
        return self._type.get_declaration()

    @property
    def usr(self):
        return str(self.cursor.get_usr())

    def __hash__(self):
        return hash(self.usr)

    def __eq__(self, other: "Symbol"):
        if not isinstance(other, type(self)):
            return False

        return self.usr == other.usr

    def __repr__(self):
        return f"_Type({self.name})"

    @property
    def name(self):
        return self._type.spelling

    def get_declaration_text(self) -> str:
        # TODO: figure out how to resolve complex types
        return f"/* {self.__repr__()} */"

    def get_location_text(self) -> str:
        return _cursor_location_text(self.cursor)


class Variable(Symbol):
    def __init__(self, cursor: Cursor):
        super().__init__(cursor)

    def get_declaration_text(self) -> str:
        return f"extern {_declaration_text(self.cursor)};"

    @property
    def type(self):
        return _Type(self.cursor.type)


class Function(Symbol):
    def __init__(self, cursor: Cursor):
        super().__init__(cursor)

    @property
    def type(self):
        return _Type(self.cursor.result_type)

    @property
    def arguments(self):
        return [Variable(a) for a in self.cursor.get_arguments()]

    def get_declaration_text(self) -> str:
        arguments = self.cursor.get_arguments()
        arguments = ", ".join([_declaration_text(arg) for arg in arguments])
        ret_type = self.cursor.result_type
        return f"{ret_type.spelling} {self.cursor.spelling}({arguments});"


class Amalgamation:
    def __init__(self):
        self.usr: Dict[str, Symbol] = {}
        self.graph: Graph = Graph()

    @staticmethod
    def _register_type_dependencies(t: _Type) -> List[Cursor]:
        """TODO: type dependencies shall be searched for and registered to the global context"""
        return []

    def _register_symbol(self, symbol: Symbol):
        """keep track of unique symbols using USR (Unified Symbol Resolution)"""
        self.usr[symbol.usr] = symbol

    def _add_variable(self, variable: Variable):
        """register 'Variable' object to graph"""
        type_ = None if variable.type.is_basic else variable.type

        # add dependent types to graph
        self.graph.add_edge(type_, variable)
        self._register_type_dependencies(type_)

        self._register_symbol(variable)

    def _add_function(self, function: Function):
        """register 'Function' object to graph"""
        type_ = None if function.type.is_basic else function.type

        # add dependent return type to graph
        self.graph.add_edge(type_, function)
        self._register_type_dependencies(type_)

        # add dependent argument types to graph
        for argument in function.arguments:
            type_ = None if argument.type.is_basic else argument.type
            self.graph.add_edge(type_, function)
            self._register_type_dependencies(type_)

        self._register_symbol(function)

    def _symbol_visitor(self, cursor):
        """Filter CursorKind and register global symbols to context"""
        usr = cursor.get_usr()
        if usr in self.usr.keys():
            _log.debug(f"Symbol duplicate: {cursor.spelling}")
            return  # skip

        if cursor.kind == CursorKind.VAR_DECL:
            self._add_variable(Variable(cursor))

        if cursor.kind == CursorKind.FUNCTION_DECL:
            self._add_function(Function(cursor))

    def _node_visitor(self, cursor: Cursor, parent: Cursor = None, level=0):
        """Visit recursively all nodes and pass global symbol cursor to _symbol_visitor"""
        if parent:
            if parent.kind.is_translation_unit():
                if cursor.kind == CursorKind.VAR_DECL or cursor.kind == CursorKind.FUNCTION_DECL:
                    self._symbol_visitor(cursor)

        for child in cursor.get_children():
            self._node_visitor(child, cursor, level + 1)

    def parse(self, sources: List[Path]):
        """Produce AST for all sources and run it through internal _node_visitor"""
        for source in sources:
            tu = TranslationUnit.from_source(source, None)

            for diagnostic in tu.diagnostics:
                _log.error(f"Error occurred while parsing: {source}")
                _log.error(diagnostic)

            self._node_visitor(tu.cursor)

    def get_declarations(self) -> List[Declaration]:
        """Return list of prepared and sorted declarations"""
        return self.graph.topological_sort()

    def get_content(self) -> str:
        """Return parsed content"""
        content = ""

        sorted_usr = self.get_declarations()

        for decl in sorted_usr:
            if decl is None:
                continue

            content += f"{decl.get_declaration_text()}  // {decl.get_location_text()}\n"

        if not content:
            _log.warning("Content is empty. You need to parse something first!")

        return content

    def dump(self, file: PathLike):
        """Dump content to file"""
        with open(file, mode="w+") as fp:
            fp.write(self.get_content())

    def print(self):
        """Print content on stdout"""
        print(self.get_content())


if __name__ == '__main__':
    ap = ArgumentParser(description="Create C/C++ source code amalgamation")
    ap.add_argument("SOURCE", nargs="+", help="C/C++ source files")
    ap.add_argument("-o", "--output", type=Path, help="Output to a specific file instead of stdout")
    args = ap.parse_args()

    sources = [Path(p) for p in args.SOURCE]
    for source in sources:
        if not source.exists():
            _log.error(f"Input source path does not exist: {source}")
            sys.exit(1)

    amalgamation = Amalgamation()
    amalgamation.parse(sources=sources)

    output = args.output
    if output is not None:
        amalgamation.dump(file=output)
    else:
        amalgamation.print()
