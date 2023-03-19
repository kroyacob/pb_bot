import uuid
from datetime import datetime, time
from typing import List, Optional
from pydantic import BaseModel, Field
from bunnet import Document, Link, Indexed, init_bunnet

class Score(BaseModel):
    #score_id: Indexed(int)
    id: str = Field(default_factory=uuid.uuid4, alias='_id')
    player_id: str
    create_time: datetime = datetime.now()

    class Settings:
        is_root = True
        #collection = "scores"   

class TimeScore(Score):
    value: datetime

class PointScore(Score):
    value: int

class Category(BaseModel):
    name: str = 'Default'
    label: str = 'Category'
    is_enabled: bool = True
    score_type: str
    score_fmt: Optional[str]
    scores: Optional[List[TimeScore|PointScore]] = []

class Category(Category):
    categories: Optional[List[Category]]

class Game(Document):
    #id: str = Field(default_factory=uuid.uuid4, alias='_id')
    name: str
    is_enabled: bool
    categories: List[Category] = []

    class Settings():
        name = 'games'

class Channel(Document):
    name: str
    games: List[Link[Game]] = [] #TODO Should this be optional?

    class Settings():
        name = 'channels'

# End of schema definitions
def init_model(db):
    init_bunnet(database=db, document_models=[Channel, Game ])
