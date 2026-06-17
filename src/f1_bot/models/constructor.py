from pydantic import BaseModel


class Constructor(BaseModel):
    constructor_id: str
    name: str
    nationality: str | None = None
    url: str | None = None


class ConstructorStanding(BaseModel):
    position: int
    points: float
    wins: int
    constructor: Constructor
