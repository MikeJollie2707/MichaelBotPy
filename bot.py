import discord
from discord.ext import commands

import os
import sys
import traceback
import logging
import json

def setup(bot_name):
    TOKEN = None # A str
    bot_info = None # A dict
    db_info = None # A dict

    fin = open("./setup/config.json")
    initial_bot_state = json.load(fin)

    try:
        with open("./setup/config.json") as fin:
            bot_info = json.load(fin)[bot_name]
            
            with open(f"./setup/{bot_info['token']}") as fi:
                TOKEN = json.load(fi).get("token")
            with open(f"./setup/{bot_info['db']}") as fi:
                db_info = json.load(fi)
    except FileNotFoundError as fnfe:
        print(fnfe)
    except KeyError as ke:
        print(ke)
    
    return (TOKEN, bot_info, db_info)

def setupLogger(enable : bool = True):
    logger = logging.getLogger("discord")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(filename = "discord.log", encoding = "utf-8", mode = "w")
    handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
    logger.addHandler(handler)

if __name__ == "__main__":
    argc = len(sys.argv)

    bot_info = None
    if (argc == 2):
        # sys.argv is a list, with the script's name as the first one, and the argument as the second one.
        bot_info = setup(sys.argv[1])
    else:
        print("Too many arguments. The second argument should be the bot's index in 'config.json'.")

    TOKEN = bot_info[0]
    prefix = bot_info[1]
    description = bot_info[2]

    setupLogger(enable = True)

    if TOKEN is None or prefix is None:
        print("Unable to load token and prefix.")
    else:
        bot = commands.Bot(
            command_prefix = commands.when_mentioned_or(prefix), 
            description = description,
            status = discord.Status.online,
            activity = discord.Game(name = "Linux")
        )

        try:
            for filename in sorted(os.listdir('./categories')):
                if filename.endswith('.py'):
                    bot.load_extension(f'categories.{filename[:-3]}')
        except Exception:
            print(traceback.print_exc())
        else:
            bot.run(TOKEN)