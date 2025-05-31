import json
import os
import glob
from supabase import create_client, Client
from dotenv import load_dotenv
from jsonlib import parse_datetime_from_data, extract_number_from_filename, extract_number_from_string
import re

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
    

async def bwf_calendar_to_supabase(output_dir: str = "output") -> dict:
    """
    Save JSON calendar data from output folder to Supabase bwf_calendar table, including id field.
    
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

    # Month mapping for conversion
    month_map = {
        "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4, "MAY": 5, "JUNE": 6,
        "JULY": 7, "AUGUST": 8, "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12
    }

    try:
        # Find all JSON files in output folder matching calendar_*.json
        json_files = glob.glob(os.path.join(output_dir, "calendar_*.json"))
        if not json_files:
            return {"success": False, "message": f"No calendar_*.json files found in {output_dir}"}

        total_inserted = 0
        total_skipped = 0
        total_files = len(json_files)
        error_messages = []

        for json_file in json_files:
            try:
                # Read JSON file
                with open(json_file, "r", encoding="utf-8") as f:
                    tournaments = json.load(f)

                if not tournaments:
                    error_messages.append(f"No tournament data found in {json_file}")
                    continue

                # Insert tournaments into bwf_calendar table
                inserted_count = 0
                skipped_count = 0
                for tournament in tournaments:
                    # Validate required fields
                    required_fields = [
                        "Month", "Date", "Tournament_Name", "Location",
                        "Country", "Category", "Prize_Money", "id"
                    ]
                    missing_fields = [field for field in required_fields if not tournament.get(field)]
                    if missing_fields:
                        error_messages.append(
                            f"Skipped tournament {tournament.get('Tournament_Name', 'unknown')} in {json_file}: "
                            f"Missing required fields: {', '.join(missing_fields)}"
                        )
                        skipped_count += 1
                        continue

                    # Convert month to integer
                    month_str = tournament.get("Month").upper()
                    if month_str not in month_map:
                        error_messages.append(
                            f"Skipped tournament {tournament.get('Tournament_Name', 'unknown')} in {json_file}: "
                            f"Invalid month: {month_str}"
                        )
                        skipped_count += 1
                        continue
                    month_num = month_map[month_str]

                    # Clean prize money
                    prize_money_str = tournament.get("Prize_Money")
                    try:
                        prize_money = int(prize_money_str.replace("US $ ", "").replace(",", ""))
                    except (ValueError, AttributeError):
                        error_messages.append(
                            f"Skipped tournament {tournament.get('Tournament_Name', 'unknown')} in {json_file}: "
                            f"Invalid prize money format: {prize_money_str}"
                        )
                        skipped_count += 1
                        continue

                    # Clean category by removing "HSBC BWF WORLD TOUR " prefix
                    category = tournament.get("Category", "")
                    if category.startswith("HSBC BWF WORLD TOUR "):
                        category = category.replace("HSBC BWF WORLD TOUR ", "")

                    # Prepare data for insertion, including id
                    tournament_data = {
                        "id": tournament.get("id"),
                        "month": month_num,
                        "date": tournament.get("Date"),
                        "name": tournament.get("Tournament_Name"),
                        "location": tournament.get("Location"),
                        "country": tournament.get("Country"),
                        "category": category,
                        "prize_money": prize_money
                    }

                    # Insert or update (upsert) to handle duplicates
                    response = supabase.table("bwf_calendar").upsert(
                        tournament_data,
                        on_conflict="id"  # Use id as the conflict key
                    ).execute()

                    # Check if insertion was successful
                    if response.data:
                        inserted_count += 1
                    else:
                        error_messages.append(
                            f"Failed to insert tournament {tournament.get('Tournament_Name')} from {json_file}: {response.error}"
                        )

                total_inserted += inserted_count
                total_skipped += skipped_count
                print(f"Processed {json_file}: Inserted {inserted_count} tournaments, Skipped {skipped_count} tournaments")

            except Exception as e:
                error_messages.append(f"Error processing {json_file}: {str(e)}")

        # Prepare final result
        result = {
            "success": total_inserted > 0,
            "message": f"Processed {total_files} JSON files: Inserted {total_inserted} tournaments, Skipped {total_skipped} tournaments"
        }
        if error_messages:
            result["message"] += f"\nErrors encountered:\n" + "\n".join(error_messages)

        return result

    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing files in {output_dir}: {str(e)}"
        }
    

async def bwf_tour_to_supabase(output_dir: str = "output") -> dict:
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
            print(json_file)
            try:
                # # Extract tour number from filename (e.g., match_card_text_01.json -> 01)
                # tour_number = extract_number_from_filename(json_file)
                # if not tour_number:
                #     error_messages.append(f"Skipped {json_file}: Could not extract tour number")
                #     continue
                # tour_number = int(tour_number)  # Convert to integer for table

                # Read JSON file
                with open(json_file, "r", encoding="utf-8") as f:
                    matches = json.load(f)

                if not matches:
                    error_messages.append(f"No match data found in {json_file}")
                    continue

                inserted_count = 0
                skipped_count = 0
                for match in matches:
                    # Validate required fields
                    required_fields = [
                        "Match_Name", "Team_1_Players", "Team_1_Country",
                        "Team_2_Players", "Team_2_Country", "Date",
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

                    # Extract court number (e.g., "Court 1" -> 1)
                    court_str = match.get("Court", "")
                    court_number = re.search(r'\d+', court_str)
                    court_number = int(court_number.group(0)) if court_number else None
                    if court_number is None:
                        error_messages.append(
                            f"Skipped match {match.get('Match_Name', 'unknown')} in {json_file}: "
                            f"Invalid court format: {court_str}"
                        )
                        skipped_count += 1
                        continue

                    # Parse datetime
                    match_datetime = parse_datetime_from_data({
                        "Date": match.get("Date"),
                        "Time": match.get("Time")
                    })
                    if match_datetime is None:
                        error_messages.append(
                            f"Skipped match {match.get('Match_Name', 'unknown')} in {json_file}: "
                            f"Invalid datetime format"
                        )
                        skipped_count += 1
                        continue

                    # Ensure team_1_players and team_2_players are lists
                    team_1_players = match.get("Team_1_Players")
                    team_2_players = match.get("Team_2_Players")
                    scores = match.get("Scores")
                    if isinstance(team_1_players, str):
                        team_1_players = [team_1_players]
                    if isinstance(team_2_players, str):
                        team_2_players = [team_2_players]
                    if isinstance(scores, str):
                        scores = [scores] if scores else []

                    # Prepare data for insertion
                    match_data = {
                        "tour": match.get("id"),
                        "court": court_number,
                        "match": extract_number_from_filename( match.get("Match_Name")),
                        "team_1_players": team_1_players,
                        "team_1_country": match.get("Team_1_Country"),
                        "team_1_seeding": extract_number_from_string(match.get("Team_1_Seeding")),
                        "team_2_players": team_2_players,
                        "team_2_country": match.get("Team_2_Country"),
                        "team_2_seeding": extract_number_from_string(match.get("Team_2_Seeding")),
                        "scores": scores if scores else None,
                        "datetime": match_datetime.isoformat(),
                        "status": match.get("Status"),
                        "category": match.get("Category"),
                        "round": match.get("Round"),
                        "stadium": match.get("Stadium"),
                        "duration": match.get("Duration")
                    }

                    # Insert or update (upsert) to handle duplicates
                    response = supabase.table("bwf_tour").upsert(
                        match_data,
                        on_conflict="tour,match,court"
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

