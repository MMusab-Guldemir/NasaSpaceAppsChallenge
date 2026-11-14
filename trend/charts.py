"""Plotly charts for the Earth System Trend Detective.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

Styling follows a light chart surface with recessive hairline grids, 2 px lines, 8 px markers,
one y-axis per chart and a unified hover tooltip. All visible labels are passed in by the app, so
the charts work in every interface language.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRIDLINE = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES_1 = "#2a78d6"  # observed values (blue)
SERIES_2 = "#eb6834"  # fitted trend (orange)
BAND_FILL = "rgba(235, 104, 52, 0.16)"
FONT_FAMILY = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def _style(
    fig: go.Figure, x_title: str, y_title: str, show_legend: bool, separators: str
) -> go.Figure:
    # The chart title is rendered by the app above the chart, so the legend can sit below the
    # x-axis and wrap freely on narrow screens without covering the plot.
    fig.update_layout(
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"family": FONT_FAMILY, "color": TEXT_SECONDARY, "size": 13},
        separators=separators,
        hovermode="x unified",
        hoverlabel={"bgcolor": "#ffffff", "font": {"color": TEXT_PRIMARY}},
        margin={"l": 64, "r": 24, "t": 16, "b": 120 if show_legend else 56},
        height=460 if show_legend else 360,
        showlegend=show_legend,
        legend={"orientation": "h", "yanchor": "top", "y": -0.18, "xanchor": "left", "x": 0},
    )
    fig.update_xaxes(
        title=x_title, showgrid=False, linecolor=AXIS, ticks="outside", tickcolor=AXIS, zeroline=False
    )
    fig.update_yaxes(title=y_title, gridcolor=GRIDLINE, gridwidth=1, linecolor=AXIS, zeroline=False)
    return fig


def annual_trend_figure(
    annual: pd.DataFrame,
    band: pd.DataFrame,
    *,
    series_name: str,
    trend_name: str,
    band_name: str,
    x_title: str,
    y_title: str,
    unit: str,
    separators: str = ".,",
) -> go.Figure:
    """Annual values with the fitted linear trend and its 95% confidence band."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=band["year"], y=band["high"], mode="lines", line={"width": 0},
            hoverinfo="skip", showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=band["year"], y=band["low"], mode="lines", line={"width": 0}, fill="tonexty",
            fillcolor=BAND_FILL, name=band_name, hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=annual["year"], y=annual["value"], mode="lines+markers", name=series_name,
            line={"color": SERIES_1, "width": 2},
            marker={"size": 8, "color": SERIES_1, "line": {"color": SURFACE, "width": 2}},
            hovertemplate=f"%{{y:.2f}} {unit}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=band["year"], y=band["fit"], mode="lines", name=trend_name,
            line={"color": SERIES_2, "width": 2},
            hovertemplate=f"%{{y:.2f}} {unit}<extra></extra>",
        )
    )
    return _style(fig, x_title, y_title, True, separators)


def monthly_figure(
    monthly: pd.DataFrame, *, x_title: str, y_title: str, unit: str, separators: str = ".,"
) -> go.Figure:
    """Monthly values, including the seasonal cycle, for context."""
    fig = go.Figure(
        go.Scatter(
            x=monthly["date"], y=monthly["value"], mode="lines",
            line={"color": SERIES_1, "width": 1.5},
            hovertemplate=f"%{{y:.2f}} {unit}<extra></extra>",
        )
    )
    return _style(fig, x_title, y_title, False, separators)


def sparkline_figure(annual: pd.DataFrame, band: pd.DataFrame | None = None) -> go.Figure:
    """A tiny, static annual series with its trend line for the clue cards."""
    fig = go.Figure(
        go.Scatter(
            x=annual["year"], y=annual["value"], mode="lines",
            line={"color": SERIES_1, "width": 1.5}, hoverinfo="skip",
        )
    )
    if band is not None:
        fig.add_trace(
            go.Scatter(
                x=band["year"], y=band["fit"], mode="lines",
                line={"color": SERIES_2, "width": 1.5}, hoverinfo="skip",
            )
        )
    fig.update_layout(
        height=64, margin={"l": 0, "r": 0, "t": 4, "b": 4}, showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig
