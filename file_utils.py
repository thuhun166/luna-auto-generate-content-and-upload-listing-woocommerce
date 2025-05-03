import csv
import os
import random
import json
from tkinter import messagebox

def read_csv(file_path):
    with open(file_path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def read_web_config():
    return read_csv('web_form.csv')

def load_club_codes():
    club_codes = []
    if os.path.exists('club_code.csv'):
        with open('club_code.csv', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                club_codes.append({
                    'club_name': row['club_name'].lower(),
                    'name_code': row['name_code']
                })
    return club_codes

club_codes = load_club_codes()

def get_club_code(product_title):
    title_lower = product_title.lower()
    for club in club_codes:
        if club['club_name'].lower() in title_lower:
            return club
    return None

def get_club_data(product_title, website):
    club_file = os.path.join('club', f"{website.lower()}_club.csv")
    if not os.path.exists(club_file):
        return None
    clubs = read_csv(club_file)
    for club in clubs:
        if club['club_name'].lower() in product_title.lower():
            category_ids = club['category_id'].split(',')
            return {**club, 'category_ids': category_ids}
    return None

def load_players():
    players_file = 'players.csv'
    players = []
    if os.path.exists(players_file):
        with open(players_file, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    players.append(row[0].lower())
    return players

def get_product_price_and_variations(title, website):
    prices_file = os.path.join('prices', f"{website.lower()}_prices.csv")
    if not os.path.exists(prices_file):
        return None, None, []
    prices = read_csv(prices_file)
    title_words = set(title.lower().split())
    best_match_score = 0
    best_price = None
    for price_entry in prices:
        product_type_words = set(price_entry['product_type'].lower().split())
        match_score = len(title_words.intersection(product_type_words))
        if match_score > best_match_score:
            best_match_score = match_score
            best_price = price_entry
    if best_price:
        variations = best_price.get('variations', '')
        variation_list = variations.split(',') if variations else []
        return best_price['regular_price'], best_price['sale_price'], variation_list
    else:
        return None, None, []

def get_seo_data(website):
    seo_file = os.path.join('seo', f"{website.lower()}_seo.csv")
    if not os.path.exists(seo_file):
        return {"seo_title": "Default Title", "meta_description": "Default Description"}
    seo_data = read_csv(seo_file)
    return random.choice(seo_data)

def get_short_description(website):
    for config in read_web_config():
        if config['web_name'] == website:
            return config['short_description']
    return ""

def load_api_keys(web_name):
    try:
        with open("api_keys.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get(web_name)
    except FileNotFoundError:
        messagebox.showerror("Error", "API keys file not found!")
        return None

def save_api_keys(web_name, wp_user, app_password, consumer_key, consumer_secret):
    config = {web_name: {
        "wp_user": wp_user,
        "app_password": app_password,
        "consumer_key": consumer_key,
        "consumer_secret": consumer_secret
    }}
    try:
        with open("api_keys.json", "r", encoding="utf-8") as f:
            existing = json.load(f)
    except FileNotFoundError:
        existing = {}
    existing.update(config)
    with open("api_keys.json", "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4)
