# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/helpers.ipynb.

# %% ../nbs/helpers.ipynb 7
from __future__ import annotations

import base64
import json
import platform
import re
import sys
import uuid
from collections import defaultdict
from importlib import resources
from io import BytesIO
from pathlib import Path
from typing import Any
from typing import Iterable
from typing import Mapping
from typing import Sequence

import pcleaner.data
import pcleaner.structures as st
from IPython.display import clear_output
from IPython.display import display
from IPython.display import HTML
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont


# %% auto 0
__all__ = ['IN_MAC', 'IN_LINUX', 'IN_WIN', 'PRINT_FORMATS', 'is_mac', 'is_linux', 'is_win', 'default_device', 'cleanupwidgets',
           'RenderJSON', 'page_boxes', 'crop_box', 'size', 'dpi', 'get_image_html', 'get_columns_html',
           'display_columns', 'get_image_grid_html', 'display_image_grid', 'acc_as_html', 'strip_uuid',
           'defaultdict_to_dict', '_pops_', '_pops_values_', '_gets_']

# %% ../nbs/helpers.ipynb 12
def is_mac(): return platform.system() == 'Darwin'
def is_linux(): return platform.system() == 'Linux'
def is_win(): return platform.system() == 'Windows'


IN_MAC, IN_LINUX, IN_WIN = False, False, False

if is_win():
    IN_WIN = True   
elif is_mac():
    IN_MAC = True
elif is_linux():
    IN_LINUX = True


# %% ../nbs/helpers.ipynb 14
def default_device():
    import torch
    return "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"


# %% ../nbs/helpers.ipynb 16
_all_ = ['_pops_', '_pops_values_', '_gets_']


# %% ../nbs/helpers.ipynb 17
def _pops_(d: dict, ks: Iterable) -> dict: 
    "Pops `ks` keys from `d` and returns them in a dict. Note: `d` is changed in-place."
    return {k:d.pop(k) for k in ks if k in d}


# %% ../nbs/helpers.ipynb 19
def _pops_values_(d: dict, ks: Iterable) -> tuple:
    "Pops `ks` keys from `d` and returns them as a tuple. Note: `d` is changed in-place."
    return tuple(d.pop(k, None) for k in ks)


# %% ../nbs/helpers.ipynb 21
def _gets_(d: Mapping[str, Any], ks: Iterable):
    "Fetches values from a mapping for a given list of keys, returning `None` for missing keys."
    return (d.get(k, None) for k in ks)


# %% ../nbs/helpers.ipynb 24
def _get_globals(mod: str):
    if hasattr(sys, '_getframe'):
        glb = sys._getframe(2).f_globals
    else:
        glb = sys.modules[mod].__dict__
    return glb


# %% ../nbs/helpers.ipynb 26
def cleanupwidgets(*ws, mod: str|None=None, clear=True):
    glb = _get_globals(mod or __name__)
    if clear: clear_output(wait=True)
    for w in ws:
        _w = glb.get(w) if isinstance(w, str) else w
        if _w:
            try: _w.close()  # type: ignore
            except: pass


# %% ../nbs/helpers.ipynb 29
class RenderJSON(object):
    def __init__(self, json_data, max_height=200, init_level=0):
        if isinstance(json_data, (Sequence, Mapping)):
            s = json.dumps(json_data)
        elif hasattr(json_data, 'to_dict'):
            s = json.dumps(json_data.to_dict())
        elif hasattr(json_data, 'to_json'):
            s = json_data.to_json()
        else:
            s = json_data
        self.json_str = s
        self.uuid = str(uuid.uuid4())
        self.max_height = max_height
        self.init_level = init_level


    def display(self):
        html_content = f"""
        <div id="wrapper-{self.uuid}" style="width: 100%; max-height: {self.max_height}px; overflow-y: auto;">
            <div id="{self.uuid}" style="width: 100%;"></div>
            <script>
                function renderMyJson() {{
                    renderjson.set_show_to_level({self.init_level});
                    document.getElementById('{self.uuid}').appendChild(renderjson({self.json_str}));
                }}
                function loadScript(url, callback) {{
                    var script = document.createElement("script");
                    script.type = "text/javascript";
                    script.onload = function() {{
                        callback();
                    }};
                    script.src = url;
                    document.getElementsByTagName("head")[0].appendChild(script);
                }}
                loadScript("https://cdn.jsdelivr.net/npm/renderjson@latest/renderjson.js", renderMyJson);
            </script>
        </div>
        """
        display(HTML(html_content))

    def _ipython_display_(self):
        self.display()

