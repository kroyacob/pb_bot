import discord
from discord.ext import commands
import yaml
from botdata import BotData
from datetime import datetime

# Loading Base Config
try:
    print("Loading Config...")
    with open("config.yml", 'r') as config_file:
        config = yaml.load(config_file, Loader=yaml.FullLoader)
except Exception as e:
    print(e)
    print("Unable to load config.yml. Make sure you created your configuration.")
    exit(1)

token               = config["base_config"]["auth_token"]
admin_role_enabled  = config["base_config"]["admin_role"]["enabled"]
admin_role_name     = config["base_config"]["admin_role"]["role"]
user_role_enabled   = config["base_config"]["user_role"]["enabled"]
user_role_name      = config["base_config"]["user_role"]["role"]
mongo_url           = config["base_config"]["mongo_url"]
db_name             = config["base_config"]["db_name"]
# DB Data init and config loading
bot_data = BotData(mongo_url, db_name, "games-config.yml")

active_channels = bot_data.get_active_channels()#[game['channel'] for game in config['games'] if game['enabled']]
active_games    = bot_data.get_active_games()#[game['name'] for game in config['games'] if game['enabled']]

print(f'Active Channels: [{", ".join(active_channels)}]')
print(f'Active Games: [{", ".join(active_games)}]')

# Bot Init
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix = '!', intents=intents)

# Error Handling Setup
class InvalidChannelCheckFailure(commands.CheckFailure):
    pass

# Bot Basic Events
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

# Custom Checks
def check_admin_role_config():
    def predicate(ctx):
        return True

    if admin_role_enabled:
        return commands.has_role(admin_role_name)
    else:
        return commands.check(predicate)

def check_user_role_config():
    def predicate(ctx):
        return True

    if user_role_enabled:
        return commands.has_role(user_role_name)
    else:
        return commands.check(predicate)

# Scenario:
# Need to check active games.
# If Game is active, check channel.
# if message came from channel, begin parsing.
# This will serve as a primary entry point for the bot and logic needs to be available for every command, so a generic call is needed.

def determine_valid_channel():
    # More or less, for all enabled games, grab all valid channels and determine if the command should continue.
    # Ideally, an exception that results in a channel message is thrown for channels in the game list.
    # Otherwise, a silent exception should occur to avoid spamming channels that are not bot enabled.
    def predicate(ctx):
        channel_name = ctx.channel.name
        if channel_name in bot_data.get_active_channels():
            return True
        else:
            raise InvalidChannelCheckFailure(f'#{channel_name} is not currently active for a game.')
    return commands.check(predicate)

#def determine_game(ctx):
    # This logic will be required to be heavily modified when multi-game channel support is added.
    # Since filtering has already been done with determine_valid_channel(), we can hopefully safely assume we do not need to check active status for the game.
    #channel_name = ctx.channel.name
    #if channel_name in bot_data.get_active_channels():
    #    return bot_data.get_games_in_channel(channel_name)


@determine_valid_channel()
@bot.command()
async def add(ctx, *args):
    pass
    #args = ctx.args
    #kwargs = ctx.kwargs.get('game_name')
    #for arg in args:
        #print(f"Got arg: {arg}")
    #await ctx.send(f'[{kwargs}] Just testing... ')

#def validate_name_and_category(game_name, category_name='Default'):


#TODO Add autocomple for games in current channel
#TODO Add autocomplete for categories of selected game
#TODO 'Default' is a special category case that needs to be fleshed out.
#TODO Implement as slash command?
#TODO Better validation. Score value validation doens't exist yet.
@determine_valid_channel()
@bot.command()
async def add_score(ctx, game_name, score, category_name='Default'):
    user_id = ctx.message.author.id
    print("Getting user_name")
    user_name = ctx.message.author.name
    print(f"Got user_name {user_name}")
    channel_name = ctx.channel.name

    #Validate game
    active_game_list = bot_data.get_games_in_channel(channel_name)
    print(f"Active games: {active_game_list}")
    if not game_name in active_game_list:
        await ctx.send(f'Invalid game selected for this channel. Valid games are {", ".join(active_game_list)}')
        return False

    #Validate category
    active_category_list = bot_data.get_categories_for_game(game_name)
    print(f"Active categories: {active_category_list}")
    if not category_name in active_category_list:
        await ctx.send(f'Invalid category selected for this game. Valid categoreis are {", ".join(active_category_list)}')
        return False

    #Add score data
    bot_data.add_score(user_name, game_name, score, category_name)
    await ctx.send(f'Successfully added score={score} to {game_name}:{category_name} for user {user_name}')

@determine_valid_channel()
@bot.command()
async def list_scores(ctx, game_name, category_name='Default'):
    user_id = ctx.message.author.id
    channel_name = ctx.channel.name
    #Validate game
    active_game_list = bot_data.get_games_in_channel(channel_name)
    print(f"Active games: {active_game_list}")
    if not game_name in active_game_list:
        await ctx.send(f'Invalid game selected for this channel. Valid games are {", ".join(active_game_list)}')
        return False

    #Validate category
    active_category_list = bot_data.get_categories_for_game(game_name)
    print(f"Active categories: {active_category_list}")
    if not category_name in active_category_list:
        await ctx.send(f'Invalid category selected for this game. Valid categoreis are {", ".join(active_category_list)}')
        return False

    score_list = bot_data.get_scores(game_name)
    print(f"Got score_list: {score_list}")
    msg_list = []
    for score in score_list:
        user_name = score[0]
        create_time = score[2].strftime("%m/%d/%Y %H:%M:%S")
        value = score[1]
        msg_list.append(f"{user_name} set {value} on {create_time}")

    msg = "\n".join(msg_list)
    if(len(score_list) > 0):
        await ctx.send(f'Scores set for {game_name}:{category_name}\n {msg}')
    else:
        await ctx.send(f'No scores set for {game_name}:{category_name}')


# Error Handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, InvalidChannelCheckFailure):
        await ctx.send(error)
    if isinstance(error, discord.ext.commands.errors.MissingRole):
        await ctx.send(error)

@add.error
async def add_error(ctx, error):
    print(f"Add Command Error. : [{error}]")

# Launch
bot.run(token)