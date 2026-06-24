---
name: ab-variations-generator
description: Generate optimized marketing variants (A/B testing pairs) for copywriting and visual asset prompts across multiple channels. Use this skill when the user requests ad variations, target audience tests, or multiple campaign concepts.
---

# ab-variations-generator

## Overview
This skill guides the agent in generating high-performing, channel-specific copy and design variations to be used in A/B testing pipelines.

## Instructions

### 1. Identify Context and Target Audience
- Analyze the user brief to extract the target persona, campaign objective, and specific value propositions.
- Determine target channels (e.g., LinkedIn Ads, Facebook Ads, Google Search, email campaigns).

### 2. Generate Variant Pairs
Generate at least two distinct variations (Variant A and Variant B):
- **Variant A (Control - Benefit/Value-Driven)**: Focuses directly on utility, features, or primary values. Keep the layout clean and message straightforward.
- **Variant B (Challenger - Pain-Point/Emotion-Driven)**: Focuses on resolving specific user frustrations, FOMO (fear of missing out), or high-energy curiosity hooks.

### 3. Visual Layout Variations
For each copywriting variant, suggest matching visual prompts:
- Variant A Visual: Centered product/service visualization under bright, clean professional lighting.
- Variant B Visual: Contextual action shot showing the user persona experiencing/resolving the pain-point.

### 4. Output Formatting
Write the variant specs into a markdown file in the workspace directory:
`write_file_to_sandbox(filename="ab_variants_brief.md", content="...")`
Include copywriting headlines, body text, CTA buttons, and detailed description prompts for ComfyUI/Ideogram generation.
