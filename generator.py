import io
import math
import random
from numbers import Number

from PIL import Image  # Importing Pillow (Image Library)
import cairo

from dataclasses import dataclass

# black is used to indicate an area a maze can be generated in,
# white is where a maze cannot be generated (i.e. a wall must be put there)
# pink should be placed on image borders and specifies where start and end points are
MAZE_CAN_GENERATE_COLOUR = (0, 0, 0)
ENTRANCES_COLOUR = (255, 0, 255)
EXITS_COLOUR = (0, 255, 255)

HEAD_SIZE = 0.2


class MaskError(Exception):
    """Raised when an error is found in a mask image file"""


@dataclass
class Vec2D:
    x: Number
    y: Number

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, other):
        if isinstance(other, Vec2D):
            return self.__class__(x=self.x + other.x, y=self.y + other.y)
        else:
            raise ValueError()

    def __sub__(self, other):
        if isinstance(other, Vec2D):
            return self.__class__(x=self.x - other.x, y=self.y - other.y)

    def __iter__(self):
        yield self.x
        yield self.y

    def __mul__(self, other):
        if isinstance(other, Number):
            return Vec2D(x=other * self.x, y=other * self.y)
        else:
            raise ValueError

    def __hash__(self):
        return hash(f"({self.x},{self.y})")

    def get_perpendicular(self):
        return self.__class__(x=-self.y, y=self.x)

    @classmethod
    def directions(cls):
        return tuple(cls(*v) for v in ((0, 1), (1, 0), (0, -1), (-1, 0)))


class Cell(Vec2D):
    """Represents the coordinates of a cell"""


class Pixel(Vec2D):
    """Represents the coordinates of a pixel in the maze mask"""


