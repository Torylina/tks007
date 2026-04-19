from math import pi, sqrt
from functools import reduce
from operator import add
from common.r3 import R3
from common.tk_drawer import TkDrawer


class Segment:
    """ Одномерный отрезок """
    # Параметры конструктора: начало и конец отрезка (числа)

    def __init__(self, beg, fin):
        self.beg, self.fin = beg, fin

    # Отрезок вырожден?
    def is_degenerate(self):
        return self.beg >= self.fin

    # Пересечение с отрезком
    def intersect(self, other):
        if other.beg > self.beg:
            self.beg = other.beg
        if other.fin < self.fin:
            self.fin = other.fin
        return self

    # Разность отрезков
    # Разность двух отрезков всегда является списком из двух отрезков!
    def subtraction(self, other):
        return [Segment(
            self.beg, self.fin if self.fin < other.beg else other.beg),
            Segment(self.beg if self.beg > other.fin else other.fin, self.fin)]


class Edge:
    """ Ребро полиэдра """
    # Начало и конец стандартного одномерного отрезка
    SBEG, SFIN = 0.0, 1.0

    # Параметры конструктора: начало и конец ребра (точки в R3)
    def __init__(self, beg, fin, original_beg=None, original_fin=None):
        self.beg, self.fin = beg, fin
        # Сохраняем оригинальные точки для вычисления длины
        self.original_beg = original_beg if original_beg else beg
        self.original_fin = original_fin if original_fin else fin
        # Список «просветов»
        self.gaps = [Segment(Edge.SBEG, Edge.SFIN)]

    # Учёт тени от одной грани
    def shadow(self, facet):
        # «Вертикальная» грань не затеняет ничего
        if facet.is_vertical():
            return
        # Нахождение одномерной тени на ребре
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
        # Преобразование списка «просветов», если тень невырождена
        gaps = [s.subtraction(shade) for s in self.gaps]
        self.gaps = [
            s for s in reduce(add, gaps, []) if not s.is_degenerate()]

    # Преобразование одномерных координат в трёхмерные
    def r3(self, t):
        return self.beg * (Edge.SFIN - t) + self.fin * t

    # Пересечение ребра с полупространством, задаваемым точкой (a)
    # на плоскости и вектором внешней нормали (n) к ней
    def intersect_edge_with_normal(self, a, n):
        f0, f1 = n.dot(self.beg - a), n.dot(self.fin - a)
        if f0 >= 0.0 and f1 >= 0.0:
            return Segment(Edge.SFIN, Edge.SBEG)
        if f0 < 0.0 and f1 < 0.0:
            return Segment(Edge.SBEG, Edge.SFIN)
        x = - f0 / (f1 - f0)
        return Segment(Edge.SBEG, x) if f0 < 0.0 else Segment(x, Edge.SFIN)

    # Длина ребра в пространстве (вычисляется по оригинальным точкам)
    def length(self):
        return sqrt((self.original_fin.x - self.original_beg.x)**2 +
                    (self.original_fin.y - self.original_beg.y)**2 +
                    (self.original_fin.z - self.original_beg.z)**2)


class Facet:
    """ Грань полиэдра """
    # Параметры конструктора: список вершин

    def __init__(self, vertexes):
        self.vertexes = vertexes

    # «Вертикальна» ли грань?
    def is_vertical(self):
        return self.h_normal().dot(Polyedr.V) == 0.0

    # Нормаль к «горизонтальному» полупространству
    def h_normal(self):
        n = (
            self.vertexes[1] - self.vertexes[0]).cross(
            self.vertexes[2] - self.vertexes[0])
        return n * (-1.0) if n.dot(Polyedr.V) < 0.0 else n

    # Нормали к «вертикальным» полупространствам, причём k-я из них
    # является нормалью к грани, которая содержит ребро, соединяющее
    # вершины с индексами k-1 и k
    def v_normals(self):
        return [self._vert(x) for x in range(len(self.vertexes))]

    # Вспомогательный метод
    def _vert(self, k):
        n = (self.vertexes[k] - self.vertexes[k - 1]).cross(Polyedr.V)
        return n * \
            (-1.0) if n.dot(self.vertexes[k - 1] - self.center()) < 0.0 else n

    # Центр грани
    def center(self):
        return sum(self.vertexes, R3(0.0, 0.0, 0.0)) * \
            (1.0 / len(self.vertexes))


