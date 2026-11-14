"""How the seasons were removed: each month compared with the usual value of its calendar month.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

Monthly values swing with the seasons far more than they change from one decade to the next. The
verdict removes the seasons by using one value per year (``to_annual`` in trend/stats.py). This module
shows a second way that keeps every month: each month minus the usual value of its calendar month (the
mean of all Januaries, all Februaries and so on), smoothed with a centred 12-month average. The
challenge statement suggests removing the seasonal cycle; this makes that step visible.
"""
from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go

from trend.charts import (
    AXIS,
    FONT_FAMILY,
    GRIDLINE,
    SERIES_1,
    SERIES_2,
    SURFACE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from trend.i18n import num
from trend.variables import Variable

SMOOTH_MONTHS = 12  # window of the centred moving average
SMOOTH_MIN_MONTHS = 6  # months with data needed inside the window
MIN_RATIO = 1.5  # the comparison sentence is shown only when the seasons clearly outweigh the trend
COLUMNS = ["date", "value", "usual", "anomaly", "smooth"]

SEASON_TEXT = {
    "en": {
        "title": "Monthly values and the seasonal cycle",
        "option_with": "With the seasonal cycle",
        "option_removed": "Seasonal cycle removed",
        "anomaly": "Difference from the usual value of that month",
        "smooth": "12-month average",
        "y_title": "Difference ({unit})",
        "caption": (
            "Each month minus the usual value of its calendar month over the chosen years: for example, "
            "every January minus the average of all Januaries. The thick line is the average of the 12 "
            "months around each point."
        ),
        "sentence": (
            "In a typical year the monthly value swings by {swing} {unit} between its highest and lowest "
            "month. The fitted line changes the monthly value by {rate} {unit} per decade, about {ratio} "
            "times less, so the detective "
            "removes the seasons first: here by comparing each month with its own usual value, and in "
            "the verdict by using one value per year."
        ),
    },
    "tr": {
        "title": "Aylık değerler ve mevsim döngüsü",
        "option_with": "Mevsim döngüsüyle",
        "option_removed": "Mevsim döngüsü çıkarılmış",
        "anomaly": "O ayın olağan değerinden fark",
        "smooth": "12 aylık ortalama",
        "y_title": "Fark ({unit})",
        "caption": (
            "Her ayın değerinden, seçilen yıllarda o takvim ayının olağan değeri çıkarılır: örneğin her "
            "ocaktan bütün ocakların ortalaması çıkarılır. Kalın çizgi, her noktanın çevresindeki 12 ayın "
            "ortalamasıdır."
        ),
        "sentence": (
            "Olağan bir yılda aylık değer, en yüksek ve en düşük ay arasında {swing} {unit} oynar. Çizgiye "
            "göre aylık değer ise on yılda {rate} {unit} değişiyor, yani yaklaşık {ratio} kat daha az; bu "
            "yüzden dedektif önce "
            "mevsimleri çıkarır: burada her ayı kendi olağan değeriyle karşılaştırarak, kararda ise yılda "
            "tek değer kullanarak."
        ),
    },
}


def season_text(lang: str, key: str, **values) -> str:
    text = SEASON_TEXT.get(lang, SEASON_TEXT["en"])[key]
    return text.format(**values) if values else text


def _month_series(monthly: pd.DataFrame) -> pd.Series:
    """One value per month on a complete monthly range, so missing months stay as NaN gaps.

    Dates are moved to the first of their month and duplicate months are averaged, as in ``to_annual``.
    """
    df = monthly.loc[:, ["date", "value"]].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.to_period("M").dt.to_timestamp()
    df["value"] = df["value"].astype(float)
    series = df.groupby("date")["value"].mean()
    if series.empty:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([], name="date"))
    full = pd.date_range(series.index.min(), series.index.max(), freq="MS", name="date")
    return series.reindex(full)


def deseasonalize(monthly: pd.DataFrame) -> pd.DataFrame:
    """Monthly differences from the usual value of each calendar month.

    ``monthly`` needs ``date`` and ``value``. Returns one row per month from the first to the last month
    given, with ``date``, ``value``, ``usual`` (mean of that calendar month over the given rows, ignoring
    missing values), ``anomaly`` (value minus usual) and ``smooth`` (centred 12-month rolling mean of the
    anomaly, needing at least 6 months with data). Missing months are NaN in ``value`` and ``anomaly``.
    """
    series = _month_series(monthly)
    if series.empty:
        return pd.DataFrame({column: pd.Series(dtype="datetime64[ns]" if column == "date" else float)
                             for column in COLUMNS})
    usual = series.groupby(series.index.month).transform("mean")
    anomaly = series - usual
    smooth = anomaly.rolling(SMOOTH_MONTHS, center=True, min_periods=SMOOTH_MIN_MONTHS).mean()
    return pd.DataFrame({
        "date": series.index,
        "value": series.to_numpy(),
        "usual": usual.to_numpy(),
        "anomaly": anomaly.to_numpy(),
        "smooth": smooth.to_numpy(),
    })


