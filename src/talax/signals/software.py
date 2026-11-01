"""Whether an image editor left its name in the file."""

from __future__ import annotations

from talax.i18n import Message
from talax.model import Context, Result, State
from talax.traits import editors_in, software_strings


class EditingSoftware:
    id = "software"
    name = "Editing software"

    def is_relevant(self, ctx: Context) -> bool:
        return True

    def evaluate(self, ctx: Context) -> Result:
        software = software_strings(ctx.metadata)
        photoshop_block = any(k.startswith("Photoshop:") for k in ctx.metadata.tags)
        evidence: dict[str, object] = {
            "software": list(software),
            "photoshop_block": photoshop_block,
        }
        editors = editors_in(software)

        if editors:
            return Result(
                self.id,
                State.TO_CHECK,
                Message("software.editor", {"editors": ", ".join(editors)}),
                evidence,
            )
        if photoshop_block:
            return Result(
                self.id,
                State.TO_CHECK,
                Message("software.photoshop_block"),
                evidence,
            )
        if software:
            return Result(
                self.id,
                State.CONSISTENT,
                Message("software.other", {"software": ", ".join(software)}),
                evidence,
            )
        return Result(
            self.id,
            State.UNVERIFIABLE,
            Message("software.none"),
            evidence,
        )