class Polyedr:
    """ Полиэдр """
    # вектор проектирования
    V = R3(0.0, 0.0, 1.0)

    # Параметры конструктора: файл, задающий полиэдр
    def __init__(self, file):

        # списки вершин, рёбер и граней полиэдра
        self.vertexes, self.edges, self.facets = [], [], []

        # списки оригинальных вершин (до преобразований)
        self.original_vertexes = []

        # множество для отслеживания уже добавленных рёбер
        seen_edges = set()

        # список строк файла
        with open(file) as f:
            for i, line in enumerate(f):
                if i == 0:
                    # обрабатываем первую строку; buf - вспомогательный массив
                    buf = line.split()
                    # коэффициент гомотетии
                    c = float(buf.pop(0))
                    # углы Эйлера, определяющие вращение
                    alpha, beta, gamma = (float(x) * pi / 180.0 for x in buf)
                elif i == 1:
                    # во второй строке число вершин, граней и рёбер полиэдра
                    nv, nf, ne = (int(x) for x in line.split())
                elif i < nv + 2:
                    # задание всех вершин полиэдра
                    x, y, z = (float(x) for x in line.split())
                    # Сохраняем оригинальные вершины (без преобразований)
                    original = R3(x, y, z)
                    self.original_vertexes.append(original)
                    # Сохраняем преобразованные вершины
                    self.vertexes.append(original.rz(
                        alpha).ry(beta).rz(gamma) * c)
                else:
                    # вспомогательный массив
                    buf = line.split()
                    # количество вершин очередной грани
                    size = int(buf.pop(0))
                    # массив вершин этой грани (преобразованных)
                    vertexes = list(self.vertexes[int(n) - 1] for n in buf)
                    # массив оригинальных вершин
                    original_vertexes = list(
                        self.original_vertexes[int(n) - 1] for n in buf)
                    # задание рёбер грани (без дублирования)
                    for n in range(size):
                        v1 = vertexes[n - 1]
                        v2 = vertexes[n]
                        orig_v1 = original_vertexes[n - 1]
                        orig_v2 = original_vertexes[n]
                        # Ключ для ребра (независимо от направления)
                        key1 = (round(v1.x, 9), round(v1.y, 9),
                                round(v1.z, 9), round(v2.x, 9),
                                round(v2.y, 9), round(v2.z, 9))
                        key2 = (round(v2.x, 9), round(v2.y, 9),
                                round(v2.z, 9), round(v1.x, 9),
                                round(v1.y, 9), round(v1.z, 9))
                        # Добавляем ребро только если его ещё нет
                        if key1 not in seen_edges and key2 not in seen_edges:
                            seen_edges.add(key1)
                            self.edges.append(Edge(v1, v2, orig_v1, orig_v2))
                    # задание самой грани
                    self.facets.append(Facet(vertexes))

    # Проверка, является ли проекция точки «хорошей»
    @staticmethod
    def is_good_point(p):
        return p.x * p.x + p.y * p.y > 1.0

    # Сумма длин рёбер, у которых середина и оба конца — «хорошие» точки
    def good_edges_length_sum(self):
        total = 0.0
        total_all = 0.0
        for e in self.edges:
            edge_len = e.length()
            total_all += edge_len
            mid = R3((e.beg.x + e.fin.x) / 2,
                     (e.beg.y + e.fin.y) / 2,
                     (e.beg.z + e.fin.z) / 2)
            if (self.is_good_point(e.beg) and
                    self.is_good_point(e.fin) and
                    self.is_good_point(mid)):
                total += edge_len
        # Проверка, что сумма не превышает общую сумму
        assert total <= total_all + 1e-9
        return total

    # Метод изображения полиэдра
    def draw(self, tk):  # pragma: no cover
        tk.clean()
        for e in self.edges:
            for f in self.facets:
                e.shadow(f)
            for s in e.gaps:
                tk.draw_line(e.r3(s.beg), e.r3(s.fin))
        # Вывод суммы длин «хороших» рёбер
        result = self.good_edges_length_sum()
        print(
            f"Сумма длин рёбер с «хорошими» концами и серединой: {result:.6f}")
        print(f"Всего рёбер в полиэдре: {len(self.edges)}")
