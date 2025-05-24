import json
import logging
import random
import re

import google.generativeai as genai
import ollama

from .db_queries import get_setting
from .etc import temporary_env_var
from .llm_utils import (
    LLM_SURPRISE_ME_END_PROMPT_MANY,
    LLM_SURPRISE_ME_END_PROMPT_ONE,
    LLM_SURPRISE_ME_INITIAL_PROMPT_MANY,
    LLM_SURPRISE_ME_INITIAL_PROMPT_ONE,
)

LOGGER = logging.getLogger("visionatrix")
GENRES = [
    "fantasy",
    "science fiction",
    "horror",
    "romance",
    "mystery",
    "historical",
    "adventure",
    "thriller",
    "comedy",
    "drama",
    "western",
    "cyberpunk",
    "steampunk",
    "gothic",
    "noir",
    "surrealism",
    "dystopian",
    "utopian",
    "mythology",
    "fairy tale",
    "superhero",
    "post-apocalyptic",
    "dark fantasy",
    "slice of life",
    "folklore",
]

MOODS = [
    "serene",
    "chaotic",
    "melancholic",
    "joyful",
    "tense",
    "mysterious",
    "ominous",
    "whimsical",
    "nostalgic",
    "hopeful",
    "despairing",
    "energetic",
    "calm",
    "anxious",
    "playful",
    "somber",
    "dreamy",
    "epic",
    "intimate",
    "foreboding",
    "poignant",
    "lighthearted",
    "ambiguous",
    "bittersweet",
    "triumphant",
]

SETTINGS = [
    "forest",
    "dark forest",
    "jungle",
    "desert",
    "oasis",
    "city",
    "ocean",
    "space",
    "underwater",
    "mountain",
    "countryside",
    "arctic",
    "tundra",
    "frozen lake",
    "crystal cave",
    "volcanic",
    "cave",
    "island",
    "swamp",
    "marsh",
    "savanna",
    "grassland",
    "ruins",
    "ancient ruins",
    "castle",
    "village",
    "metropolis",
    "wasteland",
    "underworld",
    "sky realm",
    "underground tunnels",
    "alien planet",
    "laboratory",
    "arena",
    "monastery",
    "train station",
    "airport",
]

STYLES = [
    "abstract",
    "realistic",
    "impressionist",
    "surreal",
    "cinematic",
    "vintage",
    "minimalist",
    "expressionist",
    "pop art",
    "art nouveau",
    "baroque",
    "rococo",
    "cubist",
    "futurist",
    "romantic",
    "gothic",
    "renaissance",
    "modernist",
    "postmodern",
    "photorealistic",
    "watercolor style",
    "neon glow aesthetic",
    "pixelated retro",
    "line art",
    "comic book style",
]

TIME_PERIODS = [
    "ancient",
    "medieval",
    "renaissance",
    "industrial",
    "victorian",
    "modern",
    "futuristic",
    "prehistoric",
    "classical",
    "contemporary",
    "retro",
    "post-apocalyptic",
    "timeless",
    "mythical",
    "near future",
    "distant past",
    "distant future",
    "alternate history",
    "steampunk era",
    "cyberpunk era",
    "1920s prohibition",
    "1980s neon",
    "1960s flower power",
    "silver age",
    "iron age",
]

COLOR_PALETTES = [
    "monochromatic",
    "vibrant",
    "pastel",
    "dark tones",
    "bright hues",
    "earth tones",
    "neon",
    "sepia",
    "grayscale",
    "warm colors",
    "cool colors",
    "metallic",
    "jewel tones",
    "muted",
    "high contrast",
    "low contrast",
    "analogous colors",
    "complementary colors",
    "triadic colors",
    "black and white",
    "pastel neon mix",
    "rustic browns",
    "sunset gradient",
    "cosmic purples",
    "lush greens",
]

SUBJECTS = [
    "person",
    "man",
    "woman",
    "child",
    "knight",
    "bard",
    "dancer",
    "emperor",
    "queen",
    "wizard",
    "astronaut",
    "detective",
    "pirate",
    "animal",
    "tiger",
    "eagle",
    "shark",
    "dragon",
    "beast",
    "ogre",
    "troll",
    "goblin",
    "orc",
    "unicorn",
    "robot",
    "alien",
    "monster",
    "spaceship",
    "car",
    "frog",
    "ship",
    "cityscape",
    "seascape",
    "sword",
    "clock",
    "phoenix",
    "samurai",
    "golem",
    "chimera",
    "mermaid",
    "android",
    "demon",
    "angel",
    "zombie",
    "drone",
]

