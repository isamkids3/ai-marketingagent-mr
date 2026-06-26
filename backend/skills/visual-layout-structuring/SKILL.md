---
name: visual-layout-structuring
description: Structure composition details, aspect ratios, and spatial layout coordinates (bounding boxes) for image generation models. Use when generating complex visual ads, text overlays, multi-subject compositions, or banners.
---

# visual-layout-structuring

## Overview
Guides the agent in drafting precise spatial, compositional, and layout coordinates for text/image generation to prevent overlapping elements, poor margins, or misplaced graphics.

## Instructions

### 1. Define Aspect Ratio
Translate the requested channel or layout type into strict aspect ratio specifications:
- YouTube Thumbnail / Web Banner: `16:9`
- Instagram / TikTok Stories: `9:16`
- Instagram Feed / Standard Ad: `1:1`
- Facebook Feed / Portrait Ad: `4:5`
- Print / Presentation Slide: `3:2` or `4:3`

### 2. Map Spatial Coordinates (Bounding Boxes)
When describing the composition schema using normalized coordinates `[y1, x1, y2, x2]` (0-1000 range, top-left origin):
- **Bounding Boxes for ALL Elements (CRITICAL)**: Every entry in the `elements` list—whether it is a text label (`type: "text"`) or an object/icon/graphic/container (`type: "obj"`)—MUST have defined `bbox` coordinates. Bounding boxes are not just for text; bounding boxes for physical icons, shapes, and characters are essential to anchor them in 2D space, prevent them from overlapping, and stop the model from duplicating them.
- **Normalized Grid Concept**: The canvas is a virtual grid from 0 to 1000. 
  - `y1` (Top boundary): distance from the top edge.
  - `x1` (Left boundary): distance from the left edge.
  - `y2` (Bottom boundary): distance from the top edge.
  - `x2` (Right boundary): distance from the left edge.
  - **Height** of the element is `y2 - y1`. **Width** of the element is `x2 - x1`.
- **Safety Margins**: Maintain a buffer zone. Keep critical focal points and text away from borders (boundaries < 50 or > 950) to avoid cropping.
- **Background Separation**: Explicitly isolate the background (e.g., solid backdrop, transparent canvas, out-of-focus bokeh) from elements.
- **Focal Points & Layout Segmentation**: Ensure primary and secondary visual elements do not overlap. Segment the canvas into regions. For example:
  - **Header/Top zone**: `[0, 100, 200, 900]`
  - **Left column**: `[150, 50, 850, 200]`
  - **Right column**: `[150, 800, 850, 950]`
  - **Center main**: `[250, 200, 750, 800]`
  - **Bottom footer**: `[800, 100, 950, 900]`

- **Few-Shot Layout Example (Minimalist Movie Poster)**:
  Study this composition deconstruction for a complex minimalist film poster (`Flow` by Gints Zilbalodis) containing 12 distinct visual elements perfectly aligned:
  - Background: light beige paper texture.
  - Credits block (Top-right corner): `[18, 725, 319, 936]` (Tight width of 211, height of 301, leaving margins clean).
  - TIFF laurels (Left margin): `[334, 46, 387, 120]`
  - Golden Globe winner text (Right margin): `[531, 746, 638, 919]`
  - Main Title "Flow" (Centered, slightly lower): `[503, 102, 608, 497]`
  - Stylized Black Cat (Massive bottom focal element): `[611, 4, 956, 967]` (Spans the bottom of the canvas, overlapping no other elements).


### 3. Text Overlay Alignment & Ideogram 4.0 Fidelity (CRITICAL)
When the visual design calls for text overlays, you must adhere strictly to these rendering protocols:
1. **Enforce Literal Quoted Bounds**: Never describe text contextually or conceptually (do not write "paragraphs explaining the steps", "bullet points", or "labels"). You must write the exact, literal characters you want rendered enclosed strictly in double quotes (e.g., text: "99.9% Uptime").
2. **Hook Dense Data into Discrete Text Key Arrays**: Never condense a list, sequence, or paragraph block into a single text element. Break down every bullet point, subheading, paragraph block, and tagline into its own distinct, individual element entry in the elements list (with its own coordinates/description) so the character encoder processes the exact layout shapes.
3. **Strip All Banned Hedge Phrases**: Ensure there are zero alternative listings or ambiguous descriptions. Remove phrases like "or similar", "such as", "various text labels", or "e.g.". Commit to one exact word configuration.
4. **Contrast & Alignment**: Specify high-contrast backing boxes or container shapes (e.g., "enclosed in a solid black rectangular backing box"). Align the text box coordinates to negative space to prevent rendering text over faces or primary products. Enforce verbatim text strings wrapped in double quotes.
5. **Strict Word Count Limits**: To prevent generating visual gibberish, NEVER attempt to write or render a text string longer than 12 words in a single image canvas. Keep text overlays short, punchy, and strictly under 12 words.
6. **Explicit Line Breaks**: Always use explicit `\n` line breaks in the `text` field at natural word boundaries instead of relying on auto-wrap.
7. **Proportional BBox Height**: Bounding boxes for text elements MUST have a tight height proportional to the number of lines. Allocate a maximum of **150 units of height per line of text** (on the 0-1000 scale). For example, a 1-line text box should have a height (y2 - y1) of at most 150 (typically 80-120), and a 2-line text box should have a height of at most 300. NEVER allocate excessive vertical space (e.g., 400 height for 2 lines), as it forces the generator to duplicate lines or stretch text vertically to fill the empty space.

### 4. Preventing Hallucinated Layout Placeholders (Corner Gibberish)
To prevent the renderer from generating random placeholder text/gibberish in the corners or margins (e.g., "IAhghert", "Miajestarie"), the agent must:
1. **Clean Corners by Default**: By default, always append this exact sentence to the `high_level_description` or `background` description to force the corners and margins to remain completely clean: `"A clean, minimal composition with absolutely no other text, logos, branding placeholders, watermarks, or social media icons outside of the explicitly defined elements."`
2. **Branding Elements**: Only include branding text elements (such as brand names, logo text, or website URLs) in the `elements` list if the user explicitly provided or requested them. Never automatically invent or inject fake branding placeholders.
3. **Exhaustive Diagram & Infographic Layouts**: If the prompt describes a flowchart, process, or multi-step diagram (e.g., "RAG architecture", "3-step pipeline"), you MUST explicitly define every single step, connector/arrow, icon, container shape, and label as a separate element in the `elements` list with its own bounding box. Leaving parts of a diagram undefined in the JSON forces the model to hallucinate details to fill the blank space, which causes spelling typos and misaligned graphics.