# %% ../nbs/helpers.ipynb 32
def page_boxes(self: st.PageData, 
        image_path: Path, out_dir: Path | None = None) -> tuple[Image.Image, Path]:
    """
    Visualize the boxes on an image.
    Typically, this would be used to check where on the original image the
    boxes are located.

    :param image_path: The path to the image to visualize the boxes on.
    """
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)
    data_path = resources.files(pcleaner.data)
    font_path = str(data_path / "LiberationSans-Regular.ttf")
    # Figure out the optimal font size based on the image size. E.g. 30 for a 1600px image.
    font_size = int(image.size[0] / 50) + 5

    for index, box in enumerate(self.boxes):
        draw.rectangle(box.as_tuple, outline="green")
        # Draw the box number, with a white background, respecting font size.
        draw.text(
            (box.x1 + 4, box.y1),
            str(index + 1),
            fill="green",
            font=ImageFont.truetype(font_path, font_size),
            stroke_fill="white",
            stroke_width=3,
        )

    for box in self.extended_boxes:
        draw.rectangle(box.as_tuple, outline="red")
    for box in self.merged_extended_boxes:
        draw.rectangle(box.as_tuple, outline="purple")
    for box in self.reference_boxes:
        draw.rectangle(box.as_tuple, outline="blue")

    # Save the image.
    extension = "_boxes"
    out_path = image_path.with_stem(image_path.stem + extension)
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / out_path.name
    image.save(out_path)

    return image, out_path

# %% ../nbs/helpers.ipynb 34
def crop_box(box: st.Box, image: Image.Image) -> Image.Image:
    return image.crop(box.as_tuple)

# %% ../nbs/helpers.ipynb 36
PRINT_FORMATS = {
    'Golden Age': (7.75, 10.5),  # (1930s-40s) 
    'Siver Age': (7, 10.375),  # (1950s-60s)
    'Modern Age': (6.625,10.25),  # North American comic books
    'Magazine': (8.5, 11), 
    'Digest': (5.5, 8.5), 
    'Manga': (5.0, 7.5),
}


def size(w: int, h: int, unit: str = 'in', dpi: float = 300.) -> tuple:
    """
    Calculate the print size of an image in inches or centimeters.

    Args:
    w (int): Width of the image in pixels.
    h (int): Height of the image in pixels.
    unit (str): Unit of measurement ('in' for inches, 'cm' for centimeters).
    dpi (float): Dots per inch (resolution).

    Returns:
    tuple: Width and height of the image in the specified unit.
    """
    if unit == 'cm':
        return (w / dpi * 2.54, h / dpi * 2.54)
    else:  # default to inches
        return (w / dpi, h / dpi)


def dpi(w: int, h: int, print_format: str = 'Modern Age') -> float:
    """
    Calculate the dpi (dots per inch) needed to print an image at a specified format size.

    Args:
    w (int): Width of the image in pixels.
    h (int): Height of the image in pixels.
    print_format (str): Print format as defined in the formats dictionary.

    Returns:
    float: Required dpi to achieve the desired print format size.
    """
    # Default to 'Modern Age' if format not found
    format_size = PRINT_FORMATS.get(print_format, PRINT_FORMATS['Modern Age'])
    width_inch, height_inch = format_size
    dpi_w = w / width_inch
    dpi_h = h / height_inch
    return (dpi_w + dpi_h) / 2  # Average dpi for width and height


# %% ../nbs/helpers.ipynb 38
def get_image_html(image: Image.Image | Path | str, max_width: int | None = None):
    """
    Converts a PIL image or an image file path to an HTML image tag. If the image is a PIL Image object,
    it is converted to a base64-encoded PNG and embedded directly into the HTML. If the image is a file path,
    the path is used as the source URL for the image tag.
    """
    style = f' style="max-width: {max_width}px;"' if max_width is not None else ''
    if isinstance(image, (Path, str)):
        return f'<img src="{str(image)}"{style}/>'
    else:
        buffered = BytesIO()
        image.save(buffered, format='PNG')
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f'<img src="data:image/png;base64,{img_str}"{style}/>'


