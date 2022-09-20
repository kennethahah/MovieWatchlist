from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Movie:
    _id: str
    title: str
    director: str
    year: int
    cast: list[str] = field(default_factory=list)
    series: list[str] = field(default_factory=list)
    last_watched: datetime = None
    rating: int = 0
    tags: list[str]= field(default_factory=list)
    description: str = None
    video_link: str = None

@dataclass
class User:
    _id: str
    email: str
    nickname: str
    password: str
    create_date: datetime = None
    last_login: datetime = None
    movies: list[str] = field(default_factory=list) ## list of movie _id belonging to current user