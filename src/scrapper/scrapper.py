import json
import pandas as pd
from difflib import get_close_matches
from openai import OpenAI
import os, json
from dotenv import load_dotenv
import json

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
stops = pd.read_csv("stops_deduped.csv")

def generate_prompt(text: str) -> str:
    return f"""Analyze the transport alert below and return only valid JSON with:
    - "description": under 5 words summarizing what happened in Polish,
    - "category": "incident" (accident, crash, obstruction) or "traffic" (delay, congestion),
    - "loc": most likely cracovian stop name (stop, street, or area).
    If info missing, use null.
    Text: {text}"""

def find_stop(query: str, stops_df: pd.DataFrame):
    names = stops_df["stop_name"].tolist()
    match = get_close_matches(query, names, n=1, cutoff=0.4)
    if match:
        stop = stops_df[stops_df["stop_name"] == match[0]].iloc[0]
        return {
            "matched_name": stop["stop_name"],
            "latitude": stop["stop_lat"],
            "longitude": stop["stop_lon"]
        }
    else:
        return None
    
