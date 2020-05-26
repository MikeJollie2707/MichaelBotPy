import json
import discord
import datetime
import textwrap
from math import *
import ast

def get_config(guild_id) -> dict:
    """
    Get the configuration for the guild.
    Note: This function is deprecated and will be removed in near future.
    """
    config = {"ERROR": 0, "GUILD_ID": guild_id}
    file_name = str(guild_id) + ".json"
    try:
        fin = open("./data/" + file_name, 'r')
    except FileNotFoundError:
        config["ERROR"] = -1
    else:
        config = json.load(fin)

    return config

def save_config(config) -> None:
    """
    Save the configuration for the guild.
    Note: This function is deprecated and will be removed in near future.
    """
    if isinstance(config, dict):
        fin = open("./data/" + str(config["GUILD_ID"]) + ".json", 'w')
        json.dump(config, fin, indent = 4)

def get_default_embed(timestamp : datetime.datetime, author : discord.User = None, title : str = "", url : str = "", description : str = "", color : discord.Color = discord.Color.green()) -> discord.Embed:
    """
    Generate a "default" embed with footer and the time.

    The embed can still be mutated.

    Note that for logging, you should overwrite the footer to something else. It is default to "Requested by "

    Parameter:
    - `timestamp`: the timestamp, usually `utcnow()`.
    - `author`: optional `discord.User` or `discord.Member` to set to the footer. If not provided, it won't set the footer.
    - `title`: optional title.
    - `url`: optional url for the title.
    - `description`: optional description. Internally it'll remove the tabs so no need to pass textwrap.dedent(description).
    - `color`: optional color, default to green.

    Return type: `discord.Embed` or `None` on failure.
    """
    try:
        embed = discord.Embed(
            title = title,
            url = url,
            description = textwrap.dedent(description),
            color = color,
            timestamp = timestamp
        )
        if (author is not None):
            embed.set_footer(
                text = f"Requested by {author.name}",
                icon_url = author.avatar_url
            )
    except AttributeError as ae:
        print(ae)
        embed = None

    return embed

def striplist(array : list) -> str:
    """
    Turn the list of objects into a string.

    Useful for logging list of permissions.

    Parameter: 
    - `array`: a list.

    Return type: `str`
    """

    st = str(array)

    st = st.replace('[', "")
    st = st.replace(']', "")
    st = st.replace("'", "")

    return st

def calculate(expression : str) -> str:
    """
    Calculate a simple mathematical expression.

    This is currently used in `calc` command.

    Parameter:
    - `expression`: The expression to calculate. Example: `5+5`.

    Return: The result of the expression.
    - If a `ZeroDivisionError` is raised, it will be "Infinity/Undefined".
    - If an `Exception` is raised, it will be "Error".
    """

    safe_list = ['acos', 'asin', 'atan', 'atan2', 'ceil', 'cos', 
                 'cosh', 'degrees', 'e', 'exp', 'fabs', 'floor', 
                 'fmod', 'frexp', 'hypot', 'ldexp', 'log', 'log10', 
                 'modf', 'pi', 'pow', 'radians', 'sin', 'sinh', 'sqrt', 
                 'tan', 'tanh']
    safe_dict = dict([(k, locals().get(k, None)) for k in safe_list])
    answer = "" 
    try:
        answer = eval(expression, {"__builtins__":None}, safe_dict)
        answer = str(answer)
    except ZeroDivisionError as zde:
        answer = "Infinity/Undefined"
    except Exception:
        answer = "Error"
    return answer

def mention(discord_object : discord.Object) -> str:
    """
    A utility function that returns a mention string to be used.

    The only reason this function exists is because `discord.Role.mention` being retarded when the role is @everyone.
    In that case, the function will return directly @everyone, not @@everyone. Otherwise, the function just simply return object.mention.

    Because of this, you can use the default `.mention` unless it's a `discord.Role`.

    Note that if there's a custom role that's literally named `@everyone` then this function will return @everyone, not @@everyone.

    Parameter:
    - `discord_object`: A Discord Object that is mentionable, including `discord.abc.User`, `discord.abc.GuildChannel` and `discord.Role`.

    Return: The string used to mention the object.
    - If the parameter's type does not satisfy the above requirements, it returns empty string.
    """
    if isinstance(discord_object, discord.abc.User):
        return discord_object.mention
    elif isinstance(discord_object, discord.abc.GuildChannel):
        return discord_object.mention
    elif isinstance(discord_object, discord.Role):
        if discord_object.name == "@everyone":
            return "@everyone"
        else:
            return discord_object.mention
    else:
        return ""
