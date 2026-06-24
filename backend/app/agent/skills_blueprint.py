"""
Skills Blueprint System for LangChain/LangGraph.
Provides style enforcement, Ideogram v4 prompt optimization, ad copy validation,
A/B variations generation, visual layout coordinates, and campaign style harmonization.
"""

from typing import Dict, Any, Optional, List, Union
import re
from pydantic import BaseModel, Field

# ==========================================
# 1. MODULAR STYLE-ENFORCEMENT SKILL
# ==========================================

DEFAULT_STYLE_MAPS = {
    "Minimalist Pastel B2B": {
        "color_palette": "Soft, desaturated pastels (muted slate blue, warm sand, pale mint green, cream backgrounds). Max 3 colors.",
        "tone_of_voice": "Professional, clean, calming, and authoritative. Minimalist and clear copywriting style.",
        "visual_hierarchy": "Ample negative space, high contrast for primary information, large headlines with generous line height, subtle borders and shadows.",
        "typography": "Clean sans-serif fonts (e.g., Inter, Outfit, or Helvetica). Strict weight styling: Bold only for headings, Regular/Light for body copy.",
        "keywords": ["pastel", "soft", "light", "cream", "calm", "b2b minimalist", "flat design", "subtle"]
    },
    "High-Energy Cyberpunk": {
        "color_palette": "Neo-noir dark backgrounds with hyper-saturated neon highlights (cyan #00ffff, magenta #ff00ff, neon yellow #ffff00). High vibrant contrast.",
        "tone_of_voice": "Edgy, bold, disruptive, and conversational. Highly engaging, using jargon of futuristic tech.",
        "visual_hierarchy": "Dense, tech-grid-aligned structures, overlapping visual blocks, glitch aesthetics, high density of visual metadata.",
        "typography": "Futuristic monospace or heavy block sans-serif (e.g., Space Mono, Fira Code, Orbitron). Bold uppercase accents.",
        "keywords": ["cyberpunk", "neon", "saturated", "glitch", "futuristic tech", "dark neon", "edgy", "synthwave"]
    },
    "Premium Luxury Bold": {
        "color_palette": "Deep black, charcoal, warm ivory, and muted metallic gold/bronze accents. Elegant and highly restricted color list.",
        "tone_of_voice": "Sophisticated, exclusive, understated, yet bold and confident. Elevated editorial language.",
        "visual_hierarchy": "Centrally balanced composition, extreme contrast between massive headings and tiny, well-spaced subheadings. Cinematic layout spacing.",
        "typography": "High-contrast serif headings (e.g., Playfair Display, Bodoni) paired with geometric sans-serif subheadings (e.g., Futura, Montserrat) with wide letter spacing.",
        "keywords": ["luxury", "premium", "gold", "bronze", "exclusive", "editorial", "serif", "high-end", "sophisticated"]
    },
    "Modern SaaS Clean": {
        "color_palette": "Clean white and light gray backgrounds, dark slate gray (#1E293B) for primary elements, vibrant tech indigo (#4F46E5) or royal blue (#2563EB) for accents.",
        "tone_of_voice": "Friendly, approachable, professional, and clear. Focused on simplicity, modern productivity, and user benefits.",
        "visual_hierarchy": "Card-based grid layouts, subtle gradients, high contrast CTAs, rounded corners (8-12px), clean icon placements, and screenshots/dashboard elements.",
        "typography": "Modern geometric sans-serif (e.g., Inter, Plus Jakarta Sans, or DM Sans). Semi-bold for titles, regular weight for paragraphs.",
        "keywords": ["saas", "clean", "indigo", "modern tech", "minimalist tech", "corporate clean", "dashboard", "approachable"]
    },
    "Enterprise Security Dark": {
        "color_palette": "Deep obsidian/midnight blue backgrounds (#0F172A), cybersecurity emerald green (#10B981) or tech cyan (#06B6D4) for signal accents, with subtle slate dividers.",
        "tone_of_voice": "Highly authoritative, trustworthy, secure, and compliance-oriented. Serious, technical, and benefit-driven copywriting.",
        "visual_hierarchy": "Symmetrical structural alignment, glowing neon accents indicating data lines or firewall vectors, dark panels with glowing borders, and dashboard visual cues.",
        "typography": "Robust system sans-serif or technical hybrid (e.g., SF Pro, Segoe UI, or Roboto). Medium to heavy weights to signify security.",
        "keywords": ["security", "safe", "shield", "trust", "cybersecurity", "dark slate", "secure", "compliance", "obsidian", "firewall"]
    },
    "Data-Centric Tech Metric": {
        "color_palette": "Slate gray backdrops, bold amber/orange (#F59E0B) or cobalt blue highlights, with white text for maximum legibility.",
        "tone_of_voice": "Analytical, data-driven, precise, and informational. Focused on metrics, benchmarks, speed, performance, and developer experience.",
        "visual_hierarchy": "Heavy tabular layouts, chart overlays, clean dashboard tables, terminal windows with code line highlights, and prominent percentage/metric callouts.",
        "typography": "Hybrid pairing: high-readability sans-serif for main copy (e.g., Fira Sans) paired with code-friendly monospace (e.g., JetBrains Mono, Fira Code) for metric values and code segments.",
        "keywords": ["data", "chart", "metric", "graph", "monospace", "terminal", "code", "developer", "amber", "stats", "analytical"]
    },
    "AI DeepTech Holographic": {
        "color_palette": "Obsidian black base with luminous purple-to-blue (#8B5CF6 to #3B82F6) holographic color gradients, glowing purple meshes, and ambient light highlights.",
        "tone_of_voice": "Visionary, futuristic, intelligence-focused, and pioneering. Uses terms of orchestration, automation, and intelligence.",
        "visual_hierarchy": "Fluid, organic glassmorphic panels, glowing neural network meshes, central light sources, floating abstract nodes, and blurred backdrop filters.",
        "typography": "High-tech futuristic sans-serif (e.g., Space Grotesk, Orbitron, or Outfit). Light/thin weights for secondary text, futuristic shapes for headings.",
        "keywords": ["ai", "deeptech", "holographic", "violet", "glowing", "neural", "mesh", "glassmorphic", "futuristic", "gradient"]
    }
}