def seasonal_swing(monthly: pd.DataFrame) -> float:
    """Size of the seasonal cycle: the highest minus the lowest of the 12 calendar-month means.

    Calendar months without data are left out; 0.0 when fewer than 2 calendar months have data (for
    example a yearly product with one value per year).
    """
    series = _month_series(monthly)
    means = series.groupby(series.index.month).mean().dropna()
    if len(means) < 2:
        return 0.0
    return float(means.max() - means.min())


def months_in_period(
    monthly: pd.DataFrame, start_year: int, end_year: int, year_starts_month: int = 1
) -> pd.DataFrame:
    """The monthly rows of the years ``start_year`` to ``end_year``, labelled as in ``to_annual``.

    A water year (``year_starts_month`` other than 1) is labelled by the calendar year in which it ends,
    so water year 2001 runs from October 2000 to September 2001.
    """
    dates = pd.to_datetime(monthly["date"])
    label = dates.dt.year
    if year_starts_month != 1:
        label = label + (dates.dt.month >= year_starts_month).astype(int)
    return monthly[label.between(start_year, end_year)]


def monthly_rate_per_decade(slope_per_decade: float, variable: Variable) -> float:
    """The trend per decade in the unit of one monthly value.

    A yearly total (aggregation "sum") adds up the months in ``season_months``, so its trend is shared
    out over those months; a yearly mean already has the unit of one month.
    """
    if variable.aggregation == "sum":
        return slope_per_decade / len(variable.season_months)
    return slope_per_decade


def season_sentence(
    lang: str, swing: float, rate_per_decade: float, unit: str, decimals: int = 2
) -> str | None:
    """The sentence comparing the seasonal swing with the trend, or None when it would mislead.

    ``rate_per_decade`` must be in the unit of one monthly value (see ``monthly_rate_per_decade``). None
    when the swing or the shown rate is zero or not finite, or when the swing is less than ``MIN_RATIO``
    times the trend per decade (as for CO2, which rises faster than it swings).
    """
    if not (math.isfinite(swing) and math.isfinite(rate_per_decade)):
        return None
    if swing <= 0 or round(rate_per_decade, decimals) == 0:
        return None
    ratio = swing / abs(rate_per_decade)
    if ratio < MIN_RATIO:
        return None
    return season_text(
        lang, "sentence", swing=num(swing, lang, decimals), unit=unit,
        rate=num(rate_per_decade, lang, decimals, signed=True),
        ratio=num(ratio, lang, 0 if ratio >= 10 else 1),
    )


def anomaly_figure(
    table: pd.DataFrame,
    lang: str,
    *,
    x_title: str,
    y_title: str,
    unit: str,
    separators: str = ".,",
    decimals: int = 2,
) -> go.Figure:
    """Monthly differences from the usual value (thin line), their 12-month average (thick) and zero."""
    hover = f"%{{y:+.{decimals}f}} {unit}<extra></extra>"
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=table["date"], y=table["anomaly"], mode="lines", name=season_text(lang, "anomaly"),
            line={"color": SERIES_1, "width": 1.2}, hovertemplate=hover,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=table["date"], y=table["smooth"], mode="lines", name=season_text(lang, "smooth"),
            line={"color": SERIES_2, "width": 3}, hovertemplate=hover,
        )
    )
    fig.add_hline(y=0, line_color=TEXT_SECONDARY, line_width=1, layer="below")
    # The legend sits above the plot, so a short chart keeps most of its height for the lines.
    fig.update_layout(
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"family": FONT_FAMILY, "color": TEXT_SECONDARY, "size": 13},
        separators=separators,
        hovermode="x unified",
        hoverlabel={"bgcolor": "#ffffff", "font": {"color": TEXT_PRIMARY}},
        margin={"l": 64, "r": 24, "t": 40, "b": 48},
        height=320,
        showlegend=True,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
    )
    fig.update_xaxes(
        title=x_title, showgrid=False, linecolor=AXIS, ticks="outside", tickcolor=AXIS, zeroline=False,
        hoverformat="%m.%Y" if lang == "tr" else "%b %Y",  # numeric months avoid English names in Turkish
    )
    fig.update_yaxes(title=y_title, gridcolor=GRIDLINE, gridwidth=1, linecolor=AXIS, zeroline=False)
    return fig
