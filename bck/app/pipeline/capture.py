"""What an officer is told when a capture is refused, and the shape that tells them.

The quality gate is the one stage that can end a scan without a verdict, so what it
returns is deliberately not a verdict and cannot become one. A rejection carries no
findings and no ``Verdict`` member; there is no shape in which a photograph we could not
read reaches an officer looking like a conclusion about the package.

An instruction is not decoration either. An officer told only that the image was rejected
has no way to fix it and will submit the same photograph again, so every failing reason
carries the specific thing to do differently.
"""

from app.contracts import ContractModel
from app.modules.vision.preprocess import QualityReason

CAPTURE_INSTRUCTIONS: dict[QualityReason, str] = {
    QualityReason.BLUR_EXCEEDED: (
        "The image is too blurred to read a declaration from. Hold the camera steady, let "
        "it focus on the label, and capture again."
    ),
    QualityReason.GLARE_EXCEEDED: (
        "Glare is covering part of the label. Move the light source or the package so the "
        "reflection falls off the panel, and capture again."
    ),
    QualityReason.INCOMPLETE_LABEL: (
        "The label does not fill enough of the frame to be read completely. Move closer "
        "so the whole declaration panel is inside the frame, and capture again."
    ),
    QualityReason.IMAGE_EMPTY: (
        "No image was received. Capture the declaration panel and submit again."
    ),
}
"""What to tell the officer for each way a capture can fail.

One instruction per reason, and a guard test asserts every failing
:class:`~app.modules.vision.preprocess.QualityReason` has one — an officer told only that
the image was rejected has no way to fix it, and will submit the same photograph again.
"""


class QualityRejection(ContractModel):
    """A capture the gate refused, and what the officer should do about it.

    Deliberately not a verdict and not convertible into one. It carries no findings and no
    ``Verdict`` member, so there is no shape in which a rejected capture reaches an
    officer looking like a conclusion about the package.
    """

    reason_code: QualityReason
    instruction: str
    blur_score: float
    glare_ratio: float
    coverage_ratio: float
