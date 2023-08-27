import os
import json
import datetime
import csv

from twitchio.ext import commands, routines

import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

_DOC_BASE = "https://github.com/fusoyeahhh/beyond_chaos_bingo/blob/main/BINGO_RULES.md"

def closest_not_over(guesses, value):
    ordered = {k: value - v for k, v in guesses.items() if value - v >= 0}
    log.debug(str(guesses))
    log.debug(str((value, str(ordered))))
    if len(ordered) == 0:
        return set()
    closest = sorted(ordered.values())[0]
    return {k for k, v in ordered.items() if v == closest}

class PlayerSet:
    VALID_GUESS_TYPES = {"bingo", "miab", "deaths"}

    ALLOWED_BINGO_GUESSES = sorted({
        *[f"c{i}" for i in range(1, 6)],
        *[f"r{i}" for i in range(1, 6)],
        "ll", "ul"
    })
    @classmethod
    def validate_guess(cls, guess):
        return guess.strip().lower() in cls.ALLOWED_BINGO_GUESSES

    @classmethod
    def from_csv(cls, fname, ptsfile=None):
        new = cls()

        with open(fname) as csvfile:
            statereader = csv.reader(csvfile, delimiter=",")

            for name, *row in statereader:
                for gtype, value in zip(cls.VALID_GUESS_TYPES, row):
                    if gtype != "bingo":
                        new.guess(name, gtype, int(value) if value != "" else None)
                    else:
                        new.guess(name, gtype, value if value != "" else None)

        return new

    def __init__(self, overwrite=False):
        self._store = {}
        self._overwrite = overwrite

    @property
    def overwrite(self):
        return self._overwrite

    @overwrite.setter
    def overwrite(self, value):
        self._overwrite = bool(value)

    def to_csv(self, fname, game_state=None):
        with open(fname, "w", newline="") as csvfile:
            statewriter = csv.writer(csvfile, delimiter=",")
            if game_state is not None:
                statewriter.writerow(game_state)

            for name, pstore in self._store.items():
                row = (
                    name,
                    *[str(pstore.get(k, "")) for k in self.VALID_GUESS_TYPES]
                )
                statewriter.writerow(row)

    def get_winners(self, gtype, value):
        if gtype not in self.VALID_GUESS_TYPES:
            raise ValueError(f"Invalid guess type: {gtype}")

        if len(self._store) == 0:
            return set()

        if gtype == "bingo":
            winners = {
                name for name, pstore in self._store.items()
                if pstore.get(gtype, None) == value
            }
        else:
            winners = closest_not_over({
                k: pstore[gtype]
                for k, pstore in self._store.items()
                if gtype in pstore
            }, int(value))
        return winners

    def __getitem__(self, value):
        return self._store[value]

    def _register(self, name):
        if name not in self._store:
            self._store[name] = {}

    def guess(self, name, gtype, value):
        if gtype not in self.VALID_GUESS_TYPES:
            raise ValueError(f"Invalid guess type: {gtype}")

        self._register(name)

        pstore = self._store[name]
        if value is None:
            pstore.pop(value)
            return True

        if gtype not in pstore or self.overwrite:
            pstore[gtype] = value
            return True

        return False


class AuthorizedCommand(commands.Command):
    _AUTHORIZED = set()

    async def invoke(self, ctx, *, index=0):
        user = ctx.author.name
        if self._authenticate(user):
            return await super().invoke(ctx, index=index)

        await ctx.send(f"I'm sorry, @{user}, I can't do that...")
        return

    def _authenticate(self, user):
        """
        Checks if ctx.user is in the administrator list.

        :param user: Twitch chat user name
        :return: (bool) whether or not user is authorized to use admin commands
        """
        auth = user in self._AUTHORIZED
        log.debug(f"Checking auth status for {user}: {auth}")
        return auth


