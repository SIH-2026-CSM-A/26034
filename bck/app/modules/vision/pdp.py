"""Principal display panel detection — two provenances, and the type says which.

There are exactly two ways this module can produce a region, and they are not
interchangeable:

* **model** — a YOLO detector trained on principal display panels returns a box and its
  own confidence. :class:`PDPResult`.
* **heuristic** — no weights are configured, so the region is derived from the pixels
  alone: glyph edges merged into text blocks by morphology, largest coherent block wins.
  No model, no training, no per-image accuracy. :class:`HeuristicTextRegion`.

The two are **siblings, not subclasses, and share no base**, for the reason
``app.contracts.measurement`` gives at length: a subclass would make
``isinstance(region, PDPResult)`` true while no longer guaranteeing what
:class:`PDPResult` promises, and every ``isinstance`` check written against the model type
would start passing vacuously over a heuristic guess. Rule 7 bands minimum character height
against principal display panel area, so "where the panel is" is an input to a legal
threshold; a heuristic region and a trained detection must not be one shape with a flag
that a caller may forget to read.

They agree on ``bbox``, ``confidence`` and ``area`` because a caller that only records
where the panel was found needs no branch. Anything that acts on the figure branches on
the type, or on ``method``.

The heuristic is a fallback for the absence of a trained detector, not a fallback for a
detector that ran and found nothing. An empty detection still refuses: a model that looked
and saw no panel has told us something, and substituting a guess would overwrite it.
"""

import os
from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np
import ultralytics

HEURISTIC_CONFIDENCE_PRIOR: float = 0.3
"""The confidence :class:`HeuristicTextRegion` reports. An uncalibrated prior.

It is not an accuracy, a precision, a recall or a probability, and none has been measured
for this heuristic. It is a fixed sentinel: every heuristic region carries the same value
because nothing in the method distinguishes a good region from a poor one. It is
deliberately **not comparable** to :attr:`PDPResult.confidence`, which a trained detector
produced from its own scores — the two never share a type, so no code path can rank one
against the other without first choosing to.

Calibrating it would mean measuring the heuristic against annotated panel boxes. Until
that happens the honest thing is a named constant that says so.
"""

GLYPH_EDGE_KERNEL: tuple[int, int] = (3, 3)
"""Structuring element for the morphological gradient that isolates glyph edges."""

TEXT_BLOCK_KERNEL_WIDTH_RATIO: float = 0.03
"""Width of the closing kernel that merges glyphs into text blocks, as a fraction of image
width.

Scaled rather than fixed: a kernel wide enough to bridge inter-word gaps on a 1080 px
capture merges half a 500 px capture into one blob. Uncalibrated — chosen so that the same
ratio produces a coherent block on captures at both sizes, not tuned per image.
"""

TEXT_BLOCK_KERNEL_ASPECT: int = 5
"""How much wider than tall the closing kernel is.

Text runs horizontally: merging along the line before merging across lines is what keeps a
block of print together without also swallowing the artwork above and below it.
"""

TEXT_BLOCK_KERNEL_MINIMUM_PX: int = 3
"""Floor for either kernel dimension. A 1 px structuring element closes nothing."""

MAX_FRAME_COVERAGE: float = 0.98
"""Coverage at which a heuristic region stops being a region and becomes the whole frame.

A box spanning the frame carries no information about where the panel is. Returning one
is the defect #63 removed — full-image bounds at ``confidence 0.0`` overestimate panel
area and bias Rule 7 toward POTENTIAL VIOLATION — and the heuristic can reach it honestly
on a frame with edge texture everywhere. At that point there is no coherent text region
and the module says so rather than handing back the input.
"""


@dataclass(frozen=True)
class PDPResult:
    """A principal display panel located by a trained detector.

    ``confidence`` is the detector's own score. ``area`` is in pixels²; converting it to
    physical units needs a calibration and belongs to ``app.modules.measurement``.
    """

    bbox: tuple[int, int, int, int]
    confidence: float
    area: float
    text: str = ""
    method: Literal["model"] = "model"


