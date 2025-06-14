import json
import os
import glob
from supabase import create_client, Client
from dotenv import load_dotenv
from jsonlib import parse_datetime_from_data, extract_number_from_filename, extract_number_from_string
import re
from typing import Dict, Union, Any
from datetime import datetime, timedelta

def initialize_supabase() -> Union[Client, Dict[str, Any]]:
    """
    Inisialisasi client Supabase dengan environment variables.
    
    Returns:
        Client: Supabase client jika berhasil
        Dict: Dictionary dengan error message jika gagal
    """
    # Load environment variables
    load_dotenv()
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        return {"success": False, "message": "Missing Supabase URL or Key"}
    
    try:
        # Initialize Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)
        return supabase
    except Exception as e:
        return {"success": False, "message": f"Failed to initialize Supabase client: {str(e)}"}

def get_supabase_client() -> Union[Client, None]:
    """
    Fungsi helper untuk mendapatkan Supabase client.
    
    Returns:
        Client: Supabase client jika berhasil, None jika gagal
    """
    result = initialize_supabase()
    
    if isinstance(result, dict):
        print(f"Error: {result['message']}")
        return None
    
    return result


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
        # Find all JSON files in output folder matching match_*.json
        json_files = glob.glob(os.path.join(output_dir, "match_*.json"))
        if not json_files:
            return {"success": False, "message": f"No match_*.json files found in {output_dir}"}

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
                        "datetime": match.get("Date"),
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
                        on_conflict="tour,match_name,court,datetime"
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
        # Find all JSON files in output folder matching match_*.json
        json_files = glob.glob(os.path.join(output_dir, "match_*.json"))
        if not json_files:
            return {"success": False, "message": f"No match_*.json files found in {output_dir}"}

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

                    # Handle winner field - convert to integer if it exists and is valid
                    winner = match.get("Winner")
                    if winner is not None:
                        # If winner is a string, try to convert to integer
                        if isinstance(winner, str):
                            if winner.strip().isdigit():
                                winner = int(winner.strip())
                            elif winner.strip().lower() in ['1', 'team 1', 'team1']:
                                winner = 1
                            elif winner.strip().lower() in ['2', 'team 2', 'team2']:
                                winner = 2
                            else:
                                winner = None  # Invalid winner format
                        # If winner is already an integer, validate it's 1 or 2
                        elif isinstance(winner, int):
                            if winner not in [1, 2]:
                                winner = None  # Invalid winner value
                        else:
                            winner = None  # Invalid winner type

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
                        "duration": match.get("Duration"),
                        "winner": winner  # Add winner field
                    }

                    # Insert or update (upsert) to handle duplicates
                    response = supabase.table("bwf_tour").upsert(
                        match_data,
                        on_conflict="tour,match,court,datetime"
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


async def bwf_schedule_to_supabase(schedule_dir: str = "input/schedule") -> dict:
    """Save schedule data from JSON files in schedule_dir to Supabase bwf_schedule table.
    
    Args:
        schedule_dir (str): Path to the folder containing schedule JSON files (default: 'input/schedule')
    
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
        # Process schedule JSON files from schedule_dir
        schedule_files = glob.glob(os.path.join(schedule_dir, "schedule_links_*.json"))
        if not schedule_files:
            return {
                "success": False,
                "message": f"No schedule_links_*.json files found in {schedule_dir}"
            }

        schedule_inserted = 0
        schedule_skipped = 0
        schedule_errors = []

        for schedule_file in schedule_files:
            try:
                # Extract tour number from filename (e.g., schedule_links_10.json -> 10)
                filename = os.path.basename(schedule_file)
                tour_match = re.search(r'schedule_links_(\d+)\.json', filename)
                if not tour_match:
                    schedule_errors.append(f"Skipped {schedule_file}: Could not extract tour number")
                    continue
                tour_number = int(tour_match.group(1))

                # Read schedule JSON file
                with open(schedule_file, "r", encoding="utf-8") as f:
                    urls = json.load(f)

                for url in urls:
                    # Extract date from URL (e.g., 2025-01-07)
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', url)
                    if date_match and "podium" not in url:  # Skip podium URLs
                        date_str = date_match.group(1)
                        try:
                            # Validate date format
                            schedule_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                            
                            # Prepare data for bwf_schedule table (exclude id as it's generated always)
                            schedule_data = {
                                "tour": tour_number,
                                "date": schedule_date.isoformat()
                            }

                            # Insert to bwf_schedule table (no upsert since id is auto-generated)
                            response = supabase.table("bwf_schedule").insert(
                                schedule_data
                            ).execute()

                            if response.data:
                                schedule_inserted += 1
                            else:
                                schedule_errors.append(
                                    f"Failed to insert schedule for tour {tour_number} and date {date_str}: {response.error}"
                                )
                                schedule_skipped += 1
                        except ValueError:
                            schedule_errors.append(f"Invalid date format in {url}")
                            schedule_skipped += 1
                    else:
                        schedule_skipped += 1

            except Exception as e:
                schedule_errors.append(f"Error processing {schedule_file}: {str(e)}")
                schedule_skipped += 1

        # Prepare final result
        result = {
            "success": schedule_inserted > 0,
            "message": (
                f"Processed {len(schedule_files)} schedule JSON files: "
                f"Inserted {schedule_inserted} schedule entries, Skipped {schedule_skipped} schedule entries"
            )
        }
        if schedule_errors:
            result["message"] += f"\nErrors encountered:\n" + "\n".join(schedule_errors)

        return result

    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing files in {schedule_dir}: {str(e)}"
        }
    
async def bwf_rankings_to_supabase(json_file: str) -> dict:
    """Load JSON tournament data to Supabase bwf_tournament table.
    
    Args:
        json_file (str): Path to the JSON file containing tournament data
    
    Returns:
        dict: Result with success status and message
    """
    client = get_supabase_client()
    if client:
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
                    "id": tournament.get("index"),
                    "name": tournament.get("name"),
                    "date": tournament.get("date"),
                    "location": tournament.get("location"),
                    "category": tournament.get("category"),
                    "prize_money": tournament.get("prize_money"),
                    "results_url": tournament.get("results_url"),
                    "status": tournament.get("status")
                }

                # Insert or update (upsert) to handle duplicates
                response = supabase.table("bwf_rankings").upsert(
                    tournament_data,
                    on_conflict="rank,category,base_category,week"
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
        

# Helper: convert "Week 20" → 20, and generate week_date (Monday of that ISO week)
def parse_week(week_str):
    """
    Parse week string seperti "Week 20" menjadi week number dan date.
    
    Args:
        week_str (str): String week format "Week X"
    
    Returns:
        tuple: (week_num, week_date) atau (None, None) jika tidak valid
    """
    match = re.search(r"Week (\d+)", week_str)
    if match:
        week_num = int(match.group(1))
        year = datetime.now().year  # adjust if week info comes with year
        return week_num, datetime.fromisocalendar(year, week_num, 1).date()
    return None, None


async def delete_bwf_tour(tour: int, date: str):
    """
    Delete records from 'bwf_tour' where tour equals `tour` and datetime falls on the specified date (dd-mm-yyyy).
    """
    supabase = get_supabase_client()
    if not supabase:
        return {"success": False, "message": "Failed to initialize Supabase client"}

    try:
        # Ubah string tanggal ke datetime object
        start = datetime.strptime(date, "%Y-%m-%d")
        end = start + timedelta(days=1)

        # Hapus data dengan tour yang cocok dan datetime antara [start, end)
        response = supabase.table("bwf_tour") \
            .delete() \
            .eq("tour", tour) \
            .gte("datetime", start.isoformat()) \
            .lt("datetime", end.isoformat()) \
            .execute()

        return {
            "success": True,
            "message": "Succeed to delete data"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to delete data: {str(e)}"
        }


async def delete_bwf_rankings_data(week_num, rank_category=0):
    # Get Supabase client
    supabase = get_supabase_client()
    if not supabase:
        return {"success": False, "message": "Failed to initialize Supabase client"}
    
    try:
        # delete to Supabase
        response = supabase.table("bwf_rankings").delete().eq("week", week_num).eq("rank_category", rank_category).execute()
        return {
            "success": True,
            "message": f"Succeed to delete data"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to delete data: {str(e)}"
        }
    

def delete_bwf_rankings_data_by_week(week_num):
    # Get Supabase client
    supabase = get_supabase_client()
    if not supabase:
        return {"success": False, "message": "Failed to initialize Supabase client"}
    
    try:
        # delete to Supabase
        supabase.table("bwf_rankings").delete().eq("week", week_num).execute()

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to delete data: {str(e)}"
        }
    



def insert_bwf_rankings_data(data, week):
    """
    Insert data BWF rankings ke Supabase database.
    
    Args:
        data (list): List of BWF ranking data
    
    Returns:
        dict: Result dengan status success/error dan message
    """

    # match = re.search(r"Week (\d+)", week)
    # week_num = int(match.group(1))

    week_num = int(week)

    # Get Supabase client
    supabase = get_supabase_client()
    if not supabase:
        return {"success": False, "message": "Failed to initialize Supabase client"}
    
    # Mapping from event/category to base_category (customize as needed)
    base_category_map = {
        "MEN'S DOUBLES": "MD",
        "WOMEN'S DOUBLES": "WD",
        "MIXED DOUBLES": "XD",
        "MEN'S SINGLES": "MS",
        "WOMEN'S SINGLES": "WS"
    }

    rank_categories = [
        "BWF World Rankings",
        "BWF World Tour Rankings",
        "BWF World Junior Rankings",
        "BWF World Team Rankings",
        "BWF World Championships Rankings",
        "Olympic Games Qualification",
        "BWF Para Badminton World Rankings",
        "Paralympic Games Qualification",
        "Parapan American Games Qualification"
    ]

    rank_category_map = {text: index for index, text in enumerate(rank_categories)}
    
    inserted_count = 0
    errors = []
   
    try:

        # delete to Supabase
        # supabase.table("bwf_rankings").delete().eq("week", week_num).execute()

        # Insert to Supabase
        for entry in data:
            try:
                week_num, week_date = parse_week("Week " + str(entry["week"]))
                rank_category = rank_category_map.get(entry["ranking_option"], -1)
                base_category = base_category_map.get(entry["event"].upper(), -1)
                
                row = {
                    "rank": int(entry["rank"]),
                    "category": base_category,
                    "rank_category": rank_category,
                    "points": int(entry["points"]),
                    "tournaments": 0,  # If not provided
                    "week": week_num,
                    "week_date": str(week_date),
                    "player1_name": entry["players"][0]["player_name"],
                    "nationality1": entry["country"],
                    "player2_name": entry["players"][1]["player_name"] if len(entry["players"]) > 1 else "",
                    "nationality2": entry["country"],
                    "created_at": datetime.now().isoformat()
                }


                
                # Upsert into the table (avoid duplicate by unique constraint)
                response = supabase.table("bwf_rankings").upsert(
                    row, 
                    on_conflict="rank,category,rank_category,week,player1_name"
                ).execute()
                
                inserted_count += 1
                print(f"Inserted rank {entry['rank']} - {entry['players'][0]['player_name']}")
                
            except Exception as e:
                error_msg = f"Error inserting rank {entry.get('rank', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                print(error_msg)
        
        return {
            "success": True,
            "message": f"Successfully inserted {inserted_count} records",
            "inserted_count": inserted_count,
            "errors": errors
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to insert data: {str(e)}",
            "inserted_count": inserted_count,
            "errors": errors
        }
