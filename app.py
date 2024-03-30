import math
from io import BytesIO

from PIL import Image
from flask import *

import generator
import db

print(__import__("sys").path)

app = Flask(__name__)
database = db.Database("database.db")


@app.route('/maze_shapes')
def maze_list():
    return render_template("shape_list.html", username="", mazes=database.get_all_mazes())


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate")
def generate_ui():
    try:
        shape_id = validate_integer(request.args.get("maze_shape"), 0)
        maze = database.get_maze_from_id(shape_id)
    except Exception as e:
        print(e)
        # TODO: Better error pages
        return abort(400)
    print(maze)
    return render_template("generate.html", maze=maze)


@app.route("/generated_maze.png")
def generate_maze():
    shape_id = validate_integer(request.args.get("maze_shape"), 0)
    maze = database.get_maze_from_id(shape_id)
    size = validate_integer(request.args.get("maze_size"), 1)
    mask = Image.open(f"static/maze_{maze.MazeID}.png").convert("RGB")
    scale = int(math.sqrt((mask.width * mask.height) // size))
    n_rows = mask.height // scale
    n_cols = mask.width // scale  # approximate square cells
    maze = generator.MazeTemplate(mask, n_rows, n_cols).generate()

    #  using io object to serve png file, this way it doesn't need to be saved to disk
    img_io = BytesIO()
    maze.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype="image/png")


def validate_integer(i: str, min_value: int = None, max_value: int = None) -> int:
    """
    :param i: the number (as a string) to validate
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
    return i


@app.route('/signup')
def signup():
    if request.args.get("username") is not None:
        flash("Account created, please log in", "success")
        return redirect("/login")
    return render_template("sign_up.html")


@app.route('/login')
def login():
    if request.args.get("username") is not None:
        flash("Login Successful", "success")
        return redirect(location="/")
    return render_template("log_in.html")


@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')


if __name__ == '__main__':
    app.secret_key = 'a secret key'  # TODO: change
    app.run(debug=True, host="0.0.0.0")