class StyleEnforcerSkill:
    """
    Looks up pre-defined style sheets and compiles style-enforcement rules
    packaged into a <style_guidelines> XML wrapper for prompt injection.
    """
    def __init__(self, custom_styles: Optional[Dict[str, Dict[str, Any]]] = None):
        self.style_repository: Dict[str, Dict[str, Any]] = dict(DEFAULT_STYLE_MAPS)
        if custom_styles:
            self.style_repository.update(custom_styles)

    def register_style(self, style_name: str, style_spec: Dict[str, Any]) -> None:
        """Register a new brand or campaign style mapping."""
        self.style_repository[style_name] = style_spec

    def detect_and_compile(self, user_input: str) -> Optional[str]:
        """
        Scans user_input for exact style name match OR keyword matches.
        Returns the compiled style block if matched, else None.
        """
        normalized_input = user_input.lower()
        
        # 1. First pass: Check for direct substring matches of the style name
        for style_name, spec in self.style_repository.items():
            if style_name.lower() in normalized_input:
                return self.compile_style_block(style_name, spec)
                
        # 2. Second pass: Word-intersection check against keywords/synonyms
        input_words = set(re.findall(r'\b\w+\b', normalized_input))
        
        best_match = None
        max_overlap = 0
        
        for style_name, spec in self.style_repository.items():
            keywords = spec.get("keywords", [])
            keywords_lower = {k.lower() for k in keywords}
            overlap = len(input_words.intersection(keywords_lower))
            if overlap > max_overlap:
                max_overlap = overlap
                best_match = (style_name, spec)
                
        if best_match and max_overlap >= 1:
            style_name, spec = best_match
            return self.compile_style_block(style_name, spec)
            
        return None

    def compile_style_block(self, style_name: str, spec: Dict[str, Any]) -> str:
        """Compiles the style specifications into a structured XML block."""
        return f"""<style_guidelines style_name="{style_name}">
IMPORTANT: You must adhere strictly to the following brand style guidelines:
- COLOR PALETTE: {spec.get('color_palette', 'No specific color restrictions.')}
- TONE OF VOICE: {spec.get('tone_of_voice', 'Standard conversational.')}
- VISUAL HIERARCHY: {spec.get('visual_hierarchy', 'Default layout.')}
- TYPOGRAPHY: {spec.get('typography', 'Standard sans-serif.')}
</style_guidelines>"""


