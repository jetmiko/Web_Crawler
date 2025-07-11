import json
import os
from typing import List, Union
import re
from datetime import datetime

def extract_date_from_string(text: str) -> str:
    """
    Extracts the date (in YYYY-MM-DD format) from a string.
    Returns the date string or None if not found or invalid.
    """
    try:
        # Cari pola tanggal di akhir string
        match = re.search(r'(\d{4}-\d{2}-\d{2})$', text)
        if match:
            date_str = match.group(1)
            
            # Validasi apakah memang tanggal yang sah
            datetime.strptime(date_str, "%Y-%m-%d")  # akan raise ValueError jika tidak valid
            return date_str
        else:
            return None
    except Exception as e:
        print(f"Error extracting date: {e}")
        return None


def extract_number_from_filename(filename):
    try:
        # Use regex to find a number (one or more digits) in the filename
        match = re.search(r'\d+', filename)
        if match:
            return match.group(0)
        else:
            print(f"Error: No number found in filename {filename}")
            return ""
    except Exception as e:
        print(f"Error: {str(e)}")
        return ""
    
def extract_number_from_string(input_string):
    # Periksa apakah input_string adalah None
    if input_string is None:
        # print("Input string adalah None, mengembalikan 0.")
        return 0
    
    try:
        # Gunakan regex untuk menemukan angka (satu digit atau lebih) dalam string
        match = re.search(r'\d+', input_string)
        if match:
            # Ubah hasil yang cocok menjadi integer dan kembalikan
            return int(match.group(0))
        else:
            print(f"Error: Tidak ada angka ditemukan dalam string '{input_string}', mengembalikan 0.")
            return 0 # Kembalikan 0 jika tidak ada angka yang ditemukan
    except TypeError:
        # Menangani kasus jika input_string bukan string (selain None yang sudah ditangani)
        # Misalnya, jika input adalah tipe data numerik atau boolean secara tidak sengaja.
        print(f"Error: Tipe input tidak valid ('{type(input_string).__name__}'), mengembalikan 0.")
        return 0
    except Exception as e:
        print(f"Error: {str(e)}, mengembalikan 0.")
        return 0 # Kembalikan 0 jika terjadi kesalahan lain

def parse_datetime_from_data(data):
    try:
        # Extract date and time from the input dictionary
        date_str = data.get("Date", "").strip()
        time_str = data.get("Time", "").strip()

        # Check if date and time are provided
        if not date_str or not time_str:
            print("Error: Missing Date or Time in input data")
            return None

        # Remove "Est." prefix from time if present
        time_str = re.sub(r'^Est\.\s*', '', time_str)

        # print(f"time_str: {time_str}")

        # Combine date and time strings, assuming year 2025
        datetime_str = f"{date_str} 2025 {time_str}"

        # Parse the combined string into a datetime object
        dt = datetime.strptime(datetime_str, "%d %b %Y %I:%M %p")

        return dt

    except ValueError as e:
        print(f"Error: Invalid date or time format - {str(e)}")
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

# Example usage:
# data = {"Date": "7 JAN", "Time": "Est. 11:30 AM"}
# result = parse_datetime_from_data(data)
# print(result)  # Output: 2025-01-07 11:30:00


def read_json_list(folder, filename):
    file_path = os.path.join(folder, filename)
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            if isinstance(data, list):
                return data
            else:
                print("Error: JSON root is not a list")
                return []
    except FileNotFoundError:
        print(f"Error: File {file_path} not found")
        return []
    except json.JSONDecodeError:
        print("Error: Invalid JSON format")
        return []
    except Exception as e:
        print(f"Error: {str(e)}")
        return []


def get_string_array_from_json(filename: str, key: str, folder_name: str = "") -> List[str]:
    """
    Membaca file JSON dan menghasilkan array string berdasarkan key tertentu.
    
    Args:
        filename (str): Nama file JSON yang akan dibaca
        key (str): Key yang akan diambil nilainya dari setiap object dalam JSON
        folder_name (str, optional): Nama folder tempat file JSON berada
        
    Returns:
        List[str]: Array berisi nilai string dari key yang diminta
        
    Raises:
        FileNotFoundError: Jika file tidak ditemukan
        json.JSONDecodeError: Jika format JSON tidak valid
        KeyError: Jika key tidak ditemukan dalam object
        TypeError: Jika data JSON bukan berupa list
    """
    try:
        # Menentukan path file dengan folder jika ada
        if folder_name:
            file_path = os.path.join(folder_name, filename)
        else:
            file_path = filename
            
        # Membaca file JSON
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Memastikan data adalah list
        if not isinstance(data, list):
            raise TypeError("JSON data harus berupa array/list")
        
        # Mengambil nilai dari key tertentu dan mengkonversi ke string
        result = []
        for item in data:
            if isinstance(item, dict):
                if key in item:
                    # Konversi nilai ke string
                    value = str(item[key]) if item[key] is not None else ""
                    result.append(value)
                else:
                    print(f"Warning: Key '{key}' tidak ditemukan dalam salah satu object")
            else:
                print(f"Warning: Item dalam array bukan berupa object/dictionary")
        
        return result
        
    except FileNotFoundError:
        print(f"Error: File '{file_path}' tidak ditemukan")
        return []
    except json.JSONDecodeError as e:
        print(f"Error: Format JSON tidak valid - {e}")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []

