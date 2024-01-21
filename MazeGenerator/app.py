from flask import Flask, send_file, request
from PIL import Image
from . import generator
from io import BytesIO

app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!<img src="/test50.png">'


@app.route('/test<n>.png')
def test(n: str):
    n_rows = int(n)

    mask = Image.open("MazeGenerator/maze_masks/dino_mask.png").convert("RGB")
    n_cols = (n_rows*mask.width)//mask.height
    seed = request.args.get("seed")
    maze = generator.MazeTemplate(mask, n_rows, n_cols).generate(seed)

    img_io = BytesIO()
    maze.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype="image/png")


if __name__ == '__main__':
    app.run()
