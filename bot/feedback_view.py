from __future__ import annotations

from typing import Any

import httpx
import structlog
from discord import Interaction
from discord.ui import Button, View

from bot.i18n import gettext

logger = structlog.get_logger()


class FeedbackView(View):
    up_button: Any
    down_button: Any

    def __init__(
        self,
        answer_id: str,
        bot_api_key: str,
        api_url: str,
        language: str,
        timeout: float = 180.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.answer_id = answer_id
        self.bot_api_key = bot_api_key
        self.api_url = api_url.rstrip("/")
        self.language = language
        self._submitted = False

        self.up_button = Button(emoji="\U0001f44d")
        self.down_button = Button(emoji="\U0001f44e")

        self.up_button.callback = self._on_positive
        self.down_button.callback = self._on_negative

        self.add_item(self.up_button)
        self.add_item(self.down_button)

    async def _on_positive(self, interaction: Interaction) -> None:
        await self._submit(interaction, "positive")

    async def _on_negative(self, interaction: Interaction) -> None:
        await self._submit(interaction, "negative")

    async def _submit(self, interaction: Interaction, rating: str) -> None:
        if self._submitted:
            return
        self._submitted = True

        parent_view = self.up_button.view

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/api/rag/feedback",
                    headers={"X-Bot-Api-Key": self.bot_api_key},
                    json={"answer_id": self.answer_id, "rating": rating},
                )
                response.raise_for_status()
        except httpx.HTTPError:
            logger.exception(
                "feedback_submit_failed",
                answer_id=self.answer_id,
                rating=rating,
            )
            self._submitted = False
            await interaction.response.send_message(
                gettext(self.language, "general_failure"),
                ephemeral=True,
            )
            return

        logger.info(
            "feedback_submitted",
            answer_id=self.answer_id,
            rating=rating,
        )

        if parent_view is not None:
            self.up_button.disabled = True
            self.down_button.disabled = True
            await interaction.response.edit_message(view=parent_view)

        await interaction.followup.send(
            gettext(self.language, "feedback_recorded"),
            ephemeral=True,
        )
