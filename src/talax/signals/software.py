"""Whether an image editor left its name in the file."""

from __future__ import annotations

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
                f"The file was saved by an image editor: {', '.join(editors)}. "
                "Editing is often legitimate (cropping, exposure), but the "
                "image is no longer exactly what the camera produced.",
                evidence,
            )
        if photoshop_block:
            return Result(
                self.id,
                State.TO_CHECK,
                "The file contains an Adobe Photoshop data block, a trace "
                "left by Adobe editing software.",
                evidence,
            )
        if software:
            return Result(
                self.id,
                State.CONSISTENT,
                f"Recorded software: {', '.join(software)}. It is not one of "
                "the image editors Tala X recognises; that list is limited, "
                "and many editors write nothing at all.",
                evidence,
            )
        return Result(
            self.id,
            State.UNVERIFIABLE,
            "No software is recorded in the file. Many editors and platforms "
            "write nothing, so this neither suggests nor rules out editing.",
            evidence,
        )
