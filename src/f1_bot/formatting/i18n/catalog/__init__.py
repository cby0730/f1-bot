"""Merge the per-domain catalogs into one flat `CATALOG`.

Flat keys (``"schedule.next_race_header"``) rather than nested lookup: a key is a
single string that greps cleanly, and the language sits on the *inner* level so
adding a language never touches the key set.

Duplicate keys across domains are a programmer error and raise at import.
"""

from f1_bot.formatting.i18n.catalog.commands import COMMAND_ORDER, COMMANDS
from f1_bot.formatting.i18n.catalog.common import COMMON
from f1_bot.formatting.i18n.catalog.datetime import DATETIME
from f1_bot.formatting.i18n.catalog.extras import EXTRAS
from f1_bot.formatting.i18n.catalog.notifications import NOTIFICATIONS
from f1_bot.formatting.i18n.catalog.race_data import RACE_DATA
from f1_bot.formatting.i18n.catalog.results import RESULTS
from f1_bot.formatting.i18n.catalog.schedule import SCHEDULE
from f1_bot.formatting.i18n.catalog.settings import SETTINGS
from f1_bot.formatting.i18n.catalog.standings import STANDINGS
from f1_bot.formatting.i18n.catalog.start import START

_DOMAINS = (
    COMMON,
    DATETIME,
    SCHEDULE,
    RESULTS,
    STANDINGS,
    RACE_DATA,
    EXTRAS,
    NOTIFICATIONS,
    SETTINGS,
    START,
    COMMANDS,
)

CATALOG: dict[str, dict[str, str]] = {}
for _domain in _DOMAINS:
    _clashes = CATALOG.keys() & _domain.keys()
    if _clashes:
        raise RuntimeError(f"Duplicate i18n keys across catalog domains: {sorted(_clashes)}")
    CATALOG.update(_domain)

__all__ = ["CATALOG", "COMMAND_ORDER"]
