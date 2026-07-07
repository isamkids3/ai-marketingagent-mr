---
name: multi-reference-editing
description: Use when combining elements, styles, subjects, or backgrounds from two or three reference images into a single generated output.
---

# Multi-Reference Editing (2 or 3 Image Focus)

## Overview
Multi-reference editing allows the generation model (like Flux) to combine visual details, subjects, styles, and environments from two or three distinct input images into a single, cohesive output image.

When the user uploads reference images, the backend automatically registers and maps them inside the prompt context as:
* **Reference Image 1**: `/sandbox/{session_id}/image1.png` (mapped to tool parameter `image_1` / labeled as `Image 1`)
* **Reference Image 2**: `/sandbox/{session_id}/image2.png` (mapped to tool parameter `image_2` / labeled as `Image 2`)
* **Reference Image 3**: `/sandbox/{session_id}/image3.png` (mapped to tool parameter `image_3` / labeled as `Image 3`)

To avoid confusing the model and to ensure correct pixel composition, the agent must write prompts that explicitly identify the source and role of each image.

---

## Instructions

### 1. Explicit Reference Prompting (Image 1, Image 2, and Image 3)
To direct the generation model's attention:
* Use the exact literal string tags **"image 1"**, **"image 2"**, and **"image 3"** in the positive text prompt.
* Describe precisely what characteristics the model should pull from each reference image.
* Assign distinct roles:
  * **Image 1** usually represents the primary subject, character, foreground object, or base composition.
  * **Image 2** usually represents the secondary subject, accessory/prop, style source, or texture source.
  * **Image 3** usually represents the background, environment, scene layout, or lighting source.

### 2. Common Composing Patterns (Two References)

#### Pattern A: Subject Placement (Compositing)
* **Goal**: Take a subject from Image 1 and place it in the environment/background of Image 2.
* **Prompt Format**:
  > *"Place the [subject] from image 1 naturally inside the [environment] from image 2. Ensure the lighting, shadows, and perspective match the room in image 2."*
* **Example**:
  > *"Take the toy alpaca from image 1 and place it sitting upright on the shelf in the bedroom from image 2, matching the soft warm lighting."*

#### Pattern B: Style & Material Transfer
* **Goal**: Keep the subject/pose from Image 1 but render it in the artistic style of Image 2.
* **Prompt Format**:
  > *"A [subject] matching the pose and content of image 1, rendered completely in the style of image 2 (including its colors, textures, and brushstrokes)."*

#### Pattern C: Pattern & Texture Application
* **Goal**: Apply the surface pattern, logo, or material texture of Image 2 onto the surface of an object in Image 1.
* **Prompt Format**:
  > *"Apply the pattern, material texture, and colors from image 2 onto the surface of the [object] in image 1, following its shape and shading."*

#### Pattern D: Double Subject Interaction
* **Goal**: Combine two separate elements into a single scene.
* **Prompt Format**:
  > *"A high-quality photograph showing the [subject 1] from image 1 interacting with the [subject 2] from image 2."*

---

### 3. Common Composing Patterns (Three References)

#### Pattern E: Triple Subject & Scene Composition
* **Goal**: Take subject 1 from Image 1, secondary subject/accessory from Image 2, and place them together in the environment/scene of Image 3.
* **Prompt Format**:
  > *"Place the [subject 1] from image 1 and the [subject 2/prop] from image 2 naturally inside the [environment] from image 3. Ensure they blend seamlessly under the lighting conditions of image 3."*
* **Example**:
  > *"Place the man in a casual pose from image 1 holding the red cup from image 2, sitting together on the park swing from image 3, matching the bright natural daylight."*

---

## Writing Effective Prompts

* **Exactly One Generation Call**: Due to the intensive processing required for multi-image reference models, you must trigger the generation tool (`image_image_2ref` or `image_image_3ref`) EXACTLY ONCE per user request. Do not run variations, A/B options, or iterative corrections in a loop.
* **Be Verbatim and Specific**: Do not say "combine the three images". Instead say, "Place the person from image 1 holding the product from image 2 inside the office lobby from image 3."
* **Detail the Blending**: Instruct the model on how to blend lighting, scale, and depth (e.g., "matching the natural daylight and shadows of image 3").
* **Avoid Generalizations**: Do not write "make it look nice". State the exact details of the final composited scene.
