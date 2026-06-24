---
name: social-compliance-check
description: Validate copywriting content for social media constraints, character counts, emoji density, hashtag limits, and brand safety guidelines. Use this skill when formatting or checking captions, headlines, or ad copy.
---

# social-compliance-check

## Overview
Ensures all copy outputs comply with specific social media platform rules, brand constraints, and visual presentation standards.

## Instructions

### 1. Platform Boundary Checks
Ensure that all drafted copy satisfies these strict character and word limit boundaries:
- **Twitter/X**: Max 280 characters. Keep it under 250 characters for visual safety when attaching media.
- **LinkedIn**: Max 3,000 characters. For engagement, place the hook in the first 140 characters before the "...see more" cutoff.
- **Instagram**: Max 2,200 characters. Keep under 30 hashtags. Recommended 5-10 highly relevant hashtags.

### 2. Brand Compliance Heuristics
- **Emoji Density**: Max 3 emojis per paragraph. No consecutive duplicate emojis. Emojis must fit the industry context (e.g., avoid cartoonish symbols for professional enterprise B2B content).
- **Placeholder Audit**: Confirm that no formatting markers or placeholders (e.g., `[Insert Name]`, `[Link Here]`, `<Date>`) remain in the final output.
- **Call-to-Action (CTA)**: Every social post must contain exactly one clear, actionable CTA (e.g., "Click the link in bio", "Comment below").

### 3. Formatting
If copy violates any rules, restructure and condense it automatically. Log a summary of modifications at the top of the output to inform the user of compliance adjustments.
