import asyncio
import os
import glob
import shutil
import sys
from list_cal import scrape_bwf_tournaments
from supabase_lib import load_json_to_supabase

async def main():
    # Check for command-line argument
    if len(sys.argv) != 2:
        print("Usage: python run.py <mode> (1 for scrape only, 2 for Supabase only, 10 for both)")
        return
    
    try:
        mode = int(sys.argv[1])
        if mode not in [1, 2, 10]:
            print("Invalid mode. Use 1 for scrape only, 2 for Supabase only, or 10 for both.")
            return
    except ValueError:
        print("Mode must be an integer (1, 2, or 10).")
        return

    url = "https://bwfworldtour.bwfbadminton.com/calendar/?cyear=2025&rstate=all"
    output_dir = "output"

    if mode in [1, 10]:
        # Scrape BWF data
        matches = await scrape_bwf_tournaments(url, output_dir)
        if not matches:
            print("Failed to scrape tournament data")
            return
        print(f"Successfully scraped {len(matches)} tournament")

    if mode in [2, 10]:
        # Find the latest JSON file
        json_pattern = os.path.join(output_dir, "tournament_data_*.json")
        json_files = glob.glob(json_pattern)
        if not json_files:
            print(f"No JSON files found in {output_dir}")
            return
        
        latest_json = max(json_files, key=os.path.getctime)
        
        # Load to Supabase
        result = await load_json_to_supabase(latest_json)
        if result["success"]:
            print(result["message"])
            
            # Rename output folder to output1, output2, etc.
            try:
                i = 1
                while True:
                    new_output_dir = f"output{i}"
                    if not os.path.exists(new_output_dir):
                        shutil.move(output_dir, new_output_dir)
                        print(f"Renamed {output_dir} to {new_output_dir}")
                        break
                    i += 1
            except FileNotFoundError:
                print(f"Error: {output_dir} folder not found for renaming")
            except Exception as e:
                print(f"Error renaming {output_dir}: {str(e)}")
        else:
            print(f"Failed to load to Supabase: {result['message']}")

if __name__ == "__main__":
    asyncio.run(main())