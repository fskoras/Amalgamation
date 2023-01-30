import os
import sys
import logging
from typing import List, Dict, Hashable
from pathlib import Path
from argparse import ArgumentParser
from collections import defaultdict

from clang.cindex import TranslationUnit, SourceLocation
from clang.cindex import Cursor, CursorKind
from clang.cindex import Type, TypeKind


logging.basicConfig()
_log = logging.getLogger(__name__)


class Graph:
    """Graph utilities"""
    def __init__(self):
        self._graph = defaultdict(list)  # dictionary containing adjacency List
        self._nodes = set()

    def __len__(self):
        return self.nodes_count

    @property
    def nodes_count(self):
        return len(self._nodes)

    def add_edge(self, u: Hashable, v: Hashable):
        """function to add an edge to graph between any 2 hashable nodes (u -> v)"""
        assert u is not v, "You can't add edge to self"
        self._nodes.update({u, v})
        self._graph[u].append(v)

    def _topological_sort_util(self, node, visited, stack):
        """A recursive function used by 'topological_sort'"""
        # Mark the current node as visited.
        visited[node] = True

        # Recur for all the vertices adjacent to this vertex
        for i in self._graph[node]:
            if not visited[i]:
                self._topological_sort_util(i, visited, stack)

        # Push current vertex to stack which stores result
        stack.insert(0, node)

    def topological_sort(self) -> List:
        """The function to do Topological Sort. It uses recursive '_topological_sort_util'

        Returns:
            List of sorted nodes

        >>> g = Graph()
        >>> g.add_edge(5, 2)
        >>> g.add_edge(5, 0)
        >>> g.add_edge(4, 0)
        >>> g.add_edge(4, 1)
        >>> g.add_edge(2, 3)
        >>> g.add_edge(3, 1)
        >>> g.topological_sort()
        [5, 4, 2, 3, 1, 0]
        """

        # Mark all the vertices as not visited
        visited = {k: False for k in self._nodes}
        stack = []

        # Call the recursive helper function to store Topological Sort starting from all vertices one by one
        for node in visited.keys():
            if not visited[node]:
                self._topological_sort_util(node, visited, stack)

        return stack


class Symbol:
    def __init__(self, cursor: Cursor):
        self.cursor = cursor

    def get_declaration_text(self) -> str:
        raise NotImplementedError

    def get_location_text(self) -> str:
        loc = self.cursor.location
        return f"{loc.file.name}:{loc.line}:{loc.column}"

    @property
    def name(self):
        return self.cursor.mangled_name


def _declaration_text(cursor: Cursor) -> str:
    return f"{cursor.type.spelling} {cursor.spelling}"


class _Type:
    def __init__(self, t: Type):
        self._type = t

    @property
    def name(self):
        return self._type.spelling


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
        self.symbols: Dict[str, Symbol] = {}
        self.graph: Graph = Graph()

    def _add_symbol(self, cursor):
        usr = cursor.get_usr()
        if usr in self.symbols.keys():
            _log.debug(f"Symbol duplicate: {cursor.spelling}")
            return

        if cursor.kind == CursorKind.VAR_DECL:
            var = Variable(cursor)
            self.symbols[usr] = var

        if cursor.kind == CursorKind.FUNCTION_DECL:
            func = Function(cursor)
            self.symbols[usr] = func

    def _symbol_visitor(self, cursor: Cursor, parent: Cursor = None, level=0):
        """visit nodes and """
        if parent:
            if parent.kind.is_translation_unit():
                if cursor.kind == CursorKind.VAR_DECL or cursor.kind == CursorKind.FUNCTION_DECL:
                    self._add_symbol(cursor)

        for child in cursor.get_children():
            self._symbol_visitor(child, cursor, level + 1)

    def parse(self, sources: List[Path]):
        for source in sources:
            tu = TranslationUnit.from_source(source, None)

            for diagnostic in tu.diagnostics:
                _log.error(f"Error occurred while parsing: {source}")
                _log.error(diagnostic)

            self._symbol_visitor(tu.cursor)

    def get_content(self):
        content = ""

        for symbol in self.symbols.values():
            content += f"{symbol.get_declaration_text()}  // {symbol.get_location_text()}\n"

        if not content:
            _log.warning("Content is empty. You need to parse something first!")

        return content

    def dump(self, output):
        with open(output, mode="w+") as fp:
            fp.write(self.get_content())

    def print(self):
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
        amalgamation.dump(output=output)
    else:
        amalgamation.print()
