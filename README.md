# BC Bingo

## Setup

Using either a Linux-style terminal or Windows Powershell, ensure the following commands work:

```bash
python -V
pip --help
```

If one doesn't work, try the same but with `3` appended,  e.g., `python3`. If they still don't work, you will need to install python on your OS. Once this works, you need to install the pre-requisites.  From the directory which contains this README, and from that same command line:

```bash
pip install -r requirements.txt
```

## Starting the Server

Now you can start up the bingo server. For a Linux style terminal:

```bash
FLASK_APP=bc_bingo python -m flask run
```

For Windows Powershell:

```
$env:FLASK_APP = 'bc_bingo'; python -m flask run
```

This should start the server on the localhost, e.g., at the URL `127.0.0.1`, on the port `5000`. Don't worry if that doesn't sound understandable, the next section covers where to go next.

## Starting the Game

Open up your web browser and put `127.0.0.1:5000` in the navigation bar. This should bring up the segment selection list for BC bingo. Select the segment you want to start with from the links available.

Once you're done, you can hit `ctrl+C` at the terminal you were using to stop the server.

## Starting the Bot

**NOTE**: The bot and server are separate processes, so you will need two terminals, one for each. One cannot start the other.

Ensure your configuration file (often `config.json`) is properly formatted and contains all the required credentials. Then...

```bash
python -m bot --config-file <path to configuration>
```

Note that the Flask configuration from the server is not needed here. You can restore from a previous state with:

## Restoring the Game State

```bash
python -m bot --config-file <path to configuration> --restore-from <path to state csv file>
```

By default, the bot will save the current state every 10 seconds in a file called `current_bingo_state.csv`, which you can provide to the previous command to restore.
