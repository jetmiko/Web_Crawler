import json
import os
import glob
from supabase import create_client, Client
from dotenv import load_dotenv

async def save_tour_to_supabase(output_dir: str = "output") -> dict:
    """Save JSON match data from output folder to Supabase bwf_tour table.
    
    Args:
        output_dir (str): Path to the folder containing JSON files (default: 'output')
    
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
        # Find all JSON files in output folder matching match_card_text_*.json
        json_files = glob.glob(os.path.join(output_dir, "match_card_text_*.json"))
        if not json_files:
            return {"success": False, "message": f"No match_card_text_*.json files found in {output_dir}"}

        total_inserted = 0
        total_skipped = 0
        total_files = len(json_files)
        error_messages = []

        for json_file in json_files:
            try:
                # Read JSON file
                with open(json_file, "r", encoding="utf-8") as f:
                    matches = json.load(f)

                if not matches:
                    error_messages.append(f"No match data found in {json_file}")
                    continue

                # Insert matches into bwf_tour table
                inserted_count = 0
                skipped_count = 0
                for match in matches:
                    # Validate required fields
                    required_fields = [
                        "Tour", "Match_Name", "Team_1_Players", "Team_1_Country",
                        "Team_2_Players", "Team_2_Country", "Separator", "Date",
                        "Status", "Time", "Category", "Round", "Court", "Stadium"
                    ]
                    missing_fields = [field for field in required_fields if not match.get(field)]
                    if missing_fields:
                        error_messages.append(
                            f"Skipped match {match.get('Match_Name', 'unknown')} in {json_file}: "
                            f"Missing required fields: {', '.join(missing_fields)}"
                        )
                        skipped_count += 1
                        continue

                    # Prepare data for insertion
                    match_data = {
                        "tour": match.get("Tour", "Unknown Tournament"),
                        "match_name": match.get("Match_Name"),
                        "team_1_players": match.get("Team_1_Players"),
                        "team_1_country": match.get("Team_1_Country"),
                        "team_1_seeding": match.get("Team_1_Seeding"),
                        "team_2_players": match.get("Team_2_Players"),
                        "team_2_country": match.get("Team_2_Country"),
                        "team_2_seeding": match.get("Team_2_Seeding"),
                        "separator": match.get("Separator"),
                        "scores": match.get("Scores"),
                        "date": match.get("Date"),
                        "status": match.get("Status"),
                        "time": match.get("Time"),
                        "category": match.get("Category"),
                        "round": match.get("Round"),
                        "court": match.get("Court"),
                        "stadium": match.get("Stadium"),
                        "duration": match.get("Duration")
                    }

                    # Insert or update (upsert) to handle duplicates
                    response = supabase.table("bwf_tour").upsert(
                        match_data,
                        on_conflict="tour,match_name,court,date"
                    ).execute()

                    # Check if insertion was successful
                    if response.data:
                        inserted_count += 1
                    else:
                        error_messages.append(
                            f"Failed to insert match {match.get('Match_Name')} from {json_file}: {response.error}"
                        )

                total_inserted += inserted_count
                total_skipped += skipped_count
                print(f"Processed {json_file}: Inserted {inserted_count} matches, Skipped {skipped_count} matches")

            except Exception as e:
                error_messages.append(f"Error processing {json_file}: {str(e)}")

        # Prepare final result
        result = {
            "success": total_inserted > 0,
            "message": f"Processed {total_files} JSON files: Inserted {total_inserted} matches, Skipped {total_skipped} matches"
        }
        if error_messages:
            result["message"] += f"\nErrors encountered:\n" + "\n".join(error_messages)

        return result

    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing files in {output_dir}: {str(e)}"
        }