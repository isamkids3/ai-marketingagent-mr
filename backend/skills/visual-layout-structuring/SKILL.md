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
- **Token-Budget Optimization (BBox & Element Limits)**: To prevent JSON truncation and LLM output token limit errors, you MUST:
  - **Limit Elements Count**: Limit the visual layout to a maximum of 6 elements per image (especially for infographics or split-screens).
  - **Concise Descriptions**: Keep each element's description concise and strictly under 40 words. Do not use overly descriptive micro-prose. This forces compact JSON output and avoids truncation failures.
- **Bounding Boxes for ALL Elements (CRITICAL)**: Every entry in the `elements` list—whether it is a text label (`type: "text"`) or an object/icon/graphic/container (`type: "obj"`)—MUST have defined `bbox` coordinates. Bounding boxes are not just for text; bounding boxes for physical icons, shapes, and characters are essential to anchor them in 2D space, prevent them from overlapping, and stop the model from duplicating them.
- **Isolate Text Coordinates & Coordinate Segmentation**: Bounding boxes for text overlays (`type: "text"`) must be separated from backdrop objects and foreground objects (`type: "obj"`, such as buttons, badges, products, characters, or containers) so they do not overlap. Keeping their bounding box definitions physically separate prevents overlapping pixel conflicts entirely. If text is meant to be placed 'on' or 'inside' a shape, do NOT overlap their bounding boxes; instead, allocate a separate, smaller bounding box for the text that sits entirely inside the container box with clean margins. Text and object bounding boxes must never intersect, or they will compete/fight for the same pixels, causing spelling glitches and rendering artifacts.
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
7. **Proportional BBox Height (Dynamic Height Calculation)**: Bounding boxes for text elements MUST have a tight height calculated dynamically based on line count. For a 1:1 canvas, allocate **70 to 80 units of height per line of text** (up to a maximum of 100 units). For example, a 1-line text box should have a height of 70 to 100, a 2-line text box should have a height of 140 to 200, and a 3-line text box should strictly have a maximum vertical span of 210 to 240 units (up to 300 maximum). NEVER allocate excessive height (e.g., 400 height for 2 or 3 lines), as this forces the generator to duplicate lines or invent random text (like "Ever croy") to fill the empty space.

### 4. Preventing Hallucinated Layout Placeholders (Corner Gibberish)
To prevent the renderer from generating random placeholder text/gibberish in the corners or margins (e.g., "IAhghert", "Placydar", "##17"), the agent must:
1. **Avoid Layout & Structural Buzzwords**: Generic layout and structural terms—such as "advertisement", "social media ad", "ad banner", "infographic", "flowchart", "process diagram", "comparison chart", "presentation slide", or "dashboard"—trigger strong pre-trained template priors. The model will automatically inject placeholder structures (fake logos, website URLs, arrows, legends, and keys) to satisfy the expected visual format.
   - **Rule**: Do NOT use these structural buzzwords unless the user explicitly requested that specific format (e.g., a flowchart or infographic).
   - **If a structural format IS requested**: You MUST follow the **Exhaustive Diagram & Infographic Layouts** rule below and explicitly define a bounding box in the `elements` list for every single item, connector, icon, and label on the canvas. Any undefined area will be filled with random geometric shapes and gibberish text.
   - **If a structural format is NOT requested**: Use clean, descriptive media types (e.g., "cinematic lifestyle photograph", "clean studio product shot", "minimalist flat graphic design", or "studio portrait") to keep the canvas free of layout placeholders.
2. **Use Positive Negation (Clean Corners & Margins)**: To keep margins and corners completely free of hallucinated labels, icons, watermarks, or URLs, do NOT use negative words (e.g., do not say "no logos, no watermarks", as the model will pay attention to these nouns and generate them). Instead, always append one of these positive descriptions to the background or high-level description:
   - For photographs/scenic backgrounds: `"The background is a smooth, continuous image extending fully to all four edges of the canvas, with the corners and margins of the frame remaining completely plain, bare, and empty."`
   - For graphical/infographic overlays: `"A clean, minimalist layout with a vast amount of empty, quiet negative space surrounding the central elements."`
3. **Branding Elements**: Only include branding text elements (such as brand names, logo text, or website URLs) in the `elements` list if the user explicitly provided or requested them. Never automatically invent or inject fake branding placeholders.
4. **Exhaustive Diagram & Infographic Layouts**: If the prompt describes a flowchart, process, or multi-step diagram (e.g., "RAG architecture", "3-step pipeline"), you MUST explicitly define every single step, connector/arrow, icon, container shape, and label as a separate element in the `elements` list with its own bounding box. Leaving parts of a diagram undefined in the JSON forces the model to hallucinate details to fill the blank space, which causes spelling typos and misaligned graphics.

### 5. Loop Prevention (Single-Shot Rule)
- **No Visual Feedback Loops**: You CANNOT see the generated images (you only receive a file path). Do NOT generate or regenerate images repeatedly in a loop to try to visually verify, tweak, or adjust the layout. Plan your coordinates mathematically, run the generation tool once, immediately return the best image path to the user, and wait for their feedback.


