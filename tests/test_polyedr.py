# test_polyedr.py
import pytest
import os
import tempfile
from math import sqrt
from shadow.polyedr import Polyedr, R3, Edge


class TestGoodEdges:
    """Тесты для проверки суммы длин «хороших» рёбер"""

    @pytest.fixture
    def temp_geom_file(self):
        """Фикстура для создания временных .geom файлов"""
        def create_file(content):
            with tempfile.NamedTemporaryFile(
                    mode='w', suffix='.geom', delete=False) as f:
                f.write(content)
                return f.name
        return create_file

    def test_all_good_square(self, temp_geom_file):
        """Квадрат, все точки которого «хорошие» (вне окружности)"""
        # Используем только 4 ребра квадрата, без дублирования
        content = """1.0 0 0 0
4 1 4
2.0 0.0 0.0
0.0 2.0 0.0
-2.0 0.0 0.0
0.0 -2.0 0.0
4 1 2 3 4"""
        filename = temp_geom_file(content)
        try:
            p = Polyedr(filename)
            total = p.good_edges_length_sum()
            # Сторона квадрата = 2√2, периметр = 8√2 ≈ 11.313708
            expected = 8 * sqrt(2)
            assert abs(total - expected) < 1e-6
        finally:
            os.unlink(filename)

    def test_no_good_cube_inside_circle(self, temp_geom_file):
        """Куб, полностью внутри окружности — сумма должна быть 0"""
        content = """1.0 0 0 0
8 6 12
0.5 0.5 0.5
0.5 -0.5 0.5
-0.5 -0.5 0.5
-0.5 0.5 0.5
0.5 0.5 -0.5
0.5 -0.5 -0.5
-0.5 -0.5 -0.5
-0.5 0.5 -0.5
4 1 2 3 4
4 5 8 7 6
4 1 5 6 2
4 2 6 7 3
4 3 7 8 4
4 4 8 5 1"""
        filename = temp_geom_file(content)
        try:
            p = Polyedr(filename)
            total = p.good_edges_length_sum()
            assert total == 0.0
        finally:
            os.unlink(filename)

    def test_partial_good_rectangle(self, temp_geom_file):
        """Прямоугольник, где только одно ребро полностью «хорошее»"""
        content = """1.0 0 0 0
4 1 4
3.0 0.0 0.0
0.0 3.0 0.0
-0.5 0.0 0.0
0.0 -0.5 0.0
4 1 2 3 4"""
        filename = temp_geom_file(content)
        try:
            p = Polyedr(filename)
            total = p.good_edges_length_sum()

            # Рёбра: (1,2), (2,3), (3,4), (4,1)
            # Точка 1: (3,0) - хорошая
            # Точка 2: (0,3) - хорошая
            # Точка 3: (-0.5,0) - нехорошая
            # Точка 4: (0,-0.5) - нехорошая

            # Только ребро (1,2) полностью хорошее
            expected = sqrt(3**2 + 3**2)  # √18 ≈ 4.242640687
            assert abs(total - expected) < 1e-6
        finally:
            os.unlink(filename)

    def test_edge_on_circle_border(self, temp_geom_file):
        """Ребро точно на границе окружности (не считается «хорошим»)"""
        content = """1.0 0 0 0
2 1 1
1.0 0.0 0.0
0.0 1.0 0.0
2 1 2"""
        filename = temp_geom_file(content)
        try:
            p = Polyedr(filename)
            total = p.good_edges_length_sum()
            # Точки (1,0) и (0,1) лежат на окружности x²+y²=1
            # Условие строгое: > 1, поэтому сумма = 0
            assert total == 0.0
        finally:
            os.unlink(filename)

    def test_midpoint_not_good(self, temp_geom_file):
        """Ребро с «хорошими» концами, но середина внутри окружности"""
        content = """1.0 0 0 0
2 1 1
2.0 0.0 0.0
-2.0 0.0 0.0
2 1 2"""
        filename = temp_geom_file(content)
        try:
            p = Polyedr(filename)
            total = p.good_edges_length_sum()
            # Концы: (2,0) и (-2,0) - хорошие (4 > 1)
            # Середина: (0,0) - нехорошая (0 <= 1)
            assert total == 0.0
        finally:
            os.unlink(filename)

    def test_rotated_polyedr(self, temp_geom_file):
        """Проверка с поворотом (углы Эйлера)"""
        content = """1.0 0 0 90
4 1 4
2.0 0.0 0.0
0.0 2.0 0.0
-2.0 0.0 0.0
0.0 -2.0 0.0
4 1 2 3 4"""
        filename = temp_geom_file(content)
        try:
            p = Polyedr(filename)
            total = p.good_edges_length_sum()
            # Поворот на 90° вокруг Z не меняет расстояния в плоскости XY
            expected = 8 * sqrt(2)
            assert abs(total - expected) < 1e-6
        finally:
            os.unlink(filename)

    def test_scaled_polyedr(self, temp_geom_file):
        """Проверка с гомотетией"""
        content = """2.0 0 0 0
4 1 4
1.0 0.0 0.0
0.0 1.0 0.0
-1.0 0.0 0.0
0.0 -1.0 0.0
4 1 2 3 4"""
        filename = temp_geom_file(content)
        try:
            p = Polyedr(filename)
            total = p.good_edges_length_sum()
            # Исходный квадрат со стороной √2 масштабируется в 2 раза
            # Получаем квадрат со стороной 2√2, периметр = 8√2
            expected = 8 * sqrt(2)
            assert abs(total - expected) < 1e-6
        finally:
            os.unlink(filename)

    def test_edges_count_correct(self, temp_geom_file):
        """Проверка, что каждое ребро считается только один раз"""
        # Простой треугольник
        content = """1.0 0 0 0
3 1 3
2.0 0.0 0.0
0.0 2.0 0.0
0.0 0.0 0.0
3 1 2 3"""
        filename = temp_geom_file(content)
        try:
            p = Polyedr(filename)
            # Проверяем количество рёбер
            assert len(p.edges) == 3

            total = p.good_edges_length_sum()

            # Только рёбра (1,2) полностью хорошее
            p1 = R3(2.0, 0.0, 0.0)
            p2 = R3(0.0, 2.0, 0.0)
            expected = sqrt(8)  # 2√2 ≈ 2.828

            assert abs(total - expected) < 1e-6
        finally:
            os.unlink(filename)


