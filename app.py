import math
from io import BytesIO

from hashlib import sha256
from PIL import Image
from flask import *
from flask_login import LoginManager, current_user, login_user, UserMixin, login_required, logout_user

import generator
import db
import validation

app = Flask(__name__)
database = db.Database("database.db")
login = LoginManager(app)


def hash_password(password: str) -> bytes:
    return sha256(password.encode('utf-8')).digest()


class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id
        self.info = database.get_user(user_id)


@login.user_loader
def get_user(user_id):
    return User(user_id)


@app.route('/maze_shapes')
def maze_list():
    return render_template("shape_list.html", username="", mazes=database.get_all_mazes())


@app.route("/")
def index():
    """TODO:add description here"""
    return render_template("index.html")


@app.route("/generate")
def generate_ui():
    """The 'generate' page, provides the user with a UI to generate mazes"""
    try:
        shape_id = validation.validate_integer(request.args.get("maze_shape"), 0)
        maze = database.get_maze_from_id(shape_id)
    except Exception as e:
        print(e)
        # TODO: Better error pages
        return abort(400)
    print(maze)
    return render_template("generate.html", maze=maze)


@app.route("/generated_maze.svg")
def generate_maze():
    """hosts the image file of a generated maze, so it is available for the browser"""
    shape_id = validation.validate_integer(request.args.get("maze_shape"), 0)
    maze = database.get_maze_from_id(shape_id)
    size = validation.validate_integer(request.args.get("maze_size"), 1)
    mask = maze.get_shape().convert("RGB")
    scale = int(math.sqrt((mask.width * mask.height) // size))
    n_rows = mask.height // scale
    n_cols = mask.width // scale  # approximate square cells
    maze_io = generator.MazeGenerator(mask, n_rows, n_cols).generate()

    #  using io object to serve png file, this way it doesn't need to be saved to disk
    maze_io.seek(0)
    return send_file(maze_io, mimetype="image/svg+xml")


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        """serve the html page to create an account"""
        return render_template("sign_up.html")

    elif request.method == 'POST':
        """create an account using POST parameters"""
        _next = request.args.get("next")
        try:
            username = request.form.get("username")
            validation.validate_username(username)

            password = request.form.get("password")
            firstname = request.form.get("firstname")
            lastname = request.form.get("lastname")

            hashed_password = sha256(password.encode('utf-8')).digest()
            user_info = db.UserInfo(-1, username, firstname, lastname)
            print(user_info)

            database.add_user(user_info, hashed_password)
            flash(f"Successfully created account for '{username}'", 'success')
        except validation.CharacterNotAllowedError:
            flash("Username can only contain letters, numbers, "
                  "full stops, hyphens and underscores", 'error')
            return redirect(url_for("signup", next=_next), 303)
        except db.UserAlreadyExistsError as e:
            flash(str(e), 'error')
            return redirect(url_for("signup", next=_next), 303)
        return redirect(url_for("login", next=_next), 303)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("log_in.html")

    elif request.method == 'POST':
        if current_user.is_authenticated:
            flash(f"Already logged in as '{current_user.info.username}'", 'info')
            return redirect(url_for('index'), 303)

        _next = None
        try:
            _next = validation.validate_next(request.form.get("next"))
        except validation.ExternalURLNotAllowedError as e:
            flash(f"denied attempt to redirect to '{e.args[1]}'", "info")

        try:
            print(_next)
            password = request.form.get('password')
            hashed_password = hash_password(password)

            username = request.form.get('username')
            user_id = database.authenticate_user(username, hashed_password)

            login_user(User(user_id))

        except Exception as e:
            flash(str(e), 'error')
            return redirect(url_for("login", next=_next), 302)
        else:
            flash(f"Successfully logged in as '{username}'", 'success')
            return redirect(_next or url_for("index"), 303)


@app.route('/settings', methods=["GET", "POST", "DELETE"])
@login_required
def settings():
    if request.method == "GET":
        return render_template("account_settings.html")

    elif request.method == "POST":
        if request.form.get("username"):
            try:
                validation.validate_username("username")
            except validation.CharacterNotAllowedError as e:
                flash(str(e), "error")
                return redirect(url_for("settings"))
        try:
            database.update_info(current_user.info.user_id,
                                 request.form.get("username"),
                                 request.form.get("firstname"),
                                 request.form.get("lastname"))
            return redirect(url_for("settings"))
        except db.UserAlreadyExistsError as e:
            flash(str(e), 'error')
            return redirect(url_for("settings"))


@app.route("/changepassword", methods=["POST"])
def update_password():
    current_password = request.form.get("current_password")
    new_password = request.form.get("new_password")
    try:
        database.authenticate_user(current_user.info.username, hash_password(current_password))
        database.update_password(current_user.info.user_id, hash_password(new_password))
        flash("Successfully updated password", "success")
    except db.AuthenticationError:
        flash("Incorrect password", "error")
    finally:
        return redirect(url_for('settings'))


@app.route("/deleteaccount", methods=["POST"])
def delete_account():
    password = request.form.get("password")
    if not password:
        flash("Please enter a password", "error")
        return redirect(url_for("settings"))
    try:
        database.authenticate_user(current_user.info.username, hash_password(password))
        database.delete_user(current_user.info.user_id)
        logout_user()
        flash("Account successfully deleted", "success")
        return redirect(url_for("index"))
    except db.AuthenticationError:
        flash("Incorrect password", "error")
        return redirect(url_for("settings"))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Successfully logged out', 'success')
    return redirect(url_for('login'), 303)


@app.errorhandler(404)
def page_not_found(_):
    return render_template("404_not_found.html")


@app.errorhandler(401)
def page_not_found(_):
    return render_template("401_unauthorised.html")


@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')


if __name__ == '__main__':
    app.secret_key = 'ZouzwDJ7wPt1ldyFaxM57l322f6Wc5X57GhnA0eMvD'
    # randomly generated alphanumeric characters

    app.run(debug=True, host="0.0.0.0")
