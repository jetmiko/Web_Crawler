import json
import os
from supabase import create_client, Client
from dotenv import load_dotenv

async def load_json_to_supabase(json_file: str) -> dict:
    """Load JSON match data to Supabase bwf_matches table.
    
    Args:
        json_file (str): Path to the JSON file containing match data
    
    Returns:
        dict: Result with success status and message
    """
    # Load environment variables
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        return {"success": False, "message": "Missing Supabase URL or Key"}

    # Initialize Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)

    try:
        # Read JSON file
        with open(json_file, "r", encoding="utf-8") as f:
            matches = json.load(f)

        if not matches:
            return {"success": False, "message": f"No match data found in {json_file}"}

        # Insert matches into bwf_matches table
        inserted_count = 0
        for match in matches:
            # Prepare data for insertion
            match_data = {
                "tournament_name": match.get("tournament_name"),
                "match_date": match.get("date"),
                "court": match.get("court"),
                "venue": match.get("venue"),
                "winner": match.get("winner"),
                "match_number": match.get("match_number"),
                "team1": match.get("team1"),
                "team2": match.get("team2"),
                "scores": match.get("scores"),
                "category": match.get("category"),
                "round": match.get("round"),
                "schedule_status": match.get("schedule_status"),
                "schedule_date": match.get("schedule_date")
            }

            # Insert or update (upsert) to handle duplicates
            response = supabase.table("bwf_matches").upsert(
                match_data,
                on_conflict="tournament_name,match_date,match_number,court"
            ).execute()

            # Check if insertion was successful
            if response.data:
                inserted_count += 1
            else:
                print(f"Failed to insert match {match.get('match_number')}: {response.error}")

        return {
            "success": True,
            "message": f"Processed {json_file}: Inserted {inserted_count} matches"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing {json_file}: {str(e)}"
        }