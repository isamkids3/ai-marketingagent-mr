---
name: multi-reference-editing
description: Use when combining elements, styles, subjects, or backgrounds from two reference images into a single generated output.
---

# Multi-Reference Editing (2-Image Focus)

## Overview
Multi-reference editing allows the generation model (like Flux) to combine visual details, subjects, styles, and environments from two distinct input images into a single, cohesive output image.

When the user uploads two reference images, the backend automatically registers and maps them inside the prompt context as:
* **Reference Image 1**: `/sandbox/{session_id}/image1.png` (mapped to tool parameter `image_1` / labeled as `Image 1`)
* **Reference Image 2**: `/sandbox/{session_id}/image2.png` (mapped to tool parameter `image_2` / labeled as `Image 2`)

To avoid confusing the model and to ensure correct pixel composition, the agent must write prompts that explicitly identify the source and role of each image.

---

## Instructions

### 1. Explicit Reference Prompting (Image 1 and Image 2)
To direct the generation model's attention:
* Use the exact literal string tags **"image 1"** and **"image 2"** in the positive text prompt.
* Describe precisely what characteristics the model should pull from each reference image.
* Assign distinct roles:
  * **Image 1** usually represents the primary subject, foreground object, character, or base composition.
  * **Image 2** usually represents the background, environment, style source, texture/pattern source, or secondary object.

### 2. Common Composing Patterns (Two References)

#### Pattern A: Subject Placement (Compositing)
* **Goal**: Take a subject (animal, product, person) from Image 1 and place it in the environment/background of Image 2.
* **Prompt Format**:
  > *"Place the [subject] from image 1 naturally inside the [environment] from image 2. Ensure the lighting, shadows, and perspective match the room in image 2."*
* **Example**:
  > *"Take the toy alpaca from image 1 and place it sitting upright on the shelf in the bedroom from image 2, matching the soft warm lighting."*

#### Pattern B: Style & Material Transfer
* **Goal**: Keep the subject/pose from Image 1 but render it in the artistic style, texture, or color palette of Image 2.
* **Prompt Format**:
  > *"A [subject] matching the pose and content of image 1, rendered completely in the style of image 2 (including its colors, textures, and brushstrokes)."*
* **Example**:
  > *"A majestic portrait of the cat from image 1, rendered in the impasto oil painting style of image 2, with thick visible paint layers and a gold color palette."*

#### Pattern C: Pattern & Texture Application
* **Goal**: Apply the surface pattern, logo, or material texture of Image 2 onto the surface of an object in Image 1.
* **Prompt Format**:
  > *"Apply the pattern, material texture, and colors from image 2 onto the surface of the [object] in image 1, following its shape and shading."*
* **Example**:
  > *"Apply the blue floral pattern from image 2 onto the white ceramic plate in image 1, aligning it naturally with the light source."*

#### Pattern D: Double Subject Interaction
* **Goal**: Combine two separate elements (e.g., a person and a prop/animal) into a single scene.
* **Prompt Format**:
  > *"A high-quality photograph showing the [subject 1] from image 1 interacting with the [subject 2] from image 2."*
* **Example**:
  > *"A photograph of the woman in image 1 sitting next to the dog from image 2 in a lush park, looking happy."*

---

## Writing Effective Prompts

* **Be Verbatim and Specific**: Do not say "combine the two images". Instead say, "Place the chair from image 1 inside the living room from image 2."
* **Detail the Blending**: Instruct the model on how to blend lighting, scale, and depth (e.g., "matching the natural daylight of image 2").
* **Avoid Generalizations**: Do not write "make it look nice". State the exact details of the final composited scene.
