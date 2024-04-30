import io
import random
from numbers import Number

from PIL import Image, ImageDraw  # Importing Pillow (Image Library)
import cairo

from dataclasses import dataclass

# black is used to indicate an area a maze can be generated in,
# white is where a maze cannot be generated (i.e. a wall must be put there)
# pink should be placed on image borders and specifies where start and end points are
MAZE_CAN_GENERATE_COLOUR = (0, 0, 0)
MAZE_CANNOT_GENERATE_COLOUR = (255, 255, 255)
ENTRANCES_COLOUR = (255, 0, 255)
EXITS_COLOUR = (0, 255, 255)
MAX_MASK_SIZE = 20_000  # masks over 20KB are not allowed (for performance reasons)


class MaskError(Exception):
    """Raised when an error is found in a mask image file"""


class NoEntrancesError(MaskError):
    """Raised when given a mask with no entrances"""


def validate_mask(mask: Image.Image):
    mask_copy = mask.copy()  # create a copy of the maze for checking for blocks of pixels

    # flags of things that we need to check
    entrance_found = False
    exit_found = False
    maze_found = False

    if mask.width <= 3 or mask.height <= 3:
        raise MaskError(f"Mask image too small")

    for i, col in enumerate(mask.getdata()):
        (y, x) = divmod(i, mask.width)
        if col == ENTRANCES_COLOUR:
            if entrance_found:
                raise MaskError(f"Found more than pixel of colour {ENTRANCES_COLOUR}")
            if is_entrance_valid(x, y, mask):
                entrance_found = True
        elif col == EXITS_COLOUR:
            if exit_found:
                raise MaskError(f"Found more than pixel of colour {EXITS_COLOUR}")
            if is_entrance_valid(x, y, mask):
                exit_found = True
        elif mask_copy.getpixel((x, y)) == MAZE_CAN_GENERATE_COLOUR:  # current pixel is black in the mask copy
            if not maze_found:  # program is yet to encounter a black pixel
                # Fill the connected black pixels with white. If we later find more black pixels, they must be
                # disconnected
                ImageDraw.floodfill(mask_copy, (x, y), MAZE_CANNOT_GENERATE_COLOUR)
                maze_found = True
            else:  # program has already found a black pixel, so this one must be disconnected
                raise MaskError(f"found disconnected part of maze at {(x, y)}")
        elif col != MAZE_CANNOT_GENERATE_COLOUR and col != MAZE_CAN_GENERATE_COLOUR:
            #  pixel is not one of the allowed colours
            raise MaskError(f"found pixel with colour {col} at {(x, y)}")
    if not entrance_found and not exit_found:
        raise NoEntrancesError("Mask has no entrances")
    if not entrance_found:
        raise MaskError(f"Could not find a pixel with colour {ENTRANCES_COLOUR}")
    if not exit_found:
        raise MaskError(f"Could not find a pixel with colour {EXITS_COLOUR}")
    if not maze_found:
        raise MaskError(f"Found not find any {MAZE_CAN_GENERATE_COLOUR} colour pixels")


def is_entrance_valid(x: int, y: int, mask: Image.Image):
    """Determines if an entrance indicator pixel will produce a valid entrance by checking if it would intersect with
    the maze.
    Raises a :class:`MaskError` if entrance is invalid

    :param x: The x-coordinate of the entrance pixel to consider
    :param y: The y-coordinate of the entrance pixel to consider
    :param mask: The mask image to check
    """
    p = Pixel(x, y)
    if y == 0:
        v = Pixel(0, 1)
    elif y == mask.height - 1:
        v = Pixel(0, -1)
    elif x == 0:
        v = Pixel(1, 0)
    elif x == mask.width - 1:
        v = Pixel(-1, 0)
    else:
        raise MaskError(f"entrance/exit pixel found at {(x, y)}, not on edge")
    while 0 <= p.x < mask.width and 0 <= p.y < mask.height:
        if mask.getpixel(tuple(p)) == MAZE_CAN_GENERATE_COLOUR:
            return True
        p += v
    raise MaskError(f"entrance/exit pixel at {(x, y)} did not intersect with maze")


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
    """Represents the logical coordinates of a cell in the maze grid"""


class Pixel(Vec2D):
    """Represents the coordinates of a pixel in the maze mask"""


class MazeGenerator:
    """Represents a maze before generating
    call the .generate() method to generate a maze to svg"""

    def __init__(self, mask: Image.Image, rows: int, cols: int):
        """
        Create a MazeGenerator object
        :param mask: The mask to use.
            It should be entirely black and white with one magenta and one aqua
            pixel on the border to indicate the entrance and exit
        :param rows: the number of cells vertically
        :param cols: the number of cells horizontally
        """
        self.mask = mask
        self.rows = rows
        self.cols = cols

        self.entrances = {}
        entrance_pixels = []  # list to keep track of entrances, these can
        # only be found once the whole adjacency dict has been created

        self.adjacency_dict = {}  # initialises an empty adjacency dictionary
        for x in range(mask.width):
            for y in range(mask.height):
                cur_pixel = Pixel(x, y)
                col = mask.getpixel(tuple(cur_pixel))
                if col == MAZE_CAN_GENERATE_COLOUR:
                    cur_cell = self.pixel_to_cell(cur_pixel)
                    self.adjacency_dict[cur_cell] = []
                elif col == ENTRANCES_COLOUR or col == EXITS_COLOUR:
                    entrance_pixels.append(cur_pixel)
        for k in self.adjacency_dict.keys():
            neighbours = [k + v for v in Cell.directions()]
            for n in neighbours:
                if n in self.adjacency_dict.keys():
                    self.adjacency_dict[k].append(n)
        self.find_entrances(entrance_pixels)

    def generate(self, seed: int = None, colour=(0, 0, 0), pen_width=0.1):
        if seed is not None:
            random.seed(seed)

        # choose any arbitrary cell in the maze
        # as all cells will be connected once the algorithm has completed, this starting cell can be any of the cells in
        # the maze
        todo = [next(iter(self.adjacency_dict.keys()))]

        maze_adj_dict = {}
        for k in self.adjacency_dict.keys():  # create a new adjacency dict that stores the connection between maze
            # cells. Starts with every cell in the maze being connected to no others (represented by an empty list)
            maze_adj_dict[k] = []

        visited = set()  # set of cells that have already been visited by the algorithm (should not be considered again)

        while len(todo) > 0:
            current_cell = todo[0]
            visited.add(current_cell)
            unvisited_neighbours = [n for n in self.adjacency_dict[current_cell]
                                    if n not in visited]

            if len(unvisited_neighbours) == 0:  # cell has no unvisited neighbours, so no reason to consider it further
                todo.pop(0)
            else:
                neighbour = random.choice(unvisited_neighbours)

                maze_adj_dict[current_cell].append(neighbour)
                maze_adj_dict[neighbour].append(current_cell)

                todo.insert(0, neighbour)

        maze_io = io.BytesIO()
        scale = 10  # the width/height of each cell
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
            context.set_source_rgb(255, 0, 0)
            for cell, neighbour in self.entrances.items():
                self.draw_arrow(cell, neighbour - cell, context)
                context.stroke()
        return maze_io

    @staticmethod
    def draw_arrow(cell: Cell, direction: Vec2D, context: cairo.Context):
        """
        draws an arrow in the specified direction between the specified cell and its adjacent

        :param cell: The cell to start the arrow at
        :param direction: The direction to draw the arrow
        :param context: The cairo context to draw the arrow on
        """
        if direction not in direction.__class__.directions():
            raise ValueError("direction is not a valid cardinal direction")
        perp = direction.get_perpendicular()
        arrow_head_left = (perp + direction * 4) * 0.2
        arrow_head_right = (direction * 4 - perp) * 0.2

        context.move_to(*cell)  # unpack the cell coordinates to be used as x, y arguments.
        context.line_to(*(cell + direction))
        context.line_to(*(cell + arrow_head_right))
        context.move_to(*(cell + direction))
        context.line_to(*(cell + arrow_head_left))

        context.stroke()  # draw the arrow

    @staticmethod
    def draw_wall(start_cell: Cell, end_cell: Cell, context: cairo.Context):
        """
        draws the wall between the two specified cells on the given context

        :param start_cell: The first cell to draw the wall between
        :param end_cell: The second cell to draw the wall between
        :param context:  The cairo context to draw the wall on
        """
        start_to_end = end_cell - start_cell
        wall_vec = start_to_end.get_perpendicular()
        start = start_cell + (start_to_end - wall_vec) * 0.5
        end = start_cell + (start_to_end + wall_vec) * 0.5

        context.move_to(*start)
        context.line_to(*end)

    def find_entrances(self, entrance_pixels: list[Pixel]):
        for pixel in entrance_pixels:
            col = self.mask.getpixel(tuple(pixel))
            if col == ENTRANCES_COLOUR or col == EXITS_COLOUR:
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

                cell = self.pixel_to_cell(pixel)
                # noinspection PyTypeChecker
                while 0 <= cell.x < self.cols and 0 <= cell.y < self.rows:
                    if cell in self.adjacency_dict.keys():
                        break
                    cell += v

                if col == ENTRANCES_COLOUR:
                    self.entrances[cell - v] = cell
                if col == EXITS_COLOUR:
                    self.entrances[cell] = cell - v

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
