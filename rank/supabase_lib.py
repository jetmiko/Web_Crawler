import json
import os
from supabase import create_client, Client
from dotenv import load_dotenv

async def load_json_to_supabase(json_file: str) -> dict:
    """Load JSON tournament data to Supabase bwf_tournament table.
    
    Args:
        json_file (str): Path to the JSON file containing tournament data
    
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
            tournaments = json.load(f)

        if not tournaments:
            return {"success": False, "message": f"No tournament data found in {json_file}"}

        # Insert tournaments into bwf_tournament table
        inserted_count = 0
        for tournament in tournaments:
            # Prepare data for insertion
            tournament_data = {
                "index": tournament.get("index"),
                "name": tournament.get("name"),
                "date": tournament.get("date"),
                "location": tournament.get("location"),
                "category": tournament.get("category"),
                "prize_money": tournament.get("prize_money"),
                "results_url": tournament.get("results_url"),
                "status": tournament.get("status")
            }

            # Insert or update (upsert) to handle duplicates
            response = supabase.table("bwf_tournament").upsert(
                tournament_data,
                on_conflict="name,date"
            ).execute()

            # Check if insertion was successful
            if response.data:
                inserted_count += 1
            else:
                print(f"Failed to insert tournament {tournament.get('name')}: {response.error}")

        return {
            "success": True,
            "message": f"Processed {json_file}: Inserted {inserted_count} tournaments"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing {json_file}: {str(e)}"
        }