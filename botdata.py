from pymongo import MongoClient
from model import *
from typing import List, Tuple
from datetime import datetime
import yaml

class BotData():
    '''
    Provides functions to interact with bot data stored in mongo DB.
    '''
    def __init__(self, url: str, db_name: str = 'BOTDATA', games_config = None):
        self.mongo_client = MongoClient(url)
        self.db = self.mongo_client[db_name]
        init_model(self.db)

        if(games_config):
            #Games config can be passed as a file or pre-loaded dict
            if(isinstance(games_config, str)):
                games_config = self.load_config_file(games_config)

            self._init_games_config(games_config)

    #Private methods
    def _init_category(self, category_config, cat_label="Category"):
        cat_name = category_config["name"]
        score_type = category_config.get("score_type", "Time")
        score_fmt = category_config.get("score_fmt", None)
        enabled = category_config.get("enabled", True)

        if "subcategory" in category_config:
            subcategory_config = category_config["subcategory"]
            cat_label = subcategory_config.get("label", "Category")
            categories = self._init_game_categories(subcategory_config["category"], cat_label)
            print("Created subcategory")
        else:
            categories = None

        category = Category(
            name=cat_name, 
            label=cat_label, 
            is_enabled=enabled, 
            score_type=score_type,
            score_fmt=score_fmt, 
            categories=categories
        )
        return category

    def _init_game_categories(self, category_config, cat_label="Category"):
        categories = []
        for category in category_config:
            categories.append(self._init_category(category, cat_label))
        return categories
        
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
            if("category" in config):
                categories = self._init_game_categories(config['category'])
            else:
                category = Category(
                    score_type="Time",
                    score_fmt="%M:%S.%f", 
                    categories=None
                )
                categories = [category]


            if not (game := self._get_game(name)):
                game = self.add_game(name, categories, enabled)
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
        return Channel.find(Channel.name == name, fetch_links = True).first_or_none()

    def _get_game(self, name: str):
        return Game.find(Game.name == name).first_or_none()

    def _get_category(self, game: Game, category_name: str):
        for category in game.categories: 
            if category.name == category_name:
                return category
            elif hasattr(category, "categories"):
                return self._get_category(category, category_name)

    def _add_channel(self, name: str, games: List[Game]):
        channel = Channel(name=name, games=games)
        channel.save()
        return channel

    def _add_game_to_channel(self, game: Game, channel: Channel):
        channel.games.append(game)
        channel.save()

    def _add_category(self, name: str, category: Category, parent_node):
        if(isinstance(parent_node, Game) or isinstance(parent_node, Category)):
            parent_node.categories.append(category)
        else:
            print(f"Invalid parent_node type {type(parent_node)}")
            return False
     
    def _add_score_to_category(self, player_id: str, category: Category, score_value: str):
        try:
            score = None
            match category.score_type:
                case "Time":
                    time = datetime.strptime(score_value, category.score_fmt)
                    score = TimeScore(player_id=player_id, value=time)
                case "Point":
                    points = int(score_value)
                    score = PointScore(player_id=player_id, value=points)
                case _:
                    print("Invalid score type selected.")
                    return False

        except ValueError as e:
            print(f"Invalid score value for {category.name}")
            print(f"Expected format is {category.score_fmt}")
            return False

        if(score):
            print("Added new score with value: {score.value} for player_id: {player_id}")
            category.scores.append(score)
            return True

        return False

    #Public methods
    def load_config_file(self, file_name: str):
        try:
            with open(file_name, 'r') as config_file:
                config = yaml.load(config_file, Loader=yaml.FullLoader)
                return config
        except Exception as e:
            print(e)
            print(f"Failed to load to load config: {file_name}")

    def add_game(self, name: str, categories: List[Category], is_enabled: bool = True):
        new_game = Game(name=name, is_enabled=is_enabled, categories=categories)
        new_game.save()
        return new_game

    def add_score(self, player_id: str, game_name: str, score_value: str, category_name: str='Default'):
        game = self._get_game(game_name)
        category = self._get_category(game, category_name)
        if(category):
            print(f"Adding score to {category.name}")
            added_score = self._add_score_to_category(player_id, category, score_value)
            if(added_score):
                game.save()
                print("Saved score to game")
            else:
                print("Failed to save score")
        else:
            print(f"Failed to add score {player_id}:{score_value} for {game_name}:{category_name}.")

    def get_channels(self):
        return [channel.name for channel in Channel.find_all()]

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
        return [game.name for game in Game.find_many(Game.is_enabled == True)]

    #Assumes channel names are uniqe. Could require a (channel, server) pair if multiple servers need to be considered.
    #game_enabled = None should return all games in the channel
    def get_games_in_channel(self, channel_name: str, game_enabled: bool = True):
        channel =  self._get_channel(channel_name)
        if(channel):
            return [game.name for game in channel.games if game_enabled is None or game.is_enabled == game_enabled]

    def get_categories_for_game(self, game_name: str, category_enabled: bool = True):
        game = self._get_game(game_name)
        print(f"Got game: {game.name}")
        if(game):
            self._get_category()
            cat_list = [category.name for category in game.categories if category.is_enabled == category_enabled]

            print(f"Got Categories: {cat_list}")
            return cat_list
        else:
            print("Game not found")
            return []

    def get_scores(self, game_name: str, category_name: str = 'Default'):
        game = self._get_game(game_name)
        category = self._get_category(game, category_name)
        if category.score_type == "Time":
            return [(score.player_id, score.value.strftime(category.score_fmt), score.create_time) for score in category.scores]
        else:
            return [(score.player_id,  score.value, score.create_time) for score in category.scores]

    def is_game_available_for_channel(self, game_name: str, channel_name: str):
        return game_name in self.get_games_in_channel(channel_name)

    def is_category_available_for_game(self, category_name: str, game_name: str):
        return category_name in self.get_categories_for_game(game_name)
