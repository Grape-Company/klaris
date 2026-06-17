from __future__ import annotations

from collections.abc import Mapping, Sequence

import discord

from bot.i18n import gettext


def build_answer_embed(
    response: str,
    sources: Sequence[Mapping[str, object]],
    answer_id: str | None,
    color: discord.Color | None,
    language: str,
) -> discord.Embed:
    """Build the main answer embed with sources as inline fields."""
    if color is None:
        color = discord.Color.green()

    embed = discord.Embed(description=response, color=color)

    source_count = len(sources)
    for source in sources[:5]:
        title = str(source.get("title", "—"))
        url = str(source.get("url", ""))
        embed.add_field(name=title, value=url or "—", inline=False)

    sources_label = gettext(language, "sources_label")
    answer_id_label = gettext(language, "answer_id_label")

    footer = f"{sources_label}: {source_count}"
    if answer_id:
        footer += f" | {answer_id_label}: {answer_id[:8]}"

    embed.set_footer(text=footer)
    return embed


def build_error_embed(message: str, language: str) -> discord.Embed:
    """Build a red error embed."""
    _ = language
    return discord.Embed(description=message, color=discord.Color.red())


def build_help_embed(
    commands: Sequence[tuple[str, str]],
    language: str,
) -> discord.Embed:
    """Build a help embed listing available commands."""
    embed = discord.Embed(
        title=gettext(language, "help_title"),
        description=gettext(language, "help_description"),
        color=discord.Color.blue(),
    )
    for name_key, desc_key in commands:
        embed.add_field(
            name=gettext(language, name_key),
            value=gettext(language, desc_key),
            inline=False,
        )
    return embed


def build_stats_embed(
    stats_data: Mapping[str, int | str],
    language: str,
) -> discord.Embed:
    """Build a stats embed from API stats data."""
    embed = discord.Embed(
        title=gettext(language, "stats_title"),
        color=discord.Color.blue(),
    )

    label_map: dict[str, str] = {
        "total_answers": "stats_total_answers",
        "total_feedback": "stats_total_feedback",
        "positive_feedback": "stats_positive",
        "negative_feedback": "stats_negative",
        "correction_count": "stats_corrections",
    }

    for key, label_key in label_map.items():
        value = stats_data.get(key)
        if value is not None:
            embed.add_field(
                name=gettext(language, label_key),
                value=str(value),
                inline=True,
            )

    return embed


def build_not_found_embed(response: str, language: str) -> discord.Embed:
    """Build a yellow/gold not-found embed."""
    embed = discord.Embed(description=response, color=discord.Color.gold())
    embed.set_footer(text=gettext(language, "not_found"))
    return embed
