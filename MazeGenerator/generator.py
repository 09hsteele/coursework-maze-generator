import random

from PIL import Image  # Importing Pillow (Image Library)

# black is used to indicate an area a maze can be generated in,
# white is where a maze cannot be generated (i.e. a wall must be put there)
# pink should be placed on image borders and decides where start and end points are
MAZE_CAN_GENERATE_COLOUR = (0, 0, 0)
ENTRANCES_COLOUR = (255, 0, 255)


class EntranceNotFoundError(Exception):
    """raised when finding entrances, if an entrance pixel doesn't intersect with
    any cells in the maze"""


class EntrancePixelNotOnEdge(Exception):
    """raised if a pixel specifying an entrance is found not on the edge of the
    image"""


class MazeTemplate:
    """Represents a maze shape and size before generating"""

    def __init__(self, mask: Image.Image, rows: int, cols: int):
        self.mask = mask
        self.rows = rows
        self.cols = cols

        self.adjacency_dict = {}  # initailises an empty adjacency dictionary
        # this will contain (x,y) coords as keys and lists of adjacent (x,y) coords as values

        #  loop through each cell in the image
        for y in range(rows):
            for x in range(cols):

                cur_pixel = self.cell_to_pixel((x, y))

                if mask.getpixel(cur_pixel) == MAZE_CAN_GENERATE_COLOUR:
                    # current pixel is not WHITE, it is in the maze
                    # so make an entry for it in adjacency_dict
                    self.adjacency_dict[(x, y)] = []

                    #  loop through possible neighbours,
                    #  check if connection is possible due to mask,
                    #  if it is, add it to list adjacency_dict[cur_pixel]
                    for neighbour_cell_coords in self.get_possible_adjacents((x, y)):
                        neighbour_pixel = self.cell_to_pixel(neighbour_cell_coords)
                        if self.can_connect(cur_pixel, neighbour_pixel):
                            self.adjacency_dict[(x, y)].append(neighbour_cell_coords)

    def generate(self, seed=None):
        if seed is not None:
            random.seed(seed)

        to_do = [next(iter(self.adjacency_dict.keys()))]
        # to_do list acts as a stack of cells to visit, initially containing an
        # arbitrary cell from adjacency_dict, as all cells should be connected,
        # the initial cell is unimportant. By the end of generation, all cells
        # will be connected.

        maze_image = Image.new("RGB", (self.mask.width + 1, self.mask.height + 1), (255, 255, 255))

        maze_adj_dict = self.adjacency_dict.copy()
        # taking this as a copy means that only cells inside the mask shape can
        # be considered

        for key in maze_adj_dict.keys():
            maze_adj_dict[key] = []
        # populate adjacency dict with empty lists

        visited = set()  # the set of points (as (x, y) tuples) that have already
        # been visited by the algorithm

        while len(to_do) > 0:
            current = to_do[0]
            visited.add(current)

            unvisited_neighbours = [n for n in self.adjacency_dict[current]
                                    if n not in visited]
            if len(unvisited_neighbours) == 0:  # no unvisited neighbours
                # cell is completely explored
                to_do.pop(0)  # remove from stack
            else:
                neighbour = random.choice(unvisited_neighbours)
                # choose a random neighbour and continue traversal

                maze_adj_dict[current].append(neighbour)
                maze_adj_dict[neighbour].append(current)
                #  if A is connected to B, B must also be connected to A (undirected)

                to_do.insert(0, neighbour)  # push new cell to stack

        entrances = self.get_entrances()

        for cell, neighbours in maze_adj_dict.items():
            theoretical_neighbours = get_theoretical_adjacents(cell)
            for n in theoretical_neighbours:
                if n not in maze_adj_dict[cell] and entrances.get(cell, None) != n:
                    self.draw_wall(cell, n, maze_image)
        return maze_image

    def draw_wall(self, start_cell, end_cell, image: Image.Image, colour=(0, 0, 0)):
        cell_height = self.mask.height / self.rows
        cell_width = self.mask.width / self.cols

        if start_cell[0] == end_cell[0]:  # cells lie on same horizontal line
            cell_x = start_cell[0]
            y = int((cell_height * (start_cell[1] + end_cell[1] + 1)) // 2)
            for x in range(int(cell_x * cell_width), int((cell_x + 1) * cell_width)):
                image.putpixel((x, y), colour)

        elif start_cell[1] == end_cell[1]:  # cells lie on same horizontal line
            cell_y = start_cell[1]
            x = int((cell_width * (start_cell[0] + end_cell[0] + 1)) // 2)
            for y in range(int(cell_y * cell_height), int((cell_y + 1) * cell_height)):
                image.putpixel((x, y), colour)

        else:
            return ValueError(f"cells {start_cell} and {end_cell} are not adjacent")

    def cell_to_pixel(self, cell_coords: tuple[int, int]) -> tuple[int, int]:
        """Finds the pixel coordinates for a given cell coordinate
        :returns: (pixel_x, pixel_y) tuple """

        cell_width = self.mask.width / self.cols
        cell_height = self.mask.height / self.rows

        (x, y) = cell_coords

        # add 0.5 to shift from top-left corner to centre of cell
        pixel_x = int((x + 0.5) * cell_width)
        pixel_y = int((y + 0.5) * cell_height)

        return pixel_x, pixel_y

    def can_connect(self, pixel_a: tuple[int, int], pixel_b: tuple[int, int]) -> bool:
        """decides whether two image points pixel_a and pixel_b can be connected
        according to the image mask"""
        # Currently only works when points share an x or y coordinate

        if pixel_a[0] == pixel_b[0]:  # both pixels lie on the same vertical line
            # loops through the smallest y coordinate to the largest y coordinate
            for y in range(min(pixel_a[1], pixel_b[1]), max(pixel_a[1], pixel_b[1]) + 1):
                if self.mask.getpixel((pixel_a[0], y)) != MAZE_CAN_GENERATE_COLOUR:
                    return False

        elif pixel_a[1] == pixel_b[1]:  # both pixels lie on the same horizontal line
            # loops through the smallest x coordinate to the largest x coordinate
            for x in range(min(pixel_a[0], pixel_b[0]), max(pixel_a[0], pixel_b[0]) + 1):
                if self.mask.getpixel((x, pixel_b[1])) != MAZE_CAN_GENERATE_COLOUR:
                    return False
        else:
            raise NotImplementedError()

        return True  # no white pixels found, so points must be connected

    def debug_connect(self, pixel_a, pixel_b):
        if pixel_a[0] == pixel_b[0]:  # both pixels lie on the same vertical line
            # loops through the smallest y coordinate to the largest y coordinate
            for y in range(min(pixel_a[1], pixel_b[1]), max(pixel_a[1], pixel_b[1])):
                self.mask.putpixel((pixel_a[0], y), (255, 0, 255))

        elif pixel_a[1] == pixel_b[1]:  # both pixels lie on the same horizontal line
            # loops through the smallest x coordinate to the largest x coordinate
            for x in range(min(pixel_a[0], pixel_b[0]), max(pixel_a[0], pixel_b[0])):
                self.mask.putpixel((x, pixel_b[1]), (255, 0, 255))
        else:
            raise NotImplementedError()

    def get_possible_adjacents(self, cell_coords):
        """Deals with boundary cases of x and y being at edges/corners of cell grid
        :returns: a list of (x,y) tuples representing cell coordinates of neighbours"""
        return [(x, y) for (x, y) in get_theoretical_adjacents(cell_coords) if
                0 <= x < self.cols and 0 <= y < self.rows]
        # filters theoretical adjacents only keeping those in the image

    def get_entrances(self) -> dict[tuple[int, int], tuple[int, int]]:
        """finds a list of connections that walls should not be drawn at as these
        are the start/end points of the maze
        :returns: a dictionary with (x, y) tuple keys, and (x, y) tuple values,
        the connection between key cells and value cells should be open to act
        as an entrance"""
        entrances = {}
        for i, colour in enumerate(self.mask.getdata()):
            if colour == ENTRANCES_COLOUR:
                (pixel_y, pixel_x) = divmod(i, self.mask.width)
                cell_x, cell_y = ((pixel_x * self.cols) // self.mask.width,
                                  (pixel_y * self.rows) // self.mask.height)
                if pixel_y == 0:  # entrance is on top of maze
                    while (cell_x, cell_y) not in self.adjacency_dict:
                        cell_y += 1
                        if cell_y >= self.rows:
                            #  could not find cell in line with entrance
                            raise EntranceNotFoundError(f"pixel ({pixel_x}, {pixel_y})"
                                                        "did not produce a valid entrance")
                    entrances[(cell_x, cell_y)] = (cell_x, cell_y - 1)
                elif pixel_x == 0:  # entrance is on left side of maze
                    while (cell_x, cell_y) not in self.adjacency_dict:
                        cell_x += 1
                        if cell_x >= self.cols:
                            #  could not find cell in line with entrance
                            raise EntranceNotFoundError(f"pixel ({pixel_x}, {pixel_y})"
                                                        "did not produce a valid entrance")
                    entrances[(cell_x, cell_y)] = (cell_x - 1, cell_y)
                elif pixel_y == self.mask.height-1:  # entrance is on bottom of maze
                    while (cell_x, cell_y) not in self.adjacency_dict:
                        cell_y -= 1
                        if cell_y < 0:
                            #  could not find cell in line with entrance
                            raise EntranceNotFoundError(f"pixel ({pixel_x}, {pixel_y})"
                                                        "did not produce a valid entrance")
                    entrances[(cell_x, cell_y)] = (cell_x, cell_y + 1)
                elif pixel_x == self.mask.width-1:  # entrance is to right of maze
                    while (cell_x, cell_y) not in self.adjacency_dict:
                        cell_x -= 1
                        if cell_x < 0:
                            #  could not find cell in line with entrance
                            raise EntranceNotFoundError(f"pixel ({pixel_x}, {pixel_y})"
                                                        "did not produce a valid entrance")
                    entrances[(cell_x, cell_y)] = (cell_x + 1, cell_y)
                else:
                    raise EntrancePixelNotOnEdge(f"pixel ({pixel_x}, {pixel_y}) not on edge")
        return entrances


def get_theoretical_adjacents(cell_coords: tuple[int, int]) -> list[tuple[int, int]]:
    """finds adjacent cells (including those with coordinates outside the image)
    :returns: a list of (x, y) tuples representing cell coordinates of neighbours"""
    (x, y) = cell_coords
    return [
        (x + 1, y),  # right
        (x - 1, y),  # left
        (x, y + 1),  # below
        (x, y - 1)  # above
    ]


if __name__ == "__main__":
    dino_mask = Image.open("maze_masks/dino_mask.png").convert("RGB")
    number_rows = 15  # arbitrary number chosen to test generation

    # approximates square cells by making the ratio of rows to columns equal to
    # the ratio of width to height of image (approximated to the nearest integer)
    number_cols = (number_rows * dino_mask.width) // dino_mask.height

    maze_template = MazeTemplate(dino_mask, number_rows, number_cols)
    m = maze_template.generate()
    m.show()
    m.save("output.png")
