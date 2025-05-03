import re
import random
from datetime import datetime
import openai
from file_utils import get_club_code, get_product_price_and_variations, load_players

players = load_players()

def extract_season_year(title, is_auto_generate=False):
    match = re.search(r'(\d{2,4})/(\d{2})', title)
    if match:
        part1, part2 = match.groups()
        if len(part1) == 2:
            if is_auto_generate:
                return f"{part1}/{part2}"
            else:
                year1 = int(part1)
                full_year1 = 2000 + year1 if year1 <= (datetime.now().year % 100) + 5 else 1900 + year1
                return f"{full_year1}/{part2}"
        elif len(part1) == 4:
            return f"{part1[2:]}/{part2}"
    return ""

def map_variation_to_website_size(value):
    mapping = {
        "16": "16 (3-4 yrs)",
        "18": "18 (4-5 yrs)",
        "20": "20 (5-6 yrs)",
        "22": "22 (7-8 yrs)",
        "24": "24 (8-9 yrs)",
        "26": "26 (10-11 yrs)",
        "28": "28 (12-13 yrs)",
    }
    return mapping.get(value, value)

def auto_generate_sku_tags(entry_title, entry_sku, entry_tags, entry_focus_keyphrase, entry_sale_price, website):
    title = entry_title.get().strip()
    if not title:
        return

    title_lower = title.lower()
    website = website.strip().upper()
    season_year = extract_season_year(title, is_auto_generate=True)
    club = get_club_code(title)
    if not club:
        return

    shirt_type = 'Shirt'
    category = 'AD'
    club_name = club['club_name'].title()
    club_code = club['name_code']

    if 'away' in title_lower:
        p_type, shirt_name = 'AW', 'Away'
    elif 'third' in title_lower:
        p_type, shirt_name = 'TH', 'Third'
    elif 'fourth' in title_lower or 'fouth' in title_lower:
        p_type, shirt_name = 'FO', 'Fourth'
    elif 'pre match' in title_lower or 'training' in title_lower:
        p_type, shirt_name = 'TN', 'Training'
    elif 'goalkeeper' in title_lower:
        p_type, shirt_name = 'GK', 'Goalkeeper'
    else:
        p_type, shirt_name = 'HO', 'Home'

    if 'kid' in title_lower:
        category = 'KD'
        category_name = 'Kids'
    else:
        category = 'AD'
        category_name = 'Men'

    if 'kit' in title_lower:
        shirt_type = 'Kit'
    elif 'shirt' in title_lower:
        shirt_type = 'Shirt'

    player_name = 'No'
    for player in players:
        if player in title_lower:
            player_name = player.upper()
            break

    prefix = website
    sku = f"{prefix}_{club_code}_{p_type}_{category}_{player_name}_{season_year}"
    tags = [
        club_name,
        f"{club_name} {season_year}",
        f"{club_name} {shirt_name} {category_name} {shirt_type}",
        f"New Arrivals {season_year}"
    ]
    if player_name != 'No':
        tags.append(player_name.capitalize())

    focus_keyphrase = (
        f"{club_name} {season_year} {player_name} {shirt_name} {category_name} Football {shirt_type}"
        if player_name != 'No'
        else f"{club_name} {season_year} {shirt_name} {category_name} Football {shirt_type}"
    )
    if "football" not in focus_keyphrase.lower():
        focus_keyphrase += " Football"

    regular_price, sale_price, _ = get_product_price_and_variations(title, website)
    if any(p in title_lower for p in players):
        try:
            sale_price = float(sale_price) + 10
        except:
            pass

    # Set to GUI
    entry_sku.delete(0, 'end')
    entry_sku.insert(0, sku)
    entry_tags.delete(0, 'end')
    entry_tags.insert(0, ', '.join(tags))
    entry_focus_keyphrase.delete(0, 'end')
    entry_focus_keyphrase.insert(0, focus_keyphrase)
    entry_sale_price.delete(0, 'end')
    entry_sale_price.insert(0, str(sale_price))

def generate_content_from_openai(image_prompt):
    openai.api_key = ""  

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": image_prompt}],
            temperature=0.7,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI error: {e}")
        return None
