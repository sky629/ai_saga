from enum import Enum


class ScenarioGenre(str, Enum):
    """Genre types for game scenarios."""

    FANTASY = "fantasy"
    SCI_FI = "sci_fi"
    CYBERPUNK = "cyberpunk"
    HORROR = "horror"
    SURVIVAL = "survival"
    MYSTERY = "mystery"
    HISTORICAL = "historical"
    POST_APOCALYPTIC = "post_apocalyptic"
