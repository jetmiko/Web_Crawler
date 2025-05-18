import asyncio
import os
import glob
import shutil
import sys
import json
from datetime import datetime
from rank_functions import scrape_rank, rank_to_json
from supabase_lib import load_json_to_supabase

async def main():
    # Check for command-line argument
    if len(sys.argv) != 2:
        print("Usage: python run.py <mode> (1 for scrape only, 2 for Supabase only, 3 for ranking options only, 10 for scrape and Supabase)")
        return
    
    try:
        mode = int(sys.argv[1])
        if mode not in [1, 2, 3, 10]:
            print("Invalid mode. Use 1 for scrape only, 2 for Supabase only, 3 for ranking options only, or 10 for scrape and Supabase.")
            return
    except ValueError:
        print("Mode must be an integer (1, 2, 3, or 10).")
        return

    url = "https://bwfbadminton.com/rankings/"
    output_dir = "output"
    data_dir = "data"
    # default_ranking_option = "BWF World Junior Rankings"

    # Determine ranking_option for modes 1 and 10
    # ranking_option = default_ranking_option

    if mode in [1, 10]:
        # Find the latest JSON file in 'data' folder
        json_pattern = os.path.join(data_dir, "ranking_options_*.json")
        json_files = glob.glob(json_pattern)
        if json_files:
            latest_json = max(json_files, key=os.path.getctime)
            try:
                with open(latest_json, "r", encoding="utf-8") as f:
                    ranking_options = json.load(f)
                if ranking_options and isinstance(ranking_options, list) and len(ranking_options) > 0:
                    for ranking_option in ranking_options:
                        print(f"Processing ranking option: {ranking_option}")
                        rankings = await scrape_rank(url, ranking_option, output_dir)
                        print(f"Scraped {len(rankings)} rankings for ranking option: {ranking_option}")
                else:
                    print(f"Warning: No valid ranking options found in {latest_json}. ")
            except Exception as e:
                print(f"Warning: Failed to read {latest_json}: {str(e)}. ")
        else:
            print(f"Warning: No JSON files found in {data_dir}. ")
    
    # if mode in [1, 10]:
    #     # Find the latest JSON file in 'data' folder
    #     json_pattern = os.path.join(data_dir, "ranking_options_*.json")
    #     json_files = glob.glob(json_pattern)
    #     if json_files:
    #         latest_json = max(json_files, key=os.path.getctime)
    #         try:
    #             with open(latest_json, "r", encoding="utf-8") as f:
    #                 ranking_options = json.load(f)
    #             if ranking_options and isinstance(ranking_options, list) and len(ranking_options) > 0:
    #                 ranking_option = ranking_options[0]
    #                 # weeks = await scrape_rank(url, ranking_option, output_dir)
    #                 rankings = await scrape_rank(url, ranking_option, output_dir)
    #                 print(f"Using ranking option from {latest_json}: {ranking_option}")
    #                 # print(f"Scraped {len(rankings)} rankings for ranking option: {rankings}")
    #             else:
    #                 print(f"Warning: No valid ranking options found in {latest_json}. Using default: {default_ranking_option}")
    #         except Exception as e:
    #             print(f"Warning: Failed to read {latest_json}: {str(e)}. Using default: {default_ranking_option}")
    #     else:
    #         print(f"Warning: No JSON files found in {data_dir}. Using default: {default_ranking_option}")

    if mode == 3:
        # Generate JSON file with ranking options
        ranking_options = await rank_to_json(url, output_dir)
        if not ranking_options:
            print("Failed to generate ranking options JSON")
            return
        print(f"Ranking options: {ranking_options}")

        # Save ranking_options to JSON file in 'data' folder
        os.makedirs(data_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = os.path.join(data_dir, f"ranking_options_{timestamp}.json")
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(ranking_options, f, indent=2, ensure_ascii=False)
            print(f"Saved ranking options to {json_path}")
        except Exception as e:
            print(f"Failed to save ranking options to {json_path}: {str(e)}")
        return

    # if mode in [1, 10]:
    #     # Scrape BWF data
    #     matches = await scrape_rank(url, ranking_option, output_dir)
    #     if not matches:
    #         print("Failed to scrape tournament data")
    #         return
    #     print(f"Successfully scraped {len(matches)} tournament")

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