# Contoh penggunaan
if __name__ == "__main__":
    # Contoh 1: Mengambil nama tournament
    tournament_names = get_string_array_from_json("tournaments.json", "Tournament_Name")
    print("Tournament Names:")
    for name in tournament_names:
        print(f"- {name}")
    
    print("\n" + "="*50 + "\n")
    
    # Contoh 2: Mengambil lokasi tournament
    locations = get_string_array_from_json("tournaments.json", "Location")
    print("Locations:")
    for location in locations:
        print(f"- {location}")
    
    print("\n" + "="*50 + "\n")
    
    # Contoh 3: Mengambil kategori tournament
    categories = get_string_array_from_json("tournaments.json", "Category")
    print("Categories:")
    for category in categories:
        print(f"- {category}")

# Fungsi tambahan untuk mendapatkan multiple keys sekaligus
def get_multiple_keys_from_json(filename: str, keys: List[str], folder_name: str = "") -> dict:
    """
    Mengambil nilai dari multiple keys sekaligus dari file JSON.
    
    Args:
        filename (str): Nama file JSON
        keys (List[str]): List berisi key-key yang ingin diambil
        folder_name (str, optional): Nama folder tempat file JSON berada
        
    Returns:
        dict: Dictionary dengan key sebagai nama field dan value sebagai array string
    """
    result = {key: [] for key in keys}
    
    try:
        # Menentukan path file dengan folder jika ada
        if folder_name:
            file_path = os.path.join(folder_name, filename)
        else:
            file_path = filename
            
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        if not isinstance(data, list):
            raise TypeError("JSON data harus berupa array/list")
        
        for item in data:
            if isinstance(item, dict):
                for key in keys:
                    if key in item:
                        value = str(item[key]) if item[key] is not None else ""
                        result[key].append(value)
                    else:
                        result[key].append("")  # Tambahkan string kosong jika key tidak ada
        
        return result
        
    except Exception as e:
        print(f"Error: {e}")
        return {key: [] for key in keys}
    
def delete_files_by_extension(folder, extension):
    """
    Menghapus semua file dengan ekstensi tertentu di folder dan subfoldernya.
    
    Args:
        folder (str): Path ke folder utama
        extension (str): Ekstensi file yang akan dihapus (contoh: '.txt')
    """
    # Memastikan ekstensi dimulai dengan titik
    if not extension.startswith('.'):
        extension = '.' + extension
        
    # Melakukan walk melalui folder dan subfolder
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(extension):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f"File dihapus: {file_path}")
                except Exception as e:
                    print(f"Gagal menghapus {file_path}: {str(e)}")   

def add_id_to_json(folder, filename):
    """
    Menambahkan field 'id' ke setiap entri dalam file JSON dengan nilai mulai dari 10 dan bertambah 10.
    
    Args:
        folder (str): Path ke folder yang berisi file JSON
        filename (str): Nama file JSON (termasuk ekstensi .json)
    """
    # Membuat path lengkap ke file JSON
    file_path = os.path.join(folder, filename)
    
    try:
        # Membaca file JSON
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Menambahkan field id ke setiap entri
        for index, item in enumerate(data):
            item['id'] = 10 + (index * 10)
        
        # Menyimpan kembali file JSON dengan format yang rapi
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        
        print(f"Berhasil menambahkan field id ke {file_path}")
    
    except FileNotFoundError:
        print(f"File {file_path} tidak ditemukan")
    except json.JSONDecodeError:
        print(f"File {file_path} bukan file JSON yang valid")
    except Exception as e:
        print(f"Terjadi kesalahan: {str(e)}")                     

# Contoh penggunaan multiple keys
def example_multiple_keys():
    """Contoh penggunaan untuk mengambil multiple keys"""
    keys_to_extract = ["Tournament_Name", "Location", "Country", "Prize_Money"]
    multiple_data = get_multiple_keys_from_json("tournaments.json", keys_to_extract)
    
    print("Multiple Keys Data:")
    for key, values in multiple_data.items():
        print(f"\n{key}:")
        for value in values:
            print(f"  - {value}")