@dataclass(frozen=True)
class HeuristicTextRegion:
    """The largest coherent text region in a frame, found without a model.

    Not a panel detection and not named as one. Nothing here identifies the region as the
    *principal* display panel; it is the biggest run of merged print in the image, which is
    frequently the panel and is sometimes the package body or a block of ingredient text.

    Carries no ``text`` field, unlike :class:`PDPResult`: the heuristic reads glyph
    *edges*, never glyphs, so a text field could only ever be empty and would invite a
    caller to read it.
    """

    bbox: tuple[int, int, int, int]
    confidence: float
    area: float
    method: Literal["heuristic"] = "heuristic"


PDPDetection = PDPResult | HeuristicTextRegion
"""Everything :func:`detect_pdp` can return. Branch on the type, or on ``method``."""


def _largest_text_region(image) -> HeuristicTextRegion:
    """Locate the largest coherent text region using morphology alone.

    Glyph edges come out of a morphological gradient and are thresholded with Otsu, which
    picks its own level per image so no brightness constant is needed. A wide closing
    kernel then merges the edges of neighbouring characters into solid blocks, and the
    largest external contour is taken as the region.

    Raises ``ValueError`` when the image cannot be read, when no contour survives, or when
    the winning region spans the frame — all three are the same finding, that there is no
    coherent text region here, and none of them may return the frame itself.
    """
    frame = image if isinstance(image, np.ndarray) else cv2.imread(str(image))
    if frame is None:
        raise ValueError("No PDP detected in image.")

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.morphologyEx(
        gray,
        cv2.MORPH_GRADIENT,
        cv2.getStructuringElement(cv2.MORPH_RECT, GLYPH_EDGE_KERNEL),
    )
    _, binary = cv2.threshold(edges, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    height, width = gray.shape
    kernel_width = max(TEXT_BLOCK_KERNEL_MINIMUM_PX, round(width * TEXT_BLOCK_KERNEL_WIDTH_RATIO))
    kernel_height = max(TEXT_BLOCK_KERNEL_MINIMUM_PX, kernel_width // TEXT_BLOCK_KERNEL_ASPECT)
    blocks = cv2.morphologyEx(
        binary,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, kernel_height)),
    )

    contours, _ = cv2.findContours(blocks, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("No PDP detected in image.")

    x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
    if w * h >= MAX_FRAME_COVERAGE * width * height:
        raise ValueError("No PDP detected in image.")

    return HeuristicTextRegion(
        bbox=(x, y, w, h),
        confidence=HEURISTIC_CONFIDENCE_PRIOR,
        area=float(w * h),
    )


def detect_pdp(image_path, weights_path=None) -> PDPDetection:
    """Locate the principal display panel, by trained detector where one is configured.

    With weights present the detector runs and a :class:`PDPResult` comes back. With no
    resolvable weights — argument ``None``, ``PDP_WEIGHTS_PATH`` unset or blank, or a path
    that is not on disk — the morphological heuristic runs instead and returns a
    :class:`HeuristicTextRegion`, which is a different type precisely so that no caller can
    treat the guess as a detection.

    A missing weights *file* routes to the heuristic rather than raising, deliberately: the
    only production caller passes ``str(settings.pdp_weights_path)``, so an unset setting
    arrives here as the string ``"None"``. Raising on it would move the boot-time refusal
    into the first scan instead of removing it. The distinct return type is what makes the
    degradation legible; it does not also need an exception.

    Raises ``ValueError`` when there is no panel to report: an empty array, a detector that
    ran and found nothing, or a frame with no coherent text region. Never returns the whole
    image as the panel.
    """
    if isinstance(image_path, np.ndarray) and image_path.size == 0:
        raise ValueError("No PDP detected in image.")

    w = weights_path or os.getenv("PDP_WEIGHTS_PATH")
    if not w or not os.path.exists(w):
        return _largest_text_region(image_path)

    model = ultralytics.YOLO(w)
    res = model(image_path)

    if not res or not hasattr(res[0], "boxes") or len(res[0].boxes) == 0:
        raise ValueError("No PDP detected in image.")

    c = res[0].boxes.xyxy[0].cpu().numpy()
    bw, bh = int(c[2] - c[0]), int(c[3] - c[1])

    return PDPResult(
        bbox=(int(c[0]), int(c[1]), bw, bh),
        confidence=float(res[0].boxes.conf[0].cpu().numpy()),
        area=float(bw * bh),
    )
