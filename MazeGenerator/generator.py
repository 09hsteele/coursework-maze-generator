import random

from PIL import Image  # Importing Pillow (Image Library)

# BLACK is used to indicate an area a maze can be generated in,
# WHITE is where a maze cannot be generated (i.e. a wall must be put there)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def can_connect(mask: Image.Image, pixel_a: tuple[int, int], pixel_b: tuple[int, int]) -> bool:
    """decides whether two image points pixel_a and pixel_b can be connected"""
    # Currently only works when points have the same x or y coordinate

    if pixel_a[0] == pixel_b[0]:  # both pixels lie on the same vertical line
        # loops through the smallest y coordinate to the largest y coordinate
        for y in range(min(pixel_a[1], pixel_b[1]), max(pixel_a[1], pixel_b[1])+1):
            if mask.getpixel((pixel_a[0], y))[:3] == WHITE:
                return False

    elif pixel_a[1] == pixel_b[1]:  # both pixels lie on the same horizontal line
        # loops through the smallest x coordinate to the largest x coordinate
        for x in range(min(pixel_a[0], pixel_b[0]), max(pixel_a[0], pixel_b[0])+1):
            if mask.getpixel((x, pixel_b[1]))[:3] == WHITE:
                return False
    else:
        raise ValueError

    return True  # no white pixels found, so points must be connected


def get_possible_adjacents(x: int, y: int, rows: int, cols: int) -> list[(int, int)]:
    """Deals with boundary cases of x and y being at edges/corners of cell grid
    :returns: a list of (x,y) tuples representing cell coordinates of neighbours"""
    neighbours = []
    if x > 0:  # cell not at far left edge (left neighbour possible)
        neighbours.append((x-1, y))
    if x < rows-1:  # cell not at far right edge (right neighbour possible)
        neighbours.append((x+1, y))
    if y > 0:
        neighbours.append((x, y-1))
    if y < cols-1:
        neighbours.append((x, y+1))
    return neighbours


def cell_to_pixel(x_or_y: int, width_or_height: float) -> int:
    """finds the pixel coordinate of a cell coordinate from its cell coordinate
    if x is passed as the first parameter, the width should be the second
    and likewise for y and height"""
    #  0.5 is added to x and y to go from top-left corner of cell to centre
    return int(width_or_height * (x_or_y+0.5))


def debug_connect(img, pixel_a, pixel_b):
    if pixel_a[0] == pixel_b[0]:  # both pixels lie on the same vertical line
        # loops through the smallest y coordinate to the largest y coordinate
        for y in range(min(pixel_a[1], pixel_b[1]), max(pixel_a[1], pixel_b[1])):
            img.putpixel((pixel_a[0], y), BLACK)

    elif pixel_a[1] == pixel_b[1]:  # both pixels lie on the same horizontal line
        # loops through the smallest x coordinate to the largest x coordinate
        for x in range(min(pixel_a[0], pixel_b[0]), max(pixel_a[0], pixel_b[0])):
            img.putpixel((x, pixel_b[1]), BLACK)
    else:
        raise ValueError


def generate_maze_from_mask(mask: Image.Image, rows: int, cols: int, seed=None):
    cell_width = mask.width / rows
    cell_height = mask.height / cols  # width and height of one cell, might not be whole number
    adjacency_dict = {}  # initailises an empty adjacency dictionary
    # will contain (x,y) coords as keys and lists of adjacent (x,y) coords as values

    maze = Image.new("RGB", mask.size, WHITE)

    for y in range(cols):
        for x in range(rows):

            # converts cell coords to coords of pixels in centre of cells
            cur_pixel = (cell_to_pixel(x, cell_width), cell_to_pixel(y, cell_height))

            if mask.getpixel(cur_pixel) != WHITE:
                # current pixel is not WHITE, it is in the maze
                # so put it in adjacency_dict
                adjacency_dict[(x, y)] = []

                #  loop through possible neighbours, check is connection is possible,
                #  if it is, add neighbour to the list adjacency_dict[(x,y)]
                for (neighbour_x, neighbour_y) in get_possible_adjacents(x, y, rows, cols):
                    neighbour_pixel = (cell_to_pixel(neighbour_x, cell_width),
                                       cell_to_pixel(neighbour_y, cell_height))
                    if can_connect(mask, cur_pixel, neighbour_pixel):
                        adjacency_dict[(x, y)].append((neighbour_x, neighbour_y))
                        # debug_connect(maze, cur_pixel, neighbour_pixel)

    generate_maze_from_graph(maze, adjacency_dict, cell_width, cell_height, seed)

    return maze


def generate_maze_from_graph(img, adjacency_dict, cell_width, cell_height, seed=None):
    if seed is not None:
        random.seed(seed)
    to_do = [next(iter(adjacency_dict))]  # this list acts as a stack of cells to explore
    # any root can be chosen, assuming all nodes are connected
    # by the end of generation, all cells will be connected.
    visited = set()  # the set of points that have already been visited.
    while len(to_do) > 0:
        current = to_do[0]
        visited.add(current)
        unvisited_neighbours = [n for n in adjacency_dict[current] if n not in visited]
        if len(unvisited_neighbours) == 0:  # no unvisited neighbours, cell completely explored
            to_do.pop(0)
        else:
            neighbour = random.choice(unvisited_neighbours)  # pick a random neighbour to continue traversal
            debug_connect(img, (cell_to_pixel(neighbour[0], cell_width),
                          cell_to_pixel(neighbour[1], cell_height)),
                          (cell_to_pixel(current[0], cell_width),
                           cell_to_pixel(current[1], cell_height)))

            to_do.insert(0, neighbour)  # push new cell to stack


if __name__ == "__main__":
    dino_mask = Image.open("maze_masks/dino_mask.png").convert("RGB")
    number_rows = 30  # arbitrary number chosen for testing purposes

    # approximates square cells by making the ratio of rows to columns equal to
    # the ratio of width to height of image
    number_cols = (number_rows * dino_mask.height) // dino_mask.width

    dino_maze = generate_maze_from_mask(dino_mask, number_rows, number_cols)
    dino_maze.show()
    dino_maze.save("tmp.png")
