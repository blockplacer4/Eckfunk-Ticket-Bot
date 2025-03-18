"""
Discord Ticket Bot

Written in Python by Janosch | blockyy and Luxx
© 2024 Soluslab. All rights reserved.
"""

import ezcord
import discord
import configparser

bot = ezcord.Bot(intents=discord.Intents.all())

# Lade alle Cogs (Erweiterungen)
bot.load_extension("cogs")

config = configparser.ConfigParser()
config.read("config.ini")
bot.run(config["KEYS"]["discord_bot_token"])