# ==========================================
# 2. IDEOGRAM V4 TEXT ACCURACY SKILL
# ==========================================

IDEOGRAM_V4_RULES = """<text_rendering_rules>
### IDEOGRAM V4 TEXT ACCURACY & RENDERING PROTOCOLS (NON-NEGOTIABLE)
1. **Strict Quotation Wrapping (Literal Bounds)**: Any verbatim text elements MUST be enclosed in double quotes in descriptions and the text field. Never describe text conceptually (e.g. do not write "bullet points explaining the steps" or "text labels"). Commit to literal strings wrapped in double quotes.
2. **Hook Dense Data into Discrete Text Key Arrays**: Never condense a list, sequence, or paragraph block into a single text element. Break down every bullet point, tagline, subheading, or paragraph block into its own separate element entry in the elements list (each with its own coordinates and description) to avoid character collisions and textures.
3. **Strip All Banned Hedge Phrases**: Do not use ambiguous terms like "or similar", "such as", "various text labels", or "e.g.". Commit to one exact word, weight, layout, and style configuration.
4. **Explicit Spatial Cues**: Describe layout position and alignment of text elements explicitly (e.g., 'the text "Launch" centered at the top in a bold sans-serif font').
5. **Contrast**: Text must contrast sharply with its background.
6. **Word Count Limits**: NEVER attempt to write or render a text string longer than 12 words in a single image. Longer text blocks become illegible gibberish. Keep text overlays short, punchy, and strictly under 12 words.
</text_rendering_rules>"""

class IdeogramTextPromptingSkill:
    """
    Utility skill designed to enforce and rewrite text layout prompts for Ideogram v4.
    """
    @staticmethod
    def get_system_rules() -> str:
        return IDEOGRAM_V4_RULES

    @classmethod
    def optimize_raw_brief(cls, raw_brief: str) -> str:
        optimized = raw_brief
        text_patterns = [
            (r'(?i)\b(?:render text:|text reading:|text:|worded)\s+([A-Za-z0-9_-]+)\b', r'text "\1"'),
            (r'(?i)\bthe word\s+([A-Za-z0-9_-]+)\b', r'the word "\1"'),
        ]
        for pattern, replacement in text_patterns:
            optimized = re.sub(pattern, replacement, optimized)
        optimized += " Clean typography, perfect spelling, crisp letter outlines, no overlapping characters."
        return optimized.strip()


# ==========================================
# 3. BONUS MARKETING & COMPLIANCE SKILLS
# ==========================================

class ABVariationsGeneratorSkill:
    """
    Generates marketing variations (A/B testing pairs) for copy and visual assets
    based on target platforms and emotional triggers.
    """
    @staticmethod
    def compile_rules() -> str:
        return """<ab_testing_generation_rules>
### AUTOMATED A/B VARIATIONS RULES
When generating ad copy or image prompts for variations:
- Always output exactly two options: Variant A (Control) and Variant B (Challenger).
- **Variant A**: Focus on direct value propositions, product features, and clean layouts.
- **Variant B**: Focus on high-urgency hook elements, emotional solutions, and human persona action shots.
- Format all copy and visual generation briefs separated clearly with visual separators.
</ab_testing_generation_rules>"""

    @staticmethod
    def generate_variation_brief(product: str, audience: str, channel: str) -> Dict[str, Any]:
        """Utility function to create structured A/B briefs programmatically."""
        # Baseline templates for ad platforms
        is_linkedin = "linkedin" in channel.lower()
        t1 = "Value-driven, professional, focus on business outcomes." if is_linkedin else "Casual, engaging, benefit-focused."
        t2 = "Urgent, emotional, addressing core workspace frustrations." if is_linkedin else "High-energy, FOMO hook, bold CTA."

        return {
            "variant_a": {
                "headline": f"Boost your {product} results today.",
                "body": f"Get the ultimate visual solution tailored for {audience}.",
                "visual_brief": f"A clean workspace presenting {product} under bright studio lighting. Aspect ratio 1:1.",
                "theme": t1
            },
            "variant_b": {
                "headline": f"Tired of manual {product} workflows?",
                "body": f"Stop wasting hours. Discover the automated tool {audience} are switching to.",
                "visual_brief": f"An active designer looking relieved, pointing at a monitor showing {product}. Aspect ratio 4:5.",
                "theme": t2
            }
        }


