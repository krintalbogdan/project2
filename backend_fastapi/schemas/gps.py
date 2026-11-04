from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel
'''
class StoryOptionsSchema(BaseModel):
    text: str
    node_id: Optional[int] = None

class StoryNodeBase(BaseModel):
    content: str
    is_ending: bool = False
    is_winning_ending: bool = False

class CompleteStoryNodeResponse(StoryNodeBase):
    id: int
    options: List[StoryOptionsSchema]

    class Config:
        from_attributes = True
'''

class CreateJob(BaseModel):
    from_coord: list[float]
    to_coord: list[float]
    algorithm: str

class CreateJobResponse(BaseModel):
    id: int

class ProcessQuery(BaseModel):
    id: int

class QueryResponse(BaseModel):
    status: str
    path: list[list[int]]