ACTIONS = [
    "standing",
    "sitting",
    "running",
    "flying",
    "swimming",
    "fighting",
    "casting a spell",
    "exploring",
    "creating art",
    "playing an instrument",
    "reading",
    "writing",
    "dancing",
    "singing",
    "sleeping",
    "observing stars",
    "battling a monster",
    "piloting a vehicle",
    "discovering treasure",
    "gazing into the distance",
    "meditating",
    "transforming",
    "celebrating",
    "escaping danger",
    "performing a ritual",
    "eating",
    "praying",
]

WEATHERS = [
    "sunny",
    "rainy",
    "snowy",
    "windy",
    "stormy",
    "cloudy",
    "foggy",
    "misty",
    "hazy",
    "thunderstorm",
    "tornado",
    "aurora",
    "eclipse",
    "rainbow",
    "clear skies",
    "overcast",
    "heatwave",
    "hurricane",
    "blizzard",
    "drizzle",
]

LIGHTINGS = [
    "daylight",
    "moonlight",
    "artificial light",
    "candlelight",
    "firelight",
    "neon light",
    "twilight",
    "dawn",
    "dusk",
    "golden hour",
    "shadowy",
    "spotlight",
    "backlit",
    "silhouette",
    "glowing",
    "radiant",
    "dim",
    "bright",
    "colorful stage lighting",
    "pulse-strobing lights",
]

ART_MEDIUMS = [
    "oil painting",
    "watercolor",
    "digital art",
    "pencil sketch",
    "charcoal",
    "pastel",
    "acrylic",
    "ink",
    "collage",
    "sculpture",
    "photography",
    "mosaic",
    "fresco",
    "graffiti",
    "pixel art",
    "vector art",
    "mixed media",
    "glass art",
    "textile art",
    "printmaking",
]

PERSPECTIVES = [
    "first-person view",
    "birds-eye view",
    "close-up",
    "wide shot",
    "over-the-shoulder view",
    "profile view",
    "frontal view",
    "three-quarter view",
    "isometric",
    "panoramic",
    "macro view",
    "micro view",
    "tilted frame",
    "symmetrical frame",
    "asymmetrical frame",
    "fish-eye lens",
    "long shot",
    "medium shot",
    "dutch angle",
]

EMOTION = [
    "smiling",
    "laughing",
    "joyful expression",
    "angry expression",
    "rage",
    "crying",
    "tearful",
    "sad expression",
    "surprised",
    "shocked",
    "thoughtful",
    "curious",
    "confident",
    "scared",
    "terrified",
    "peaceful look",
    "embarrassed",
]

CATEGORIES = {
    "genres": GENRES,
    "moods": MOODS,
    "settings": SETTINGS,
    "styles": STYLES,
    "time_periods": TIME_PERIODS,
    "color_palettes": COLOR_PALETTES,
    "subjects": SUBJECTS,
    "actions": ACTIONS,
    "weathers": WEATHERS,
    "lightings": LIGHTINGS,
    "art_mediums": ART_MEDIUMS,
    "perspectives": PERSPECTIVES,
    "emotion": EMOTION,
}


def pick_random_keywords(num_core_min=3, num_core_max=6, num_extra_min=2, num_extra_max=5):
    core_categories_list = ["genres", "moods", "settings", "styles", "time_periods", "color_palettes"]
    extra_categories_list = ["subjects", "actions", "weathers", "lightings", "art_mediums", "perspectives", "emotion"]
    chosen = {}

    # Pick a random number of core categories
    num_core = random.randint(num_core_min, min(num_core_max, len(core_categories_list)))
    core_chosen_names = random.sample(core_categories_list, num_core)
    for cat in core_chosen_names:
        chosen[cat] = random.choice(CATEGORIES[cat])

    # Decide how many extra categories to pick
    actual_num_extra_max = min(num_extra_max, len(extra_categories_list))
    num_extra_min = min(num_extra_min, actual_num_extra_max)

    num_extra = random.randint(num_extra_min, actual_num_extra_max)
    if num_extra > 0:
        extras_chosen_names = random.sample(extra_categories_list, num_extra)
        for cat in extras_chosen_names:
            chosen[cat] = random.choice(CATEGORIES[cat])

    return chosen