class SocialComplianceCheckSkill:
    """
    Checks copywriting length constraints, emoji density, and hashtags rules.
    """
    @staticmethod
    def compile_rules() -> str:
        return """<social_compliance_rules>
### SOCIAL MEDIA COPY COMPLIANCE RULES
Ensure all social copy meets strict platform rules:
- **Twitter/X**: Keep text under 280 characters.
- **LinkedIn**: Keep text under 3000 characters; place the hook in the first 140 characters.
- **Instagram**: Keep under 30 hashtags.
- **Brand Safety**: Zero empty placeholders like '[insert link]' or '[name]'. Limit emoji density to max 3 emojis per paragraph.
- **CTA Rule**: Include exactly one clear CTA link or action message.
</social_compliance_rules>"""

    @staticmethod
    def validate_copy(text: str, platform: str) -> Dict[str, Union[bool, List[str]]]:
        """Programmatic verification of copy constraints."""
        errors = []
        text_len = len(text)
        
        if platform.lower() == "twitter" and text_len > 280:
            errors.append(f"Twitter character limit exceeded: {text_len}/280 characters.")
        elif platform.lower() == "linkedin" and text_len > 3000:
            errors.append(f"LinkedIn character limit exceeded: {text_len}/3000 characters.")
            
        # Check for placeholder formats
        placeholders = re.findall(r'\[.*?\]|<.*?>', text)
        if placeholders:
            errors.append(f"Unfilled placeholders found: {placeholders}")
            
        # Check emoji count
        emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)
        emojis = emoji_pattern.findall(text)
        if len(emojis) > 10:
            errors.append(f"High emoji count ({len(emojis)}). Keep under 10 emojis.")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }


# ==========================================
# 4. TAILORED ASSET GENERATION SKILLS
# ==========================================

class VisualLayoutStructuringSkill:
    """
    Formulates precise coordinate maps (bounding boxes) and canvas rules
    specifically for multi-element visual generations (e.g. ComfyUI, Ideogram).
    """
    @staticmethod
    def compile_rules() -> str:
        return """<visual_layout_structuring_rules>
### VISUAL COMPOSITION & LAYOUT STRUCTURING
Follow these guidelines to coordinate complex visual ad canvas elements:
1. **Normalized Coordinates**: When placing multiple subjects, characters, or text boxes, specify layout coordinates in `[y1, x1, y2, x2]` (0-1000 scale, top-left origin).
2. **Buffer Zone (Safety Margins)**: Avoid placing focal objects or text within 50 units of the border. Keep margins clean.
3. **Background Isolation**: Distinctly define the background prompt separate from physical elements. Never blend backgrounds with overlapping subject instructions.
4. **Negative Space Alignment**: When text overlays are requested, position the bounding box in negative space (e.g., in a clean upper corner or side panel) to prevent blocking the focal subject.
5. **No Overlaps**: Calculate coordinates mathematically to ensure bounding boxes of primary subjects and text overlay boxes do not intersect.
6. **Ideogram 4.0 Text Fidelity Constraints**:
   - Translate all conceptual text layouts into double-quoted literal strings.
   - Break down every bullet point, tagline, and paragraph into its own individual text element in the elements list with its own unique coordinates. Never combine them.
   - Strip all alternative listings ("or similar", "such as", "various", "e.g."). Pick one configuration.
</visual_layout_structuring_rules>"""

    @staticmethod
    def calculate_bounds(element_type: str, align: str = "center") -> List[int]:
        """Helper to output correct coordinate list [y1, x1, y2, x2] for standard layouts."""
        if element_type == "text_header":
            return [80, 100, 220, 900] # centered top strip
        elif element_type == "footer_cta":
            return [800, 200, 920, 800] # centered bottom strip
        elif element_type == "left_focal_subject":
            return [150, 50, 850, 480] # left side vertical placement
        elif element_type == "right_focal_subject":
            return [150, 520, 850, 950] # right side vertical placement
        return [100, 100, 900, 900] # full center area


