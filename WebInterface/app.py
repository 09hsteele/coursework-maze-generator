from flask import *
from PIL import Image
from MazeGenerator import generator
from io import BytesIO

app = Flask(__name__)


@app.route('/')
def index():
    return render_template("index.html", username="", mazes=mazes)


@app.route("/generate.html")
def generate_ui():
    try:
        shape = validate_integer(request.args.get("maze_shape"), 0, len(mazes) - 1)
    except:
        return abort(400)
    print(shape)
    print(mazes[shape])

    return render_template("generate.html", shapeID=shape, mazes=mazes)


@app.route("/generated_maze.png")
def generate_maze():
    shape = validate_integer(request.args.get("maze_shape"), 0, len(mazes) - 1)
    n_cols = validate_integer(request.args.get("maze_size"), 1)
    mask = Image.open(f"WebInterface/static/maze_{shape}.png").convert("RGB")
    n_rows = (n_cols * mask.height) // mask.width  # approximate square cells
    maze = generator.MazeTemplate(mask, n_rows, n_cols).generate()

    #  using io object to serve png file, this way it doesn't need to be saved to disk
    img_io = BytesIO()
    maze.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype="image/png")


def validate_integer(i: str, min_value: int = None, max_value: int = None) -> int:
    """
    :param i: the number to validate
    :param min_value: the smallest acceptable value of i, can be None (no limit)
    :param max_value: the largest acceptable value of i, can be None (no limit)
    :returns: int(i) if i is an integer between given parameters (inclusive),
        otherwise raises a ValueError
    """
    # TODO: add error descriptions
    try:
        i = int(i)
    except (ValueError, TypeError) as e:
        raise e
    if min_value is not None:
        if i < min_value:
            raise ValueError
    if max_value is not None:
        if i > max_value:
            raise ValueError
        if min_value is not None:
            if max_value < min_value:
                raise ValueError
    return i


@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')


mazes = [("Triceratops",), ("Fish",), ("Rabbit",), ("Wolf",), ("Box",)]

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
