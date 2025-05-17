import json
import os
import glob
from supabase import create_client, Client
from uuid import uuid4
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Supabase client using environment variables
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

# Validate environment variables
if not url or not key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")

supabase: Client = create_client(url, key)

def load_json_to_supabase():
    """Read JSON files from output folder and insert into bwf_matches table."""
    output_dir = "output"
    json_pattern = os.path.join(output_dir, "match_data_*.json")
    
    # Find all JSON files
    json_files = glob.glob(json_pattern)
    if not json_files:
        print(f"No JSON files found in {output_dir}")
        return

    for json_file in json_files:
        print(f"Processing file: {json_file}")
        try:
            # Read JSON file
            with open(json_file, "r", encoding="utf-8") as f:
                matches_data = json.load(f)
            
            if not isinstance(matches_data, list):
                print(f"Error: {json_file} does not contain a list of matches")
                continue

            # Insert each match
            for match in matches_data:
                try:
                    # Validate required fields
                    required_fields = ["tournament_name", "date", "court", "venue", "match_number", "team1", "team2", "scores"]
                    missing_fields = [field for field in required_fields if field not in match]
                    if missing_fields:
                        print(f"Skipping match in {json_file}: Missing fields {missing_fields}")
                        continue

                    # Prepare match record
                    match_record = {
                        "id": str(uuid4()),
                        "tournament_name": match["tournament_name"],
                        "match_date": match["date"],
                        "court": match["court"],
                        "venue": match["venue"],
                        "winner": match.get("winner"),  # Allow null
                        "match_number": match["match_number"],
                        "team1": match["team1"],
                        "team2": match["team2"],
                        "scores": match["scores"]
                    }

                    # Insert into bwf_matches table
                    supabase.table("bwf_matches").insert(match_record).execute()
                    print(f"Inserted match: {match['match_number']} from {json_file}")

                except Exception as e:
                    # Handle duplicate matches or other errors
                    if "duplicate key value violates unique constraint" in str(e):
                        print(f"Skipped duplicate match: {match.get('match_number', 'Unknown')} in {json_file}")
                    else:
                        print(f"Error inserting match from {json_file}: {str(e)}")

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON in {json_file}: {str(e)}")
        except Exception as e:
            print(f"Error processing {json_file}: {str(e)}")

    print("Finished processing all JSON files.")

if __name__ == "__main__":
    load_json_to_supabase()