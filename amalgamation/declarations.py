from clang.cindex import Type, TypeKind
from clang.cindex import Cursor


def _cursor_location_text(cursor: Cursor) -> str:
    loc = cursor.location
    if not loc.file:
        return ""
    return f"{loc.file.name}:{loc.line}:{loc.column}"


class Declaration:
    def get_cursor(self) -> Cursor:
        raise NotImplementedError

    def get_declaration_text(self) -> str:
        raise NotImplementedError

    def get_location_text(self) -> str:
        raise NotImplementedError


class Symbol(Declaration):
    def __init__(self, cursor: Cursor):
        self.cursor = cursor

    def get_cursor(self) -> Cursor:
        return self.cursor

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

    def get_cursor(self) -> Cursor:
        return self.cursor

    @property
    def kind(self) -> TypeKind:
        return self._type.kind

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