class MazeGenerator:
    """Represents a maze before generating
    call the .generate() method to generate a maze to svg"""

    def __init__(self, mask: Image.Image, rows: int, cols: int):
        self.mask = mask
        self.rows = rows
        self.cols = cols

        self.adjacency_dict = {}  # initailises an empty adjacency dictionary
        for x in range(mask.width):
            for y in range(mask.height):
                cur_pixel = Pixel(x, y)
                if mask.getpixel(tuple(cur_pixel)) == MAZE_CAN_GENERATE_COLOUR:
                    cur_cell = self.pixel_to_cell(cur_pixel)
                    self.adjacency_dict[cur_cell] = []
        for k in self.adjacency_dict.keys():
            neighbours = [k + v for v in Cell.directions()]
            for n in neighbours:
                if n in self.adjacency_dict.keys():
                    self.adjacency_dict[k].append(n)
        self.entrances = self.get_entrances()

    def generate(self, seed: int = None, colour=(0, 0, 0), pen_width=0.1):
        if seed is not None:
            random.seed(seed)

        # choose any arbitary cell in the maze
        # as all cells will be connected once the algorithm has completed, this
        # starting cell can be any of the cells in the maze
        todo = [next(iter(self.adjacency_dict.keys()))]

        maze_adj_dict = self.adjacency_dict.copy()
        for k in maze_adj_dict:
            maze_adj_dict[k] = []

        visited = set()

        while len(todo) > 0:
            current_cell = todo[0]
            visited.add(current_cell)
            unvisited_neighbours = [n for n in self.adjacency_dict[current_cell]
                                    if n not in visited]

            if len(unvisited_neighbours) == 0:
                todo.pop(0)
            else:
                neighbour = random.choice(unvisited_neighbours)

                maze_adj_dict[current_cell].append(neighbour)
                maze_adj_dict[neighbour].append(current_cell)

                todo.insert(0, neighbour)

        maze_io = io.BytesIO()
        scale = 10
        with cairo.SVGSurface(maze_io, scale * (self.cols + 2), scale * (self.rows + 2)) as maze_surface:
            context = cairo.Context(maze_surface)
            context.scale(scale, scale)
            context.translate(1, 1)
            context.set_line_width(pen_width)
            context.set_source_rgb(*colour)
            context.set_line_cap(cairo.LINE_CAP_ROUND)
            context.set_line_join(cairo.LINE_JOIN_ROUND)

            for cell, neighbours in maze_adj_dict.items():
                theoretical_neighbours = [cell + v for v in Cell.directions()]
                for n in theoretical_neighbours:
                    if self.entrances.get(cell, None) == n or self.entrances.get(n, None) == cell:
                        continue
                    elif n not in neighbours and self.entrances.get(cell, None) != n:
                        self.draw_wall(cell, n, context)
            context.stroke()
            for cell, neighbour in self.entrances.items():
                print(cell, neighbour)
                self.draw_arrow(cell, neighbour - cell, context)
                context.stroke()
        return maze_io

    @staticmethod
    def draw_arrow(cell: Cell, direction: Vec2D, context: cairo.Context, colour=(255, 0, 0)):
        if direction not in direction.__class__.directions():
            raise ValueError("direction is not a valid cardinal direction")
        context.move_to(*cell)
        context.line_to(*(cell + direction))
        perp = direction.get_perpendicular()
        arrow_head_left = (perp + direction * 4) * 0.2
        arrow_head_right = (direction * 4 - perp) * 0.2
        context.line_to(*(cell + arrow_head_right))
        context.move_to(*(cell + direction))
        context.line_to(*(cell + arrow_head_left))

        orig_source = None
        if colour is not None:
            orig_source = context.get_source()
            context.set_source_rgb(*colour)

        context.stroke()

        if orig_source is not None:
            context.set_source(orig_source)

        print(cell)

    @staticmethod
    def draw_wall(start_cell: Cell, end_cell: Cell, context: cairo.Context):
        start_to_end = end_cell - start_cell
        wall_vec = start_to_end.get_perpendicular()
        start = start_cell + (start_to_end - wall_vec) * 0.5
        end = start_cell + (start_to_end + wall_vec) * 0.5

        context.move_to(*start)
        context.line_to(*end)

    def get_entrances(self) -> dict[Cell, Cell]:
        entrances = {}
        for i, col in enumerate(self.mask.getdata()):
            if col == ENTRANCES_COLOUR or col == EXITS_COLOUR:
                pixel = Pixel(*reversed(divmod(i, self.mask.width)))
                if pixel.y == 0:  # entrance is on top of maze
                    v = Cell(0, 1)
                elif pixel.x == 0:  # entrance is to left of maze
                    v = Cell(1, 0)
                elif pixel.y == self.mask.height - 1:  # entrance is below maze
                    v = Cell(0, -1)
                elif pixel.x == self.mask.width - 1:  # entrance is to right of maze
                    v = Cell(-1, 0)
                else:
                    raise MaskError("Entrance found not on border of image")

                cell = None
                while self.is_pixel_in_image(pixel):
                    if self.pixel_to_cell(pixel) in self.adjacency_dict.keys():
                        cell = self.pixel_to_cell(pixel)
                        break
                    pixel += v

                if cell is None:
                    raise MaskError("Entrance did not produce a valid cell")

                if col == ENTRANCES_COLOUR:
                    entrances[cell - v] = cell
                if col == EXITS_COLOUR:
                    entrances[cell] = cell - v
        print(entrances)
        return entrances

    def cell_to_pixel(self, cell: Cell) -> Pixel:
        (x, y) = cell
        new_x = ((x + 0.5) * self.mask.width) / self.cols
        new_y = ((y + 0.5) * self.mask.height) / self.rows

        return Pixel(x=new_x, y=new_y)

    def pixel_to_cell(self, pixel: Pixel) -> Cell:
        return Cell((pixel.x * self.cols) // self.mask.width,
                    (pixel.y * self.rows) // self.mask.height)

    def is_pixel_in_image(self, pixel: Pixel) -> bool:
        if min(pixel) < 0:
            return False
        if pixel.x > self.mask.width - 1:
            return False
        if pixel.y > self.mask.height - 1:
            return False
        return True


if __name__ == "__main__":
    dino_mask = Image.open("static/maze_0.png").convert("RGB")
    number_rows = 25  # arbitrary number chosen to test generation

    # approximates square cells by making the ratio of rows to columns equal to
    # the ratio of width to height of image (approximated to the nearest integer)
    number_cols = (number_rows * dino_mask.width) // dino_mask.height

    maze_template = MazeGenerator(dino_mask, number_rows, number_cols)
    m = maze_template.generate()
    with open("s.svg", "wb") as f:
        f.write(m.getbuffer())
