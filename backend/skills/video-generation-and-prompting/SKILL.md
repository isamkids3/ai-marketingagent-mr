---
name: video-generation-and-prompting
description: Guidelines and best practices for creating cinematic videos using the LTX-Video tools (text_video and image_text_video). Trigger this skill when the user wants to generate a video or animate an image.
---

# Video Generation and prompting Skill

This skill governs the execution and prompting strategy for the LTX-Video model. It is connected directly to two primary tools:
1. **`text_video`**: For generating a new video from scratch based on a detailed text prompt.
2. **`image_text_video`**: For animating or guiding a video generation using an initial/reference image (e.g. animating a static character or scene).

---

## ⏱️ Video Duration Constraints
* The agent has the flexibility to choose the duration of the generated video (using the `duration` parameter in seconds).
* **CRITICAL RULE**: The duration **MUST NEVER exceed 30 seconds** (the valid range is `1` to `30` seconds). Always default to a reasonable length (e.g. `5`, `10`, or `15` seconds) depending on the complexity of the action.

---

## 🎨 Prompting Principles for LTX-Video

LTX models respond best to highly detailed, descriptive prompts written like a **cinematic shot description for a director**.

### 1. Core Principles
* **Be Specific and Descriptive**: Avoid simple prompts like *"a person walking"*. Instead use: *"a young woman in a red coat walking briskly through a rain-soaked Tokyo street at night, neon reflections on wet pavement, handheld camera following from behind."*
* **Describe the Full Scene**: Always detail the **Subject**, their **Action**, the **Environment/Atmosphere**, the **Lighting**, the **Camera Behavior**, and the **Audio**.
* **Use Cinematic Language**: Integrate terms like *"macro lens"*, *"tracking shot"*, *"shallow depth of field"*, *"low angle"*, or *"golden hour"* to guide the camera work and visual style.
* **Describe Audio**: LTX-2.3 generates synchronized sound. Always include audio descriptions at the end of the prompt (e.g. *"the sound of rain on pavement"*, *"a deep resonant narrator voice speaking in a quiet room"*, *"faint room tone and mechanical clicks"*).
* **Write as a Single Paragraph**: Always structure the final prompt as a single, continuous, flowing paragraph in the present tense.

---

## 🚀 Prompting Guidelines by Tool

### A. Text-to-Video (`text_video`)
Since the model is generating the video from scratch:
* Start with a strong visual establishing shot.
* Exhaustively detail the subject, action, environment, lighting, camera movement, and audio.
* Longer, descriptive prompts perform significantly better to fill the duration of the clip.

### B. Image-to-Video (`image_text_video`)
Since the visual starting point is already defined by the `init_image` reference:
* **DO NOT** describe static elements already visible in the initial image.
* **DO** focus the prompt entirely on the **motion, action, transitions, and audio**.
* Describe the transition from stillness to motion: how the subject moves, how the camera follows, and what sounds emerge.

---

## 📽️ Key Elements to Include in Every Prompt

1. **Establish the Shot**: Use cinematic scale terms (e.g., *"wide establishing shot"*, *"intimate close-up"*).
2. **Set the Scene**: Describe lighting conditions (e.g. *"cool diffused daylight"*, *"flickering lamps"*), textures, colors, and atmosphere. AVOID the word *"warm"* to grade the shot (it triggers low-quality AI color grading); describe warm light sources pool-by-pool instead (e.g. *"amber light pool from the candle"*).
3. **Describe the Action**: Present the action in a chronological, natural sequence.
4. **Define the Character(s)**: Mention age, hair, attire, and physical emotional cues (e.g., *"he pauses, his eyes widen in surprise"*, instead of abstract labels like *"confused"*).
5. **Identify Camera Movement**: Specify the camera motion (e.g. *"slow dolly in"*, *"handheld tracking"*).
6. **Describe the Audio**: Detail ambient sounds, speech, or music. Put spoken dialogue in quotation marks (e.g. *Reporter (live): "black gold has been found!"*).

---

## 🚫 What to Avoid
* **Internal Emotional States**: Do not use labels like *"sad"* or *"confused"*. Describe visual cues instead (e.g. *"shoulders slumped, looking down"*).
* **Text and Logos**: Readable text is not reliable in LTX videos. Avoid prompting for legible text overlays.
* **Complex Physics**: Avoid chaotic motion or complex structural transformations which introduce visual artifacts.
* **Overloaded Scenes**: Keep the focus on a single primary subject or clear interaction. Too many characters reduce clarity.

---

## 📝 Sample Prompts

### Example 1 (Text-to-Video)
> EXT. SMALL TOWN STREET – MORNING – LIVE NEWS BROADCAST. The shot opens on a news reporter standing in front of a row of cordoned-off cars, yellow caution tape fluttering behind him. The light is warm, early sun reflecting off the camera lens. The faint hum of chatter and distant drilling fills the air. The reporter, composed but visibly excited, looks directly into the camera, microphone in hand. Reporter (live): "Thank you, Sylvia. And yes — this is a sentence I never thought I'd say on live television — but this morning, here in the quiet town of New Castle, Vermont… black gold has been found!" He gestures slightly toward the field behind him. Reporter (grinning): "If my cameraman can pan over, you'll see what all the excitement's about." The camera pans right, slowly revealing a construction site surrounded by workers in hard hats. A beat of silence — then, with a sudden roar, a geyser of oil erupts from the ground, blasting upward in a violent plume. Workers cheer and scramble, the black stream glistening in the morning light. The camera shakes slightly, trying to stay focused through the chaos. Reporter (off-screen, shouting over the noise): "There it is, folks — the moment New Castle will never forget!" The camera catches the sunlight gleaming off the oil mist before pulling back, revealing the entire scene — the small-town skyline silhouetted against the wild fountain of oil.

### Example 2 (Image-to-Video / Cat Animation)
> The camera holds static for a split second before the cat from the image suddenly crouches low, its eyes locking onto something just off-camera. Its hindquarters twitch rhythmically in anticipation. With a sudden burst of fluid energy, the cat springs forward directly toward the lens, paws outstretched. The ambient audio captures a soft, low purr that abruptly shifts to the rustle of carpet fibers and a sharp, playful feline chirp as it leaps.
