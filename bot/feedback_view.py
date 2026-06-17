from __future__ import annotations

from typing import Any

import structlog
from discord import Interaction, TextStyle
from discord.ui import Button, Modal, TextInput, View

from bot.i18n import gettext
from bot.klaris_client import KlarisApiClient

logger = structlog.get_logger()


class FeedbackModal(Modal):
    correction = TextInput(
        label="Correção (opcional)",
        style=TextStyle.paragraph,
        required=False,
        max_length=1000,
    )

    def __init__(
        self,
        answer_id: str,
        client: KlarisApiClient,
        language: str,
        rating: str = "negative",
        feedback_view: FeedbackView | None = None,
        origin_message: Any | None = None,
    ) -> None:
        super().__init__(title="Feedback — Correção")
        self.answer_id = answer_id
        self.client = client
        self.language = language
        self.rating = rating
        self.feedback_view = feedback_view
        self.origin_message = origin_message

    async def on_submit(self, interaction: Interaction) -> None:
        try:
            await self.client.submit_feedback(
                answer_id=self.answer_id,
                rating=self.rating,
                correction=self.correction.value,
            )
        except Exception:
            logger.exception(
                "feedback_submit_failed",
                answer_id=self.answer_id,
                rating=self.rating,
            )
            await interaction.response.send_message(
                gettext(self.language, "general_failure"),
                ephemeral=True,
            )
            return

        logger.info(
            "feedback_submitted",
            answer_id=self.answer_id,
            rating=self.rating,
            correction=bool(self.correction.value),
        )

        if self.feedback_view is not None:
            self.feedback_view.disable_feedback_buttons()
            if self.origin_message is not None:
                await self.origin_message.edit(view=self.feedback_view)

        await interaction.response.send_message(
            gettext(self.language, "feedback_recorded"),
            ephemeral=True,
        )


class FeedbackView(View):
    up_button: Any
    down_button: Any
    fix_button: Any

    def __init__(
        self,
        answer_id: str,
        client: KlarisApiClient,
        language: str,
        timeout: float = 180.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.answer_id = answer_id
        self.client = client
        self.language = language
        self._submitted = False

        self.up_button = Button(emoji="\U0001f44d")
        self.down_button = Button(emoji="\U0001f44e")
        self.fix_button = Button(emoji="\u270f\ufe0f", label="Corrigir")

        self.up_button.callback = self._on_positive
        self.down_button.callback = self._on_negative
        self.fix_button.callback = self._on_fix

        self.add_item(self.up_button)
        self.add_item(self.down_button)
        self.add_item(self.fix_button)

    def disable_feedback_buttons(self) -> None:
        self.up_button.disabled = True
        self.down_button.disabled = True
        self.fix_button.disabled = True

    async def _on_positive(self, interaction: Interaction) -> None:
        if self._submitted:
            return
        self._submitted = True

        try:
            await self.client.submit_feedback(
                answer_id=self.answer_id,
                rating="positive",
            )
        except Exception:
            logger.exception(
                "feedback_submit_failed",
                answer_id=self.answer_id,
                rating="positive",
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
            rating="positive",
        )

        self.disable_feedback_buttons()
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            gettext(self.language, "feedback_recorded"),
            ephemeral=True,
        )

    async def _on_negative(self, interaction: Interaction) -> None:
        if self._submitted:
            return
        self._submitted = True
        self.disable_feedback_buttons()
        origin_message = getattr(interaction, "message", None)
        if origin_message is not None:
            await origin_message.edit(view=self)

        modal = FeedbackModal(
            answer_id=self.answer_id,
            client=self.client,
            language=self.language,
            rating="negative",
            feedback_view=self,
            origin_message=origin_message,
        )
        await interaction.response.send_modal(modal)

    async def _on_fix(self, interaction: Interaction) -> None:
        if self._submitted:
            return
        self._submitted = True
        self.disable_feedback_buttons()
        origin_message = getattr(interaction, "message", None)
        if origin_message is not None:
            await origin_message.edit(view=self)

        modal = FeedbackModal(
            answer_id=self.answer_id,
            client=self.client,
            language=self.language,
            rating="negative",
            feedback_view=self,
            origin_message=origin_message,
        )
        await interaction.response.send_modal(modal)
