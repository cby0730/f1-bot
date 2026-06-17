from pydantic import BaseModel


class Driver(BaseModel):
    driver_id: str
    permanent_number: str | None = None
    code: str | None = None
    given_name: str
    family_name: str
    date_of_birth: str | None = None
    nationality: str | None = None
    url: str | None = None
    # From OpenF1
    headshot_url: str | None = None
    team_name: str | None = None
    team_colour: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.given_name} {self.family_name}"


class DriverStanding(BaseModel):
    position: int
    points: float
    wins: int
    driver: Driver
    constructor_name: str