class TestIsGoodPoint:
    """Тесты для проверки метода is_good_point"""

    def test_good_points(self):
        assert Polyedr.is_good_point(R3(2.0, 0.0, 0.0))
        assert Polyedr.is_good_point(R3(0.0, 2.0, 0.0))
        assert Polyedr.is_good_point(R3(1.0, 1.0, 0.0))  # x²+y²=2 > 1
        assert Polyedr.is_good_point(R3(1.1, 0.0, 0.0))  # 1.21 > 1

    def test_not_good_points(self):
        assert not Polyedr.is_good_point(R3(0.0, 0.0, 0.0))
        assert not Polyedr.is_good_point(R3(0.5, 0.5, 0.0))  # 0.5 < 1
        assert not Polyedr.is_good_point(R3(1.0, 0.0, 0.0))  # на границе
        assert not Polyedr.is_good_point(R3(0.0, 1.0, 0.0))  # на границе
        assert not Polyedr.is_good_point(R3(0.6, 0.6, 0.0))  # 0.72 < 1


class TestEdgeLength:
    """Тесты для проверки вычисления длины ребра"""

    def test_horizontal_edge(self):
        e = Edge(R3(0.0, 0.0, 0.0), R3(3.0, 0.0, 0.0))
        assert abs(e.length() - 3.0) < 1e-6

    def test_vertical_edge(self):
        e = Edge(R3(1.0, 1.0, 1.0), R3(1.0, 1.0, 4.0))
        assert abs(e.length() - 3.0) < 1e-6

    def test_diagonal_edge(self):
        e = Edge(R3(0.0, 0.0, 0.0), R3(1.0, 1.0, 1.0))
        assert abs(e.length() - sqrt(3)) < 1e-6

    def test_negative_coordinates(self):
        e = Edge(R3(-1.0, -1.0, -1.0), R3(-4.0, -1.0, -1.0))
        assert abs(e.length() - 3.0) < 1e-6


if __name__ == "__main__":  # pragma no cover
    pytest.main([__file__, "-v"])
