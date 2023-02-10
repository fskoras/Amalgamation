from typing import List, Dict
from pathlib import Path

from clang.cindex import TranslationUnit
from clang.cindex import Cursor, CursorKind
from clang.cindex import TypeKind

from .declarations import Declaration, Symbol, _Type, Variable, Function
from .graph import Graph
from .utilities import _log
from .typing import PathLike


class Amalgamation:
    def __init__(self):
        self.usr: Dict[str, Symbol] = {}
        self.graph: Graph = Graph()

    def _resolve_typedef_declaration(self, cursor: Cursor):
        pass

    def _resolve_elaborated_declaration(self, cursor: Cursor):
        pass

    def _resolve_pointer_declaration(self, cursor: Cursor):
        pass

    def _resolve_type_dependencies(self, t: _Type):
        """pass type declaration processing to the correct resolve function"""
        type_kind = t.kind
        if type_kind == TypeKind.TYPEDEF:
            self._resolve_typedef_declaration(t.cursor)
        elif type_kind == TypeKind.ELABORATED:
            self._resolve_elaborated_declaration(t.cursor)
        elif type_kind == TypeKind.POINTER:
            self._resolve_pointer_declaration(t.cursor)
        else:
            pass  # do nothing

    def _register_symbol(self, symbol: Symbol):
        """keep track of unique symbols using USR (Unified Symbol Resolution)"""
        self.usr[symbol.usr] = symbol

    def _add_variable(self, variable: Variable):
        """register 'Variable' object to graph"""
        type_ = None if variable.type.is_basic else variable.type

        # add dependent types to graph
        self.graph.add_edge(type_, variable)
        self._resolve_type_dependencies(variable.type)

        self._register_symbol(variable)

    def _add_function(self, function: Function):
        """register 'Function' object to graph"""
        type_ = None if function.type.is_basic else function.type

        # add dependent return type to graph
        self.graph.add_edge(type_, function)
        self._resolve_type_dependencies(function.type)

        # add dependent argument types to graph
        for argument in function.arguments:
            type_ = None if argument.type.is_basic else argument.type
            self.graph.add_edge(type_, function)
            self._resolve_type_dependencies(argument.type)

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
