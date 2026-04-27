"""이미지 생성 레이아웃 공통 제약."""

GLOBAL_IMAGE_STYLE_PROMPT = "cinematic illustration"

GLOBAL_IMAGE_LAYOUT_PROMPT = (
    "single uninterrupted full-bleed illustration, one camera shot, "
    "edge-to-edge composition, borderless artwork, no blank white margins, "
    "no empty padding, no split-screen, no before-and-after composition, "
    "no sequential panels, no comic panels, no panel gutters, "
    "no speech bubbles, no dialogue balloons, no captions, no inset images, "
    "no collage layout"
)

SINGLE_PANEL_IMAGE_CONSTRAINT = (
    "Single uninterrupted scene in one camera shot only; no split-screen, "
    "no before-and-after composition, no sequential panels, no comic panels, "
    "no panel gutters, no inset images, and no collage layout."
)

COMMON_IMAGE_PROMPT_LINES = (
    "Common image contract: vertical 3:4 cinematic illustration.",
    "Single-panel illustration only.",
    SINGLE_PANEL_IMAGE_CONSTRAINT,
    (
        "No readable text, letters, words, numbers, captions, dialogue "
        "balloons, sound effects, subtitles, signage, labels, logos, or "
        "watermarks anywhere in the image."
    ),
    (
        "Do not render documents, white text boxes, book pages, forms, "
        "posters, menus, HUDs, chat windows, UI elements, or comic panels."
    ),
)
