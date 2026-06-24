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
- **Safety Margins**: Maintain a buffer zone. Keep critical focal points and text away from borders (boundaries < 50 or > 950) to avoid cropping.
- **Background Separation**: Explicitly isolate the background (e.g., solid backdrop, transparent canvas, out-of-focus bokeh) from elements.
- **Focal Points**: Ensure primary and secondary visual elements do not overlap. Calculate offsets carefully (e.g., if Subject A occupies `[100, 100, 900, 500]`, position Subject B or text elements beyond `x = 550` to avoid clipping).

### 3. Text Overlay Alignment & Ideogram 4.0 Fidelity (CRITICAL)
When the visual design calls for text overlays, you must adhere strictly to these rendering protocols:
1. **Enforce Literal Quoted Bounds**: Never describe text contextually or conceptually (do not write "paragraphs explaining the steps", "bullet points", or "labels"). You must write the exact, literal characters you want rendered enclosed strictly in double quotes (e.g., text: "99.9% Uptime").
2. **Hook Dense Data into Discrete Text Key Arrays**: Never condense a list, sequence, or paragraph block into a single text element. Break down every bullet point, subheading, paragraph block, and tagline into its own distinct, individual element entry in the elements list (with its own coordinates/description) so the character encoder processes the exact layout shapes.
3. **Strip All Banned Hedge Phrases**: Ensure there are zero alternative listings or ambiguous descriptions. Remove phrases like "or similar", "such as", "various text labels", or "e.g.". Commit to one exact word configuration.
4. **Contrast & Alignment**: Specify high-contrast backing boxes or container shapes (e.g., "enclosed in a solid black rectangular backing box"). Align the text box coordinates to negative space to prevent rendering text over faces or primary products. Enforce verbatim text strings wrapped in double quotes.
5. **Strict Word Count Limits**: To prevent generating visual gibberish, NEVER attempt to write or render a text string longer than 12 words in a single image canvas. Keep text overlays short, punchy, and strictly under 12 words.