class BCBingoBot(commands.Bot):
    COMMANDS = {}

    _POINTS_FOR = {
        "bingo": 1,
        "miab": 1,
        "deaths": 1,
    }
    GUESS_WINDOW = 60 * 5

    def __init__(self, config, segment=1, restore_from=None):
        self._cfg = self.load_config(config)
        self._cfg["prefix"] = "!"
        log.info(f"Configuration:\n{self._cfg}")

        super().__init__(**self._cfg)
        self.reset()
        self._segment = segment

        self._points = self.load_points(self._points_file)

        if restore_from is not None:
           self.restore(restore_from)

    def load_config(self, config):
        with open(config, "r") as fin:
            opts = json.load(fin)

        # add additional admin names here
        # These users can execute admin commands
        admins = set(opts.pop("admins", []))
        AuthorizedCommand._AUTHORIZED |= admins
        admins = ', '.join(admins)
        log.info(f"Added {admins} to the authorized users list.")
        # Base URL for rules and references
        self._doc_base = opts.pop("doc_url", _DOC_BASE)

        self._POINTS_FOR.update(opts.pop("points_for", {}))

        self._tracking = opts.pop("tracking_file", None)
        self._points_file = opts.pop("points_file", None)
        return opts

    def load_points(self, fname):
        pts = {}
        if fname is None:
            return pts

        with open(fname) as csvfile:
            ptreader = csv.reader(csvfile, delimiter=",")
            for name, *row in ptreader:
                pts[name] = int(row[0])

        return pts

    def assign_points(self, winners, value):
        winners = self._pstate.get_winners(gtype, value)

        for winner in winners:
            ptval = self._points.get(user, 0) + self._POINTS_FOR[gtype]
            self._points[user] = ptval
            log.info(f"{winner} now has {ptval} points")

        return winners

    @property
    def miab(self):
        return self._miab

    @miab.setter
    def miab(self, value):
        self._miab = max(0, value)

    @property
    def deaths(self):
        return self._deaths

    @deaths.setter
    def deaths(self, value):
        self._deaths = max(0, value)

    def restore(self, restore_from):
        self._pstate = PlayerSet.from_csv(restore_from)
        gstate = self._pstate._pstore.pop("_", {})
        self.miab = int(gstate.get("miab", 0))
        self.deaths = int(gstate.get("deaths", 0))
        self._segment = int(gstate.get("bingo", 1))

    def serialize(self):
        if self._tracking is not None:
            log.debug(f"Serializing state to {self._tracking}")
            game_state = ("_", *map(str, (self._segment, self.miab, self.deaths)))
            self._pstate.to_csv(self._tracking, game_state=game_state)

        if self._points_file is not None:
            log.debug(f"Serializing points to {self._points_file}")

            with open(self._points_file, "w", newline="") as csvfile:
                statewriter = csv.writer(csvfile, delimiter=",")
                for name, pval in self._store.items():
                    statewriter.writerow((name, str(pval))):

    def reset(self):
        self._pstate = PlayerSet()
        self._toggle = False
        self._miab = 0
        self._deaths = 0

    #
    # Twitch integration
    #
    @routines.routine(seconds=10)
    async def core_loop(self):
        # core interaction

        if self._timer is not None:
            # FIXME: need to keep this in sync with the routine interval
            self._timer -= 10
            if self._timer < 0:
                self._timer = None
                log.info("Firing timer event.")
                self._toggle = False
                await ctx.send(f"Guesses for {self.segment} are now CLOSED.")
            elif self.timer // 5 in list(range(0, 5 * 60, 5))[1::2]:
                min_left = self.timer % 60
                await ctx.send(f"About {min_left} minutes left for segment {self.segment} guesses.")

        try:
            log.debug("Doin' a thing...")
            self.serialize()
        except Exception as e:
            log.error("Encountered error while monitoring game state.")
            log.error(str(e))

    async def event_ready(self):
        log.warning("HELLO HUMAN, I AM CHAOS INCARNATE "
                    "WITH A BINGO PROBLEM, LET'S DO THIS THING.")
        self.core_loop.start()

    async def event_message(self, msg):
        if msg.echo:
            return

        await self.handle_commands(msg)

    #
    # Generic commands
    #
    @commands.command(name='hi')
    async def hi(self, ctx):
        await ctx.send("/me Hi. I'm BC Bingo Bot. "
                       "Welcome to Beyond Chaos Bingo "
                       "where the points don't matter and "
                       "the game over square is probably in the center. "
                       "Have you tried !bcbingo lately?")
    COMMANDS["hi"] = hi

    #
    # User-based commands
    #
    @commands.command(name='bcb'):
    async def bcb(self, ctx):
        """
        !bcb -> bcb [guess|current], reviews your guesses or shows who would win given the current situation.
        """
        user = ctx.author.name
        try:
            _, subcmd, *_ = ctx.message.content.split(" ")
        except ValueError as e:
            await ctx.send(f"@{user}, I didn't understand your request. "
                           f"Must be one of `guess` or `current`")
            return

        if subcmd == "guess":
            try:
                guesses = " | ".join(f"{gt}: {v}" for gt, v in self._pstate[user].items())
                await ctx.send(f"@{user}, your guesses are: {guesses}")
            except KeyError:
                await ctx.send(f"@{user}, I don't have guesses recorded for you.")

        elif subcmd == "current":
            miab_winners = ", ".join("@" + w for w in self._pstate.get_winners("miab", self.miab))
            deaths_winners = ", ".join("@" + w for w in self._pstate.get_winners("deaths", self.miab))
            await ctx.send(f"Current MIAB leaders: {miab_winners}")
            await ctx.send(f"Current deaths leaders: {deaths_winners}")

        else:
            await ctx.send(f"@{user}, I didn't understand your request.")
    COMMANDS["bcb"] = bcb

    @commands.command(name='guessbingo', aliases=["bingoguess", "bingo"])
    async def guessbingo(self, ctx):
        """
        !guessbingo -> Guess which bingo will occur. Valid guesses are r{1-5}, c{1-5}, and du (lower corner left to upper corner right), dd (upper corner left to lower corner right).
        """
        user = ctx.author.name
        if not self._toggle:
            await ctx.send(f"@{user}, I'm not accepting guesses right now.")
            return

        if "drop" in ctx.message.content or "students" in ctx.message.content:
            await ctx.send(f"Hilarious as always, @{user}")
            return

        try:
            _, value, *_ = ctx.message.content.split(" ")
            if not self._pstate.validate_guess(value):
                raise ValueError("Invalid bingo specification.")
            result = self._pstate.guess(user, "bingo", value.strip().lower())
        except ValueError as e:
            log.error(str(e))
            valid = ", ".join(self._pstate.ALLOWED_BINGO_GUESSES)
            await ctx.send(f"@{user}, I didn't understand your guess. "
                           f"Must be one of {valid}")
            return

        if not result:
            await ctx.send(f"@{user}, you have already guessed this category.")
            return
        await ctx.send(f"@{user}, your guess is {value}")
    COMMANDS["guessbingo"] = guessbingo

    @commands.command(name='guessmiab', aliases=["miabguess", "miab"])
    async def guessmiab(self, ctx):
        """
        !guessmiab -> Guess how many MiaB (Monster in a Box) will occur this segment.
        """
        user = ctx.author.name
        if not self._toggle:
            await ctx.send(f"@{user}, I'm not accepting guesses right now.")
            return

        try:
            _, value, *_ = ctx.message.content.split(" ")
            value = int(value.strip().lower())
            result = self._pstate.guess(user, "miab", value)
        except ValueError as e:
            log.error(str(e))
            await ctx.send(f"@{user}, I didn't understand your guess. "
                            "Please check and retry.")

        if not result:
            await ctx.send(f"@{user}, you have already guessed this category.")
            return
        await ctx.send(f"@{user}, your guess is {value}")
    COMMANDS["guessmiab"] = guessmiab

    @commands.command(name='guessdeaths', aliases=["deathsguess", "deaths"])
    async def guessdeaths(self, ctx):
        """
        !guessdeaths -> Guess how many times the player will get a Game Over this segment."
        """
        user = ctx.author.name
        if not self._toggle:
            await ctx.send(f"@{user}, I'm not accepting guesses right now.")
            return

        try:
            _, value, *_ = ctx.message.content.split(" ")
            value = int(value.strip().lower())
            result = self._pstate.guess(user, "deaths", value)
        except ValueError as e:
            log.error(str(e))
            await ctx.send(f"@{user}, I didn't understand your guess. "
                            "Please check and retry.")

        if not result:
            await ctx.send(f"@{user}, you have already guessed this category.")
            return
        await ctx.send(f"@{user}, your guess is {value}")
    COMMANDS["guessdeaths"] = guessdeaths

    #
    # Informational commands
    #
    @commands.command(name='bcbingo')
    async def explain(self, ctx):
        """
        Explain what do.
        """
        user = ctx.author.name
        await ctx.send(f"@{user}: Register guesses with "
                       f"!guessbingo !guessmiab and !guessdeaths. "
                       f"You can also do !help (command)")
    COMMANDS["bcbingo"] = explain

    #
    # Admin commands
    #
    @commands.command(name='bingoline', cls=AuthorizedCommand)
    async def bingoline(self, ctx):
        """
        !bingoline --> bingo winner
        """
        user = ctx.author.name
        try:
            _, value, *_ = ctx.message.content.split(" ")
            if not self._pstate.validate_guess(value):
                raise ValueError(f"Invalid bingo specification {value}.")
        except ValueError as e:
            log.error(str(e))
            return

        winners = self._pstate.get_winners("bingo", value)
        self.assign_points(winner, "bingo")

        winners = ", ".join("@" + w for w in self._pstate.get_winners("bingo", value))
        await ctx.send(f"C H A O S ACHIEVED. Winners for {value}: {winners}")
    
    @commands.command(name='miabcount', cls=AuthorizedCommand)
    async def miabcount(self, ctx):
        """
        !miabcount --> [number|++]
        """
        user = ctx.author.name
        value = ctx.message.content.split(" ")
        if len(value) > 1:
            value = value[1]
            if value == "++":
                self.miab += 1
            else:
                try:
                    self.miab = int(value)
                except ValueError as e:
                    log.error("Didn't understand request.")
                    log.error(str(e))
                    return

        await ctx.send(f"@{user}: MiaB count is currently {self.miab}.")

    @commands.command(name='deathcount', cls=AuthorizedCommand)
    async def deathcount(self, ctx):
        """
        !deathcount --> [number|++]
        """
        user = ctx.author.name
        value = ctx.message.content.split(" ")
        if len(value) > 1:
            value = value[1]
            if value == "++":
                self.deaths += 1
            else:
                try:
                    self.deaths = int(value)
                except ValueError as e:
                    log.error("Didn't understand request.")
                    log.error(str(e))
                    return

        await ctx.send(f"@{user}: Death count is currently {self.deaths}.")

    #
    # State handling
    #
    @commands.command(name='togglechaos', aliases=["t"], cls=AuthorizedCommand)
    async def togglechaos(self, ctx):
        """
        !togglechaos --> [on|off]
        """
        user = ctx.author.name
        value = ctx.message.content.split(" ")
        if len(value) > 1:
            _, value, *_ = value
            state = value.upper()
            if state not in {"ON", "OFF"}:
                log.error("Guess toggle must be one of on or off")
                return
            self._toggle = True if state == "ON" else False
        else:
            state = "ON" if self._toggle else "OFF"

        await ctx.send(f"@{user}: Guesses are currently {state}.")

    @commands.command(name='startsegment', aliases=["ss"], cls=AuthorizedCommand)
    async def startsegment(self, ctx):
        """
        !startsegment -> assign points for segment and reset to segment provided (next by default)
        """
        self._timer = self.GUESS_WINDOW
        min_remain = self._timer // 60
        await ctx.send(f"Guesses for segent {self.segment} close in {min_remain} minutes.")

    @commands.command(name='opensegment', aliases=["os"], cls=AuthorizedCommand)
    async def opensegment(self, ctx):
        """
        !opensegment -> Opens the current segment for guesses.
        """
        self._toggle = True
        await ctx.send(f"Guesses for {self.segment} are now OPEN.")

    @commands.command(name='segment', aliases=["s"], cls=AuthorizedCommand)
    async def segment(self, ctx):
        """
        !segment -> assign points for segment and reset to segment provided (next by default)
        """
        winners = self.assign_points(winner, "miab", self.miab)
        winners = ", ".join("@" + w for w in winners)
        await ctx.send(f"MiaB guess winners for {self._segment}: {winners}")

        winners = self.assign_points(winner, "deaths", self.deaths)
        winners = ", ".join("@" + w for w in winners)
        await ctx.send(f"Death guess winners for {self._segment}: {winners}")

        self.serialize()

        _, *value = ctx.message.content.split(" ")
        if len(value) > 0:
            try:
                self._segment = int(value[0])
            except ValueError as e:
                log.error(e)
                return
        else:
            self._segment += 1

        self.reset()

    @commands.command(name='saveandquit', aliases=["sq"], cls=AuthorizedCommand)
    async def saveandquit(self, ctx):
        """
        !saveandquit -> save data and shut down
        """
        self.serialize()
        self.close()

    #
    # Help commands
    #
    @commands.command(name='help')
    async def _help(self, ctx):
        """
        This command.
        """
        user = ctx.author.name
        cnt = ctx.message.content.lower().split(" ")
        cnt.pop(0)
        if not cnt:
            await ctx.send(f"Available commands: {' '.join(self.COMMANDS.keys())}. "
                           f"Use '!help cmd' (no excl. point on cmd) to get more help.")
            return

        arg = cnt.pop(0)
        if arg not in self.COMMANDS:
            await ctx.send(f"@{user}, that's not a command I have help for. "
                           f"Available commands: {' '.join(self.COMMANDS.keys())}.")
            return

        doc = self.COMMANDS[arg]._callback.__doc__
        await ctx.send(f"help | {arg}: {doc}")
    COMMANDS["help"] = _help

if __name__ == "__main__":
    import argparse
    import pathlib
    argp = argparse.ArgumentParser()
    argp.add_argument("-c", "--config-file",
                      help="Path to configuration file in JSON format. Required.")
    argp.add_argument("-r", "--restore-from",
                      help="Restore game state from this CSV file. Optional.")
    args = argp.parse_args()

    cfg = pathlib.Path(args.config_file or "config.json")
    if not cfg.exists():
        log.error("Configuration file does not exist or was mistyped.")
    else:
        BCBingoBot(cfg, restore_from=args.restore_from).run()