class CampaignStyleHarmonizerSkill:
    """
    Harmonizes visual styles, color lists, rendering styles, and composition patterns
    across multi-image ad campaigns using anchor rules.
    """
    @staticmethod
    def compile_rules() -> str:
        return """<campaign_style_harmonizer_rules>
### CAMPAIGN STYLE HARMONIZATION RULES
To ensure visual consistency across all generated images in a campaign:
1. **Lock the Anchor Style**: The first image's visual details (render style, lighting, texture, and color palette) must be saved as the campaign's anchor style.
2. **Reuse Key Prompts**: Carry forward the specific style modifiers (e.g., "warm cinematic lighting, shot on 35mm film, low saturation, clean minimalism") to all subsequent images.
3. **Incorporate Reference Images**: Always request `image_reference_and_text_to_image` or ControlNet mapping to pass the previous image's path as a reference for layout, style, or lighting matching.
4. **Color Integrity**: Maintain exact hex codes or specific color palettes (e.g., warm ivory and copper gold) in every canvas description.
</campaign_style_harmonizer_rules>"""

    @staticmethod
    def format_style_anchors(style_description: str) -> str:
        """Helper to extract visual modifiers from an anchor description to reuse in sub-prompts."""
        # Simple extraction heuristics for photographic/render parameters
        quality_keys = ["cinematic", "lighting", "shot on", "film", "illustration", "vector", "3d", "render", "palette"]
        found_modifiers = []
        for word in style_description.split(","):
            word_clean = word.strip()
            if any(k in word_clean.lower() for k in quality_keys):
                found_modifiers.append(word_clean)
        return ", ".join(found_modifiers) if found_modifiers else style_description


# ==========================================
# 5. DYNAMIC SKILL COMPILER / INTEGRATION
# ==========================================

class MarketingPromptCompiler:
    """
    Compiles state inputs, runs active skills, and dynamically modifies
    system instructions or visual prompts before dispatching to the LLM.
    """
    def __init__(self, custom_styles: Optional[Dict[str, Dict[str, str]]] = None):
        self.style_enforcer = StyleEnforcerSkill(custom_styles)
        self.text_enforcer = IdeogramTextPromptingSkill()
        self.ab_generator = ABVariationsGeneratorSkill()
        self.compliance_checker = SocialComplianceCheckSkill()
        self.layout_structurer = VisualLayoutStructuringSkill()
        self.style_harmonizer = CampaignStyleHarmonizerSkill()

    def compile_system_prompt(self, base_system_prompt: str, user_input: str) -> str:
        """
        Appends style guidelines, platform compliance, layout constraints,
        and Ideogram text accuracy rules based on keyword triggers.
        """
        compiled = base_system_prompt
        
        # 1. Style sheet enforcement
        style_block = self.style_enforcer.detect_and_compile(user_input)
        if style_block:
            compiled += f"\n\n{style_block}"
            
        # 2. Text rendering rules
        compiled += f"\n\n{self.text_enforcer.get_system_rules()}"
        
        # 3. Trigger variations rules if A/B is mentioned
        if any(w in user_input.lower() for w in ["a/b", "variations", "variants", "options"]):
            compiled += f"\n\n{self.ab_generator.compile_rules()}"
            
        # 4. Trigger social compliance rules if platforms are mentioned
        if any(w in user_input.lower() for w in ["twitter", "linkedin", "instagram", "compliance", "post", "social"]):
            compiled += f"\n\n{self.compliance_checker.compile_rules()}"
            
        # 5. Trigger layout structuring if visual layout elements are requested
        if any(w in user_input.lower() for w in ["layout", "coordinate", "bounding box", "bbox", "composition", "position"]):
            compiled += f"\n\n{self.layout_structurer.compile_rules()}"
            
        # 6. Trigger style harmonizer if multiple images/consistency is requested
        if any(w in user_input.lower() for w in ["consistent", "harmonize", "same style", "series", "campaign"]):
            compiled += f"\n\n{self.style_harmonizer.compile_rules()}"
        
        return compiled

    def compile_user_prompt(self, raw_user_prompt: str) -> str:
        """
        Pre-processes user layout descriptions to ensure high Ideogram fidelity.
        """
        return self.text_enforcer.optimize_raw_brief(raw_user_prompt)
