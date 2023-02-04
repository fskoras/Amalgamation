from typing import List, Hashable
from collections import defaultdict


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
