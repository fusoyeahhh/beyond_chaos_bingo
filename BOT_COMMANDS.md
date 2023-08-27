# Commands for Bingo Bot

## User commands

All chat users can use these commands.

 * `hi` -- Greetings from SkyNet. Also serves as "is alive" commands.
 * `bcbingo` -- Get some basic information on how to play
 * `help` -- Provides basic help on commands
 * `bcb`
   * `bcb current` -- see who would win if the segment ended now
   * `bcb guess` -- list the requestor's current guesses, if any
 * `guessbingo` (also `bingoguess`, `bingo`) -- enter a guess for a bingo, should be one of `r{1-5}, c{1-5}, ll, ul`
 * `guessmiab` (also `miabguess`, `miab`) -- enter a guess for number of MiaBs in this segment
 * `guessdeaths` (also `deathsguess`, `deaths`) -- enter a guess for number of deaths in this segment

## Admin commands

These commands require the user to be in the authentication list in the config file.

 * `bingoline` -- indicate a winning bingo line and assign points
 * `miabcount` -- When given with a number, will set the MiaB count to that number, when given with `++` increments the count
 * `deathcount` -- When given with a number, will set the death count to that number, when given with `++` increments the count
 * `togglechaos` (also `t`) -- Options are `t ON` or `t OFF` to toggle guesses on and off manually. If neither is given, indicates the current toggle state.
 * `opensegment` -- Opens the segment for guesses, much like `togglechaos`
 * `startsegment` -- Starts a timer which counts down, and when complete closes the segment for guessing.
 * `segment` -- If no number is given, assigns points for the segment, clears the guesses, and increments the segment. If a number is given, then same thing but moves to indicated segment.
 * `saveandquit` (also `sq`) -- Forces a save of the current state and shuts down the bot
