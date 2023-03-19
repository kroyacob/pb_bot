import yaml
import unittest
from botdata import BotData
from model import *

class BotDataIntegrationTest(unittest.TestCase):
    TEST_DB_NAME = "BOTTESTDATA"
    #@classmethod
    def _load_test_config(configName: str):
        try:
            with open(configName, 'r') as config_file:
                return yaml.load(config_file, Loader=yaml.FullLoader)
        except Exception as e:
            BotDataIntegrationTest.fail(f"Failed to load test config file: {configName} with Exception: {e}")

    @classmethod
    def setUpClass(self):
        self.config = self._load_test_config("test-config.yml")
        self.mongo_url = self.config["base_config"]["mongo_url"]
        self.games_config = self.config["games"]
        self.bot_data = BotData(self.mongo_url, self.TEST_DB_NAME)

    def setUp(self):
        #Make sure we start with a clean slate
        self.bot_data.mongo_client.drop_database(self.TEST_DB_NAME)
        self.bot_data._init_games_config(self.games_config)
        self.db = self.bot_data.mongo_client.BOTTESTDATA


    def test_init_config(self):
        #Init games config again to check for idempotency
        self.bot_data._init_games_config(self.games_config)

        #Check for expected collections
        db_collections = self.db.list_collection_names()
        assert_collections = ['games', 'channels']
        for collection in assert_collections:
            self.assertIn(collection, db_collections)

        #Check for expected games
        #self.bot_data.add_game("Junk game",[("test", "test", True)]) #Makes it fail
        db_games = [ game['name'] for game in self.db.games.find() ]
        assert_games = [ game['name'] for game in self.games_config ]
        self.assertEqual(assert_games, db_games)

        #Idempotency check
        db_channels = Channel.find_many()
        db_channels_fetch_links = Channel.find_many(fetch_links = True)
        no_fetch_chan_lengths = [len(chan.games) for chan in db_channels]
        fetch_chan_lengths = [len(chan.games) for chan in db_channels_fetch_links]
        self.assertEquals(no_fetch_chan_lengths, fetch_chan_lengths)

        #Check for expected channels having expected games. This gets nasty.
        db_channels = [ {channel.name : [game.name for game in channel.games ] } for channel in Channel.find_many(fetch_links = True)]
        assert_channels = [{game['name'] : game['channel']} for game in self.games_config]
        #Check for channels not loaded from config
        #assert_channels.append({"mk64" : ["Junk channel"]})
        print("Assert channels: ")
        for channel in assert_channels:
            print(f"Keys = {list(channel.keys())[0]}")
            print(f"Values = {list(channel.values())[0]}")

        print("\nDB Channels: ")
        for channel in db_channels:
            print(f"Keys = {list(channel.keys())[0]}")
            print(f"Values = {list(channel.values())[0]}")

        print("\nDB Channels: ")
        for channel in db_channels:
            d_chan_key = list(channel.keys())[0]
            d_chan_values = list(channel.values())[0]
            for a_channel in assert_channels:
                a_chan_key = list(a_channel.keys())[0]
                a_chan_values = list(a_channel.values())[0]
                if d_chan_key in a_chan_values:
                    print(f"Found d_chan_key={d_chan_key} in a_chan_values={a_chan_values}")
                    print(f"Asserting a_chan_key={a_chan_key} in d_chan_values={d_chan_values}")
                    self.assertIn(a_chan_key, d_chan_values)

    def test_get_active_games(self):
        db_active_games = set(self.bot_data.get_active_games())
        assert_active_games = set([ game['name'] for game in self.games_config if game['enabled'] == True ])

        self.assertEqual(db_active_games, assert_active_games)

    def test_get_active_channels(self):
        db_active_channels = set(self.bot_data.get_active_channels())
        assert_active_channels = [ game['channel'] for game in self.games_config if game['enabled'] == True ]
        assert_active_channels = set([ channel for sub_channel in assert_active_channels for channel in sub_channel])

        self.assertEqual(db_active_channels, assert_active_channels)

    def test_get_channels(self):
        config_channels = [ game['channel'] for game in self.games_config ]
        assert_channels = set([ channel for sub_channel in config_channels for channel in sub_channel])
        db_channels = set(self.bot_data.get_channels())

        self.assertEqual(db_channels, assert_channels)
        
    def test_get_games_in_channel(self):
        games_list = [ { game["name"] : set(game['channel']) } for game in self.games_config ]
        assert_games = {}
        for game in games_list:
            assert_games.update(game)
        db_games = {}
        for check_channel in self.bot_data.get_channels():
            games = self.bot_data.get_games_in_channel(check_channel, None)
            for game in games:
                if game in db_games:
                    db_games[game].add(check_channel)
                else:
                    db_games[game] = set([check_channel])

        self.assertEqual(db_games, assert_games)   
        
    #def test_create_subcategory(self):
        #subcategory = Category(name="Rainbow Road", score_type="Time")
        #category = Category(name="Single track", score_type="Time", score_fmt="%H:%M:%S", subcategory=[subcategory])
        #game = Game(name="mk64", is_enabled=True, categories=[category])
        #game.save()
    #def test_get_categories_for_game(self):
        #db_cats_for_game = self.bot_data.get_categories_for_game()
    
    def test_get_category(self):
        game = self.bot_data._get_game("mk64")
        category = self.bot_data._get_category(game, "Toad Turnpike")
        self.assertEqual("Toad Turnpike", category.name)

if __name__ == '__main__':
    unittest.main()
