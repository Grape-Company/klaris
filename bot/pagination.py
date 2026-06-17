from __future__ import annotations

from typing import Any

from discord import Embed, Interaction
from discord.ui import Button, View


class PaginatedResponseView(View):
    prev_button: Any
    next_button: Any

    def __init__(
        self,
        pages: list[Embed],
        answer_id: str | None,
        language: str,
        timeout: float = 180.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.pages = pages
        self.answer_id = answer_id
        self.language = language
        self.current_page = 0

        self.prev_button = Button(label="\u25c0 Previous", disabled=True)
        self.next_button = Button(label="Next \u25b6", disabled=len(pages) <= 1)

        self.prev_button.callback = self._previous_page
        self.next_button.callback = self._next_page

        self.add_item(self.prev_button)
        self.add_item(self.next_button)

    async def _previous_page(self, interaction: Interaction) -> None:
        self.current_page -= 1
        await self._update(interaction)

    async def _next_page(self, interaction: Interaction) -> None:
        self.current_page += 1
        await self._update(interaction)

    async def _update(self, interaction: Interaction) -> None:
        self.prev_button.disabled = self.current_page <= 0
        self.next_button.disabled = self.current_page >= len(self.pages) - 1
        embed = self.pages[self.current_page]
        await interaction.response.edit_message(embed=embed, view=self)
