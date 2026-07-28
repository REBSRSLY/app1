"""Foster/Gabbett training-load derived metrics.

Raw sessions (Rpe TL F sheet) already carry TL = Rpe * Time (Foster's sRPE
method, computed at the data source). Everything here turns that
session-level TL into the standard sports-science monitoring figures:
acute/chronic load, ACWR, monotony and strain.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ACUTE_DAYS = 7
CHRONIC_DAYS = 28


def daily_series(rpe: pd.DataFrame, player_name: str | None = None) -> pd.Series:
    """Per-calendar-day total TL, reindexed over the full date range with
    missing (rest) days filled as 0 -- required so rolling windows and
    monotony's std reflect real rest days, not just gaps in the sheet.

    player_name=None aggregates the whole team using the *mean* TL per
    athlete who trained that day (not the raw sum), so the team series
    stays on the same scale as an individual athlete's and isn't just an
    artifact of how many players trained that day.
    """
    d = rpe.dropna(subset=["TL", "Data"])
    if player_name is not None:
        d = d[d["player_name"] == player_name]
        daily = d.groupby("Data")["TL"].sum()
    else:
        per_player_daily = d.groupby(["player_name", "Data"])["TL"].sum()
        daily = per_player_daily.groupby("Data").mean()

    if daily.empty:
        return daily
    full_range = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    return daily.reindex(full_range, fill_value=0.0)


def acute_load(daily: pd.Series) -> pd.Series:
    """This week's accumulated load: rolling 7-day sum."""
    return daily.rolling(ACUTE_DAYS, min_periods=ACUTE_DAYS).sum()


def chronic_load(daily: pd.Series) -> pd.Series:
    """Average *weekly* load over the trailing 4 weeks (28-day rolling sum
    / 4) -- the Gabbett ACWR baseline. A 28-day rolling *mean* of the daily
    values would be about 7x smaller than the acute load (a weekly total)
    and make the ratio meaningless; dividing by 4 keeps both sides of the
    ratio on the same "typical week" scale."""
    return daily.rolling(CHRONIC_DAYS, min_periods=CHRONIC_DAYS).sum() / 4


def acwr(daily: pd.Series) -> pd.Series:
    """Acute:Chronic Workload Ratio. Sweet spot ~0.8-1.3; >1.5 or <0.8
    flags a sudden spike or a de-trained drop-off."""
    chronic = chronic_load(daily)
    return acute_load(daily) / chronic.replace(0, np.nan)


def monotony(daily: pd.Series) -> pd.Series:
    """Foster monotony: rolling-week mean / std of daily TL. High (>2.0)
    means no real rest days within the week."""
    mean = daily.rolling(ACUTE_DAYS, min_periods=ACUTE_DAYS).mean()
    std = daily.rolling(ACUTE_DAYS, min_periods=ACUTE_DAYS).std()
    return mean / std.replace(0, np.nan)


def strain(daily: pd.Series) -> pd.Series:
    """Weekly TL x monotony -- combined volume-and-monotony stress."""
    return acute_load(daily) * monotony(daily)


def metrics_frame(rpe: pd.DataFrame, player_name: str | None = None) -> pd.DataFrame:
    """All derived series for one athlete (or the team, if player_name is
    None) as a single date-indexed DataFrame, computed over the athlete's/
    team's *entire* history so early points in any later display window
    still get a correct trailing 7/28-day context."""
    daily = daily_series(rpe, player_name)
    if daily.empty:
        return pd.DataFrame(columns=["daily_tl", "acute", "chronic", "acwr", "monotony", "strain"])
    return pd.DataFrame({
        "daily_tl": daily,
        "acute": acute_load(daily),
        "chronic": chronic_load(daily),
        "acwr": acwr(daily),
        "monotony": monotony(daily),
        "strain": strain(daily),
    })
