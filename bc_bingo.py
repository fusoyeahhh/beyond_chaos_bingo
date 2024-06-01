#!/usr/bin/env python
import re
import glob
import random
import csv
import time
import itertools
import pprint
from enum import IntFlag, auto


from htmlBuilder import tags, attributes
class PreRenderedHtml(tags.HtmlTag):
    def __init__(self, html):
        super().__init__()
        self._html = html

    def _render(self, pretty=False, nesting_level=None):
        return self._html

class BingoBoard:
    class BingoSquare:
        @classmethod
        def render_text(cls, text):
            from htmlBuilder import tags, attributes
            text = re.split(f"__", text)
            n = len(text)
            for i, t in enumerate(text[:]):
                text.append(t if i % 2 == 0 else tags.B([], t))
                text.pop(0)

            return text

        @property
        def text(self):
            return self.render_text(self._text)

        def __init__(self, text):
            self._text = text

        def __str__(self):
            return f"({self.text}"

        def __repr__(self):
            return f"({self.text}"

    def __init__(self, option_pool, seed=0, segment=None, ncols=5, nrows=5):
        self.size = (ncols, nrows)
        self._seg = int(segment)
        self.reset(*self.size)

        self._seed = seed
        self.pool = self._init_pool(option_pool)

    def _init_pool(self, fname):
        with open(fname, "r") as csvfile:
            return [*csv.DictReader(csvfile)]

    def sample_pool(self, segment_index, seed=None):
        random.seed(seed or self._seed)
        # get groupings and choices
        def pattr(elem):
            return (elem["type"], int(elem["choices"] or "1"))

        # Filter on seg index
        pool = sorted([elem for elem in self.pool
                if int(elem["segment_index"]) == segment_index],
                key=pattr)

        # group to number of choices and generate from pool
        chosen = []
        for (t, c), grping in itertools.groupby(pool, pattr):
            grping = list(grping)
            assert len(grping) >= c, \
                    f"Group {t} has insufficient length to sample {c} items"
            chosen += random.sample(grping, k=c)

        return [ch["square"] for ch in chosen]

    def generate(self, segment=None):
        selection = self.sample_pool(segment or self._seg)
        random.shuffle(selection)

        for col in self._board:
            for i, val in enumerate(col):
                if val is not None:
                    continue
                col[i] = self.BingoSquare(selection.pop())

    def reset(self, ncols, nrows):
        self._board = [[None] * nrows for _ in range(ncols)]

    @classmethod
    def generate_rules(cls):
        from htmlBuilder import tags, attributes
        import markdown
        with open("BINGO_RULES.md") as rulefile:
            rules = rulefile.read()

        return PreRenderedHtml(markdown.markdown(rules))

    def render_grid(self):
        from htmlBuilder import tags, attributes
        return tags.Div([attributes.Class("bingo_grid")],
            [tags.Div([attributes.Class("bingo_col")], 
                [tags.Div([attributes.Class("bingo_header")], c)] +
                [tags.Div([attributes.Class("bingo_sq inactive"),
                           attributes.Onclick("toggleState(this);")],
                           sq.text) for sq in col]
                ) for c, col in zip("CHAOS", self._board)]
        )

    def generate_counter(self, name, func, img_src):
        from htmlBuilder import tags, attributes
        _name = name.replace("_", " ")

        return tags.Div([attributes.Class(f"counter {name}")], [
            tags.Button([attributes.Onclick(f"{func}(true);")], f"inc {_name}"),
            tags.Button([attributes.Onclick(f"{func}(false);")], f"dec {_name}"),
            tags.Img([attributes.Src(img_src)]),
            tags.Div([attributes.Onclick(func)], _name),
            tags.Div([attributes.Id(f"{name}_counter")], "0")
        ])
        return

    def create_header(self):
        from htmlBuilder import tags, attributes

        board_header = [f"Segment {self._seg}"]
        prev_seg, next_seg = self._seg - 1, self._seg + 1

        text = f"Segment {prev_seg}"
        if self._seg > 1:
            elems = [
                tags.A([attributes.Href(f"../{self._seed}/{prev_seg}")], text),
                tags.Div([], " &larr; ")
            ]
        else:
            elems = [
                tags.Div([attributes.Class("header_hidden")], text),
                tags.Div([attributes.Class("header_hidden")], " &larr; ")
            ]
        board_header = elems + board_header

        text = f"Segment {next_seg}"
        if self._seg < 7:
            elems = [
                tags.Div([], " &rarr; "),
                tags.A([attributes.Href(f"../{self._seed}/{next_seg}")], text)
            ]
        else:
            elems = [
                tags.Div([attributes.Class("header_hidden")], " &rarr "),
                tags.Div([attributes.Class("header_hidden")], text)
            ]
        board_header += elems

        return board_header

    def render(self):
        from htmlBuilder import tags, attributes

        with open("bingo.css", "r") as css:
            css_style = css.read()

        with open("toggle.js", "r") as jsf:
            js = jsf.read()

        head = [
            tags.Title([], "BC Bingo"),
            tags.Style([], css_style),
            tags.Script([], js),
        ]


        header = tags.Div([attributes.Class("header")], [
            self.generate_counter("miab", "incCounterMIAB", "/static/miab.png"),
            tags.Div(
                [attributes.Class("segment")],
                tags.Div(
                    [attributes.Class("header_inner")],
                    self.create_header()
                )
            ),
            self.generate_counter("death", "incCounterDeaths", "/static/squish.png"),
        ])

        body = [
            header,
            self.render_grid(),
        ]

        return tags.Html([],
                tags.Head([], head),
                tags.Body([], body),
            ).render(pretty=True)

import flask
from flask import Flask
app = Flask(__name__)

@app.route("/", defaults={"seed": None})
@app.route("/<seed>")
def render_index(seed):
    if seed is not None:
        seed = int.from_bytes(str(seed).encode("utf8"), byteorder="big")
    else:
        seed = int(time.time())

    from htmlBuilder import tags, attributes
    segments = {int(f.replace(".csv", "").split("_")[-1]): f
                    for f in glob.glob("segments/segment_*.csv")}

    head = [
        tags.Title([], "BC Bingo | Segment Selection"),
    ]

    body = [
        tags.Div([], [f"Seed: {seed}"]),
        tags.Ul([],
            [tags.Li([], tags.A([attributes.Href(f"segment/{seed}/{seg}")],
                                f"Segment {seg}"))
                for seg in sorted(segments)]
        )
    ]

    #try:
    body += [BingoBoard.generate_rules()]

    index = tags.Html([],
            tags.Head([], head),
            tags.Body([], body),
        ).render(pretty=True)

    return flask.render_template_string(index)

@app.route("/segment/", defaults={"seed": None, "seg": "1"})
@app.route("/segment/<seed>", defaults={"seed": None})
@app.route("/segment/<seed>/<seg>")
def render_board(seg, seed):
    print(seed)
    board = BingoBoard(f"segments/segment_{seg}.csv", seed=seed, segment=seg)
    board.generate(int(seg))

    return flask.render_template_string(board.render())
