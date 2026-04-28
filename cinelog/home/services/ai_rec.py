""" Talks to OpenAI and prompts AI recommended movie results """
from openai import OpenAI
from django.conf import settings
import json


def get_movie_recommendation(
    genres, era, person, awards=None, excluded_titles=None, liked_movies=None
):
    prompt_parts = []
    if genres:
        prompt_parts.append(f"Mood/Genre: {', '.join(genres)}")
    if era:
        prompt_parts.append(f"Era: {era}")
    if person:
        prompt_parts.append(f"Featuring or directed by: {person}")
    if awards:
        prompt_parts.append(f"Awards: {', '.join(awards)}")

    preferences = " | ".join(prompt_parts) if prompt_parts else "any genre, any era"

    # build exclusion string
    exclusion_note = ""
    if excluded_titles:
        titles_list = ", ".join(excluded_titles)
        exclusion_note = f" Do NOT recommend any of these movies: {titles_list}."

    # build liked movies context for surprise mode
    liked_note = ""
    if liked_movies:
        liked_parts = []
        for m in liked_movies:
            liked_parts.append(f"{m['title']} (rated {m['rating']}/5)")
        liked_note = ( 
        f" The user has already watched and logged these movies: "
        f"{', '.join(liked_parts)}. " 
        "Use this to inform your recommendations and mention relevant ones "
        "in your reason using phrasing like 'because you watched X'." 
        )

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    message = client.chat.completions.create(
        model="gpt-5-mini",
        max_completion_tokens=3000,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a movie recommendation expert. "
                    "You only recommend real, well-known movies. "
                    "Always reply with a valid JSON array and nothing else. "
                    "Do not wrap your response in markdown or code fences."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Recommend exactly 3 perfect movies for someone with these preferences: "
                    f"{preferences}. "
                    f"{liked_note}"
                    f"{exclusion_note}"
                    "Reply with ONLY a JSON array in this format, no extra text, no code fences: "
                    '[{"title": "...", "year": "...", "reason": "..."}, '
                    '{"title": "...", "year": "...", "reason": "1 sentence max"}]'
                ),
            },
        ],
    )

    raw = message.choices[0].message.content
    try:
        raw = (
            raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        )
        return json.loads(raw)
    except Exception as e:
        return [
            {
                "title": "Could not generate recommendation",
                "year": "",
                "reason": "Please try again.",
            }
        ]