def get_columns_html(
    columns: list[list], max_image_width: int | None = None, headers: list[str] | None = None
):
    if not all(len(col) == len(columns[0]) for col in columns):
        raise ValueError("All columns must have the same length.")

    # Calculate the maximum width of images in each column
    max_widths = []
    for col_index in range(len(columns)):
        max_col_width = 0
        for item in columns[col_index]:
            if isinstance(item, (Image.Image, Path)):
                if isinstance(item, (Path, str)):
                    try:
                        item = Image.open(item)
                    except:
                        continue
                width, _ = item.size
                max_col_width = max(max_col_width, width)
        if max_col_width > 0:
            max_widths.append(
                f"{min(max_col_width, max_image_width)}px"
                    if max_image_width is not None else 
                f"{max_col_width}px"
            )
        else:
            max_widths.append('auto')

    html_str = "<table>"

    # Apply calculated column widths using <colgroup> and <col> elements
    html_str += "<colgroup>"
    for width in max_widths:
        html_str += f"<col style='width: {width};'/>"
    html_str += "</colgroup>"

    if headers:
        if len(headers) != len(columns):
            raise ValueError("Headers list must match the number of columns.")
        html_str += (
            "<tr>"
            + "".join(
                f"<th style='text-align: center; font-weight: bold;'>{header}</th>"
                for header in headers
            )
            + "</tr>"
        )

    for row_items in zip(*columns):
        html_str += "<tr>"
        for i, item in enumerate(row_items):
            if isinstance(item, (Image.Image, Path)):
                img_html = get_image_html(item, max_width=max_image_width)
                html_str += f"<td style='text-align: center;'>{img_html}</td>"
            else:  # Assume the item is a string
                style = "font-weight: bold;" if i == 0 else ""
                html_str += f"<td style='font-size: 12pt; text-align: left; {style}'>{item}</td>"
        html_str += "</tr>"

    html_str += "</table>"
    return html_str


def display_columns(
    columns: list[list], max_image_width: int | None = None, headers: list[str] | None = None
):
    """
    Displays a table with any combination of columns, which can be lists of strings or lists 
    of PIL Image objects, within a Jupyter notebook cell.

    :param columns: A list of lists, where each sublist represents a column in the table. 
                    Each sublist can contain either strings or PIL Image objects.
    :param max_image_width: The maximum size of the images in pixels. This controls the max-height 
                            of the images.
    :param headers: A list of header labels for the table. If None, no headers are displayed.
    """
    return display(HTML(get_columns_html(columns, max_image_width, headers)))


def get_image_grid_html(
    images: list[Image.Image | Path | str],
    rows: int,
    columns: int,
    titles: list[str] | None = None,
    max_image_width: int | None = None,
    caption: str | None = None
):
    if titles and len(titles) != len(images):
        raise ValueError("Titles list must match the number of images if provided.")

    html_str = "<table>"

    if caption:
        html_str += (f"<caption style='caption-side: top; text-align: center; "
                    f"font-weight: bold;'>{caption}</caption>")

    image_index = 0
    for _ in range(rows):
        html_str += "<tr>"
        for _ in range(columns):
            if image_index < len(images):
                img_html = get_image_html(images[image_index], max_width=max_image_width)
                title_html = (
                    f"<div style='text-align: center;'>{titles[image_index]}</div>"
                    if titles
                    else ""
                )
                html_str += f"<td style='text-align: center;'>{title_html}{img_html}</td>"
            else:
                html_str += "<td></td>"  # Empty cell if no more images
            image_index += 1
        html_str += "</tr>"

    html_str += "</table>"
    return html_str


def display_image_grid(
    images: list[Image.Image | Path | str],
    rows: int,
    columns: int,
    titles: list[str] | None = None,
    max_image_width: int | None = None,
    caption: str | None = None,
):
    """
    Displays a grid of images in a HTML table within a Jupyter notebook cell.

    :param images: A list of PIL Image objects to be displayed.
    :param rows: The number of rows in the grid.
    :param columns: The number of columns in the grid.
    :param titles: An optional list of titles for each image. If provided, it must match the length 
                    of the images list.
    :param max_image_width: The maximum width of the images in pixels.
    """
    display(HTML(get_image_grid_html(images, rows, columns, titles, max_image_width, caption)))


def acc_as_html(acc):
    return f"<div style='font-size: 12pt;'><strong style='color: red;'>{acc:.2f}</strong><div/>"


# %% ../nbs/helpers.ipynb 40
def strip_uuid(p: Path | str):
    _p: Path = p if isinstance(p, Path) else Path(p)
    new_stem = re.sub(r'(?i)[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12}', '', _p.stem).strip('_')
    return _p.with_stem(new_stem)


# %% ../nbs/helpers.ipynb 43
# Deep copy a defaultdict of defaultdicts to a dict of dicts if it is not already a dict
def defaultdict_to_dict(d) -> dict:
    if not isinstance(d, defaultdict):
        return d
    return {k: defaultdict_to_dict(v) for k, v in d.items()}
