---
name: campaign-style-harmonizer
description: Harmonize visual styles, color palettes, lighting mood, character features, and textures across multiple generated assets in a campaign. Use when the user requests multi-image asset generation, consistent brand style transfer, or sequential visual storytelling.
---

# campaign-style-harmonizer

## Overview
Ensures visual cohesion across all generated images in a campaign by using consistent prompt templates, color systems, and reference images.

## Instructions

### 1. Establish Style Anchor
- When generating a series of assets, select or generate the first image ("Anchor Asset") and lock its stylistic parameters.
- Record the color palette, lighting style (e.g., volumetric lighting, soft studio, high contrast hard shadow), texture/render style (e.g., photorealistic, 3D claymation, flat vector illustration), and character details (if applicable).

### 2. Multi-Asset Style Transfer Protocols
- **Reference Image Usage**: When generating subsequent campaign assets, ALWAYS use the Anchor Asset as a reference image in the `image_reference_and_text_to_image` tool to guide composition, layout, and lighting.
- **Consistent Visual Prompt Tokens**: Carry forward specific style modifier keywords from the anchor prompt (e.g., "shot on 35mm film, warm cinematic lighting, muted earth tones, minimalist composition").
- **Asset ID Mapping**: Track and reference asset IDs from previous generation steps (`[Asset ID: <id>]`) in your execution plans to reuse seeds or settings where appropriate.

### 3. Campaign Color Verification
Ensure color codes and palettes match brand expectations across all generated canvases. Verify that any overlays, background canvases, and primary products share matching color hex codes or descriptions.
