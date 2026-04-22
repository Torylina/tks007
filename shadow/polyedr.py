from math import pi, sqrt
from functools import reduce
from operator import add
from common.r3 import R3
from common.tk_drawer import TkDrawer


class Segment:
    """ Одномерный отрезок """
    def __init__(self, beg, fin):
        self.beg, self.fin = beg, fin

    def is_degenerate(self):
        return self.beg >= self.fin

    def intersect(self, other):
        if other.beg > self.beg:
            self.beg = other.beg
        if other.fin < self.fin:
            self.fin = other.fin
        return self

    def subtraction(self, other):
        return [Segment(
            self.beg, self.fin if self.fin < other.beg else other.beg),
            Segment(self.beg if self.beg > other.fin else other.fin, self.fin)]


class Edge:
    """ Ребро полиэдра """
    SBEG, SFIN = 0.0, 1.0

    def __init__(self, beg, fin, original_beg=None, original_fin=None):
        self.beg, self.fin = beg, fin
        self.original_beg = original_beg if original_beg else beg
        self.original_fin = original_fin if original_fin else fin
        self.mid = R3((beg.x + fin.x) / 2,
                      (beg.y + fin.y) / 2,
                      (beg.z + fin.z) / 2)
        self._length = sqrt(
            (self.original_fin.x - self.original_beg.x)**2 +
            (self.original_fin.y - self.original_beg.y)**2 +
            (self.original_fin.z - self.original_beg.z)**2
        )
        self.gaps = [Segment(Edge.SBEG, Edge.SFIN)]

    def shadow(self, facet):
        if facet.is_vertical():
            return
        shade = Segment(Edge.SBEG, Edge.SFIN)
        for u, v in zip(facet.vertexes, facet.v_normals()):
            shade.intersect(self.intersect_edge_with_normal(u, v))
            if shade.is_degenerate():
                return

        shade.intersect(
            self.intersect_edge_with_normal(
                facet.vertexes[0], facet.h_normal()))
        if shade.is_degenerate():
            return

        gaps = [s.subtraction(shade) for s in self.gaps]
        self.gaps = [
            s for s in reduce(add, gaps, []) if not s.is_degenerate()]

    def r3(self, t):
        return self.beg * (Edge.SFIN - t) + self.fin * t

    def intersect_edge_with_normal(self, a, n):
        f0, f1 = n.dot(self.beg - a), n.dot(self.fin - a)
        if f0 >= 0.0 and f1 >= 0.0:
            return Segment(Edge.SFIN, Edge.SBEG)
        if f0 < 0.0 and f1 < 0.0:
            return Segment(Edge.SBEG, Edge.SFIN)
        x = - f0 / (f1 - f0)
        return Segment(Edge.SBEG, x) if f0 < 0.0 else Segment(x, Edge.SFIN)

    def length(self):
        return self._length


class Facet:
    """ Грань полиэдра """
    def __init__(self, vertexes):
        self.vertexes = vertexes

    def is_vertical(self):
        return self.h_normal().dot(Polyedr.V) == 0.0

    def h_normal(self):
        n = (
            self.vertexes[1] - self.vertexes[0]).cross(
            self.vertexes[2] - self.vertexes[0])
        return n * (-1.0) if n.dot(Polyedr.V) < 0.0 else n

    def v_normals(self):
        return [self._vert(x) for x in range(len(self.vertexes))]

    def _vert(self, k):
        n = (self.vertexes[k] - self.vertexes[k - 1]).cross(Polyedr.V)
        return n * \
            (-1.0) if n.dot(self.vertexes[k - 1] - self.center()) < 0.0 else n

    def center(self):
        return sum(self.vertexes, R3(0.0, 0.0, 0.0)) * \
            (1.0 / len(self.vertexes))


class Polyedr:
    """ Полиэдр """
    V = R3(0.0, 0.0, 1.0)

    def __init__(self, file):
        self.vertexes, self.edges, self.facets = [], [], []
        self.original_vertexes = []

        with open(file) as f:
            lines = f.readlines()

        buf = lines[0].split()
        c = float(buf.pop(0))
        alpha, beta, gamma = (float(x) * pi / 180.0 for x in buf)

        nv, nf, ne = (int(x) for x in lines[1].split())

        for i in range(2, nv + 2):
            x, y, z = (float(val) for val in lines[i].split())
            original = R3(x, y, z)
            self.original_vertexes.append(original)
            self.vertexes.append(original.rz(alpha).ry(beta).rz(gamma) * c)

        seen_edges = set()
        for i in range(nv + 2, len(lines)):
            buf = lines[i].split()
            size = int(buf.pop(0))
            indices = [int(n) - 1 for n in buf]

            vertexes = [self.vertexes[idx] for idx in indices]
            orig_vertexes = [self.original_vertexes[idx] for idx in indices]

            for n in range(size):
                v1, v2 = vertexes[n - 1], vertexes[n]
                orig_v1, orig_v2 = orig_vertexes[n - 1], orig_vertexes[n]

                edge_key = frozenset([
                    (round(v1.x, 9), round(v1.y, 9), round(v1.z, 9)),
                    (round(v2.x, 9), round(v2.y, 9), round(v2.z, 9))
                ])

                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    self.edges.append(Edge(v1, v2, orig_v1, orig_v2))

            self.facets.append(Facet(vertexes))

    @staticmethod
    def is_good_point(p):
        return p.x * p.x + p.y * p.y > 1.0

    def good_edges_length_sum(self):
        return sum(
            e.length() for e in self.edges
            if self.is_good_point(e.beg) and
            self.is_good_point(e.fin) and
            self.is_good_point(e.mid)
        )

    def draw(self, tk):  # pragma: no cover
        tk.clean()
        for e in self.edges:
            for f in self.facets:
                e.shadow(f)
            for s in e.gaps:
                tk.draw_line(e.r3(s.beg), e.r3(s.fin))
