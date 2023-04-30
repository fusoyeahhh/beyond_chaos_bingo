#!/usr/bin/env python
import glob
import random
import csv
import itertools
import pprint
from enum import IntFlag, auto

class SqState(IntFlag):
    INACTIVE = auto()
    BLOCKED = auto()
    ACTIVE = auto()

class BingoBoard:
    class BingoSquare:
        def __init__(self, text, state=SqState.INACTIVE):
            self.text = text
            self.state = state

        def __str__(self):
            return f"({self.text}: {str(self.state)})"

        def __repr__(self):
            return f"({self.text}: {str(self.state)})"

    def __init__(self, option_pool, ncols=5, nrows=5):
        self.size = (ncols, nrows)
        self.reset(*self.size)

        #self.pool = [f"Bingo Opt {i:03d}" for i in range(1000)]
        #self.pool = self._init_pool("segments/segment_1.csv")
        self.pool = self._init_pool(option_pool)

        self.generate()

    def _init_pool(self, fname):
        with open(fname, "r") as csvfile:
            return [*csv.DictReader(csvfile)]

    def sample_pool(self, segment_index):
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
            chosen += random.choices(list(grping), k=c)

        return [ch["square"] for ch in chosen]

    def generate(self):
        selection = self.sample_pool(1)
        random.shuffle(selection)

        for col in self._board:
            for i, val in enumerate(col):
                if val is not None:
                    continue
                col[i] = self.BingoSquare(selection.pop())

    def reset(self, ncols, nrows):
        self._board = [[None] * nrows for _ in range(ncols)]

    def render_grid(self):
        from htmlBuilder import tags, attributes
        return tags.Div([attributes.Class("bingo_grid")],
            [tags.Div([attributes.Class("bingo_col")], 
                [tags.Div([attributes.Class("bingo_sq inactive"),
                           attributes.Onclick("toggleState(this);")],
                           sq.text) for sq in col]
                ) for col in self._board]
        )

    def generate_counter(self, name, func):
        from htmlBuilder import tags, attributes
        _name = name.replace("_", " ")

        return tags.Div([attributes.Class(f"counter {name}")], [
            tags.Button([attributes.Onclick(f"{func}(true);")], f"inc {_name}"),
            tags.Button([attributes.Onclick(f"{func}(false);")], f"dec {_name}"),
            tags.Div([attributes.Onclick(func)], _name),
            tags.Div([attributes.Id(f"{name}_counter")], "0")
        ])
        return

    def render(self):
        from htmlBuilder import tags

        with open("bingo.css", "r") as css:
            css_style = css.read()

        with open("toggle.js", "r") as jsf:
            js = jsf.read()

        head = [
            tags.Title([], "BC Bingo"),
            tags.Style([], css_style),
            tags.Script([], js),
        ]

        body = [
            self.generate_counter("miab", "incCounterMIAB"),
            self.generate_counter("death", "incCounterDeaths"),
            self.render_grid(),
        ]

        return tags.Html([],
                tags.Head([], head),
                tags.Body([], body),
            ).render(pretty=True)

import flask
from flask import Flask
app = Flask(__name__)

@app.route("/")
def render_index():
    from htmlBuilder import tags, attributes
    segments = {int(f.replace(".csv", "").split("_")[-1]): f
                    for f in glob.glob("segments/segment_*.csv")}

    head = [
        tags.Title([], "BC Bingo | Segment Selection"),
    ]

    body = [
        tags.Ul([],
            [tags.Li([], tags.A([attributes.Href(f"segment/{seg}")],
                                f"Segment {seg}"))
                for seg in sorted(segments)]
        )
    ]

    index = tags.Html([],
            tags.Head([], head),
            tags.Body([], body),
        ).render(pretty=True)

    return flask.render_template_string(index)

@app.route("/segment/<seg>")
def render_board(seg):
    board = BingoBoard(f"segments/segment_{seg}.csv")

    return flask.render_template_string(board.render())