def build_llm_json_prompt(chosen_keywords_list, theme: str, min_words=15, max_words=40):
    """Build a composite instruction prompt for the LLM.
    The prompt instructs the LLM to generate a number of unique, comma-separated diffusion prompts
    (one for each provided keyword set), each between min_words and max_words words.
    The output must be valid JSON in the format:
      ["prompt1", "prompt2", ...]
    """
    count = len(chosen_keywords_list)
    if count == 1:
        instructions = LLM_SURPRISE_ME_INITIAL_PROMPT_ONE % (min_words, max_words)
    else:
        instructions = LLM_SURPRISE_ME_INITIAL_PROMPT_MANY % (count, min_words, max_words)
    if theme.strip():
        if count == 1:
            instructions += f"5. Ensure that prompt clearly and explicitly references the given theme: {theme}.\n"
        else:
            instructions += f"5. Ensure that every prompt clearly and explicitly references the given theme: {theme}.\n"
    if count == 1:
        instructions += "\nGenerate a diffusion prompt based on each of the following keyword sets:\n\n"
    else:
        instructions += "\nGenerate a diffusion prompt for each of the following keyword sets, one for each set:\n\n"

    for i, chosen_keywords in enumerate(chosen_keywords_list, start=1):
        instructions += f"Keyword Set {i}:\n"
        for cat, keyword in chosen_keywords.items():
            instructions += f"{cat.capitalize()}: {keyword}\n"
        instructions += "\n"
    if count == 1:
        instructions += LLM_SURPRISE_ME_END_PROMPT_ONE
    else:
        instructions += LLM_SURPRISE_ME_END_PROMPT_MANY
    return instructions


async def surprise_me(
    user_id: str, is_admin: bool, theme: str, min_len: int = 15, max_len: int = 40, count: int = 1
) -> list[str]:
    """
    Generate a list of random diffusion prompts by making a single LLM request.
    This function builds multiple random keyword sets, constructs a composite prompt
    instructing the LLM to generate all prompts at once in JSON format, parses the output,
    and returns a list of distinct prompts.
    """
    llm_provider = await get_setting(user_id, "llm_provider", is_admin)
    if llm_provider not in ("gemini", "ollama"):
        raise ValueError("Invalid or missing LLM provider setting. Must be 'gemini' or 'ollama'.")
    # Generate a list of random keyword sets for each desired prompt.
    chosen_keywords_list = [pick_random_keywords() for _ in range(count)]
    composite_prompt = build_llm_json_prompt(chosen_keywords_list, theme=theme, min_words=min_len, max_words=max_len)
    if llm_provider == "ollama":
        ollama_url = await get_setting(user_id, "ollama_url", is_admin)
        if not ollama_url:
            ollama_url = None
        ollama_llm_model = await get_setting(user_id, "ollama_llm_model", is_admin)
        if not ollama_llm_model:
            ollama_llm_model = "gemma3:12b-it-qat"
        ollama_keepalive = await get_setting(user_id, "ollama_keepalive", is_admin)
        if ollama_keepalive:
            ollama_keepalive += "m"
        else:
            ollama_keepalive = 0
        client = ollama.AsyncClient(host=ollama_url)
        response_data = await client.generate(
            model=ollama_llm_model, prompt=composite_prompt, system="", keep_alive=ollama_keepalive
        )
        response_text = re.sub(r"<think>.*?</think>", "", response_data["response"], flags=re.DOTALL).strip()
    else:
        google_api_key = await get_setting(user_id, "google_api_key", is_admin)
        if not google_api_key:
            raise ValueError("No GOOGLE_API_KEY defined for Gemini usage.")
        google_proxy = await get_setting(user_id, "google_proxy", is_admin)
        gemini_model = await get_setting(user_id, "gemini_model", is_admin)
        if not gemini_model:
            gemini_model = "gemini-2.0-flash-001"
        transport_type = "rest" if google_proxy else None
        genai.configure(api_key=google_api_key, transport=transport_type)
        model = genai.GenerativeModel(model_name=gemini_model)
        generation_config = genai.GenerationConfig(response_mime_type="application/json")
        if google_proxy:
            with temporary_env_var("HTTP_PROXY", google_proxy), temporary_env_var("HTTPS_PROXY", google_proxy):
                response_data = model.generate_content(
                    composite_prompt, safety_settings="BLOCK_NONE", generation_config=generation_config
                )
        else:
            response_data = await model.generate_content_async(
                composite_prompt, safety_settings="BLOCK_NONE", generation_config=generation_config
            )
        finish_reason = int(response_data.candidates[0].finish_reason)
        if finish_reason not in (1, 2):  # 1 = stop, 2 = max_tokens
            raise ValueError(f"Gemini returned error with stop reason: {response_data.candidates[0].finish_reason}")
        response_text = response_data.text.strip()

    try:
        response_text = response_text.removeprefix("```json").removesuffix("```").strip()
        prompts = json.loads(response_text)
        if not isinstance(prompts, list) or len(prompts) != count:
            raise ValueError(f"The JSON output did not contain the expected number of prompts: \n{response_text}")
    except Exception as e:
        raise ValueError(f"Failed to parse JSON response from the LLM: \n{response_text}") from e
    return prompts
