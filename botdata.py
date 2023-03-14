from pymongo import MongoClient
from model import *
from typing import List, Tuple

class BotData():
    '''
    Provides functions to interact with bot data stored in mongo DB.
    '''
    def __init__(self, url, db_name='BOTDATA', games_config=None):
        self.mongo_client = MongoClient(url)
        self.db = self.mongo_client[db_name]
        init_model(self.db)

        if(games_config):
            self._init_games_config(games_config)

    #Private methods
    def _init_games_config(self, games_config):
        '''
        Syncs the provided games_config dict state with the state of the DB.
        Only adds new channels and games if they are not currently present in DB.
        Should we be able to toggle enabled state on existing channels/games with this?
        '''
        for config in games_config:
            channel_list = config['channel']
            name = config['name']
            enabled = config['enabled']
            if not self._get_game(name):
                #TODO add config support for categories.
                #Currently every game gets one default time category with the same fmt
                game = self.add_game(name, [('Default', '%H:%M:%S', True)], enabled)
            else:
                game = self._get_game(name)

            for channel in channel_list:
                if not self._get_channel(channel):
                   new_channel = self._add_channel(channel, [game])
                else:
                    chan = self._get_channel(channel)
                    if game.name not in self.get_games_in_channel(chan.name) + self.get_games_in_channel(chan.name, False):
                        self._add_game_to_channel(game, chan)

    def _get_channel(self, name: str):
        return Channel.find(Channel.name == name).first_or_none()

    def _get_game(self, name: str):
        return Game.find(Game.name == name).first_or_none()

    def _add_channel(self, name: str, games: List[Game]):
        new_channel = Channel(name=name, games=games)
        new_channel.save()
        return new_channel

    def _add_game_to_channel(self, game: Game, channel: Channel):
        channel.games.append(game)
        channel.save()

    #Public methods
    def add_game(self, name: str, categories: List[Tuple[str, str, bool]], is_enabled: bool = True):
        cat_list = []
        for cat in categories:
            cat_list.append(Category(name=cat[0], score_fmt=cat[1], is_enabled=cat[2]))

        new_game = Game(name=name, is_enabled=is_enabled, categories=cat_list)
        new_game.save()

        return new_game

    def add_score(self, player_id: str, game_name: str, value: str, category: str='Default'):
        print("Adding score")
        game = self._get_game(game_name)
        print(f"Got game {len(game.categories)}")
        #TODO Validate score format.
        if(len(game.categories) > 0):#TODO I think the walrus operator can help clean this up.
            cat = [cat for cat in game.categories if cat.name == category][0]
            print(f"Category is {cat.name}")
            score = Score(player_id=player_id, value=value)
            print("Created new score object")
            cat.scores.append(score)
            print("Inserted new score")
            game.save()
            print("Saved score to game")
        else:
            print(f"Failed to add score {player_id}:{value} for {game_name}:{category}.")

    def get_active_channels(self):
        '''
        Returns a list of active channel names.
        A channel is considered active if it has at least one active game within it.
        '''
        active_channel_list = []
        for game_name in self.get_active_games():
            game = self._get_game(game_name)
            channels = Channel.find_all(fetch_links = True)
            for channel in channels:
                if game in channel.games:
                    active_channel_list.append(channel.name)

        return active_channel_list

    #TODO maybe create a sepearate method to get active Game objects, or maybe just get the names in the bot.py code?
    def get_active_games(self):
        '''
        Returns a list of active game names.
        '''
        return [game.name for game in Game.find_many(Game.is_enabled == True)]

    #Assumes channel names are uniqe. Could require a (channel, server) pair if multiple servers need to be considered.
    def get_games_in_channel(self, channel_name, game_enabled = True):
        channel =  Channel.find(Channel.name == channel_name, fetch_links = True).first_or_none()
        if(channel):
            return [game.name for game in channel.games if game.is_enabled == game_enabled]

    def get_categories_for_game(self, game_name, category_enabled = True):
        game = self._get_game(game_name)
        print(f"Got game: {game.name}")
        if(game):
            cat_list = [category.name for category in game.categories if category.is_enabled == category_enabled]
            print(f"Got Categories: {cat_list}")
            return cat_list
        else:
            return []

    def get_scores(self, game_name, category_name='Default'):
        game = self._get_game(game_name)
        cat = [cat for cat in game.categories if cat.name == category_name][0]
        return [(score.player_id, score.value, score.create_time) for score in cat.scores]

    def is_game_available_for_channel(self, game_name, channel_name):
        return game_name in self.get_games_in_channel(channel_name)

    def is_category_available_for_game(self, category_name, game_name):
        return category_name in self.get_categories_for_game(game_name)
