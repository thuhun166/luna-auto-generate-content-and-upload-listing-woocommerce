import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import requests
import csv
import random
import json
from PIL import Image, ImageTk
import os
import mimetypes
import re
from datetime import datetime
import openai

def generate_content_from_openai(image_prompt):
    openai.api_key = ""

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  
            messages=[
                {"role": "user", "content": image_prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        generated_text = response.choices[0].message.content.strip()
        return generated_text
    except Exception as e:
        print(f"Error generating description: {e}")
        return None
    

def read_csv(file_path):
    with open(file_path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def read_web_config():
    with open('web_form.csv', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def get_club_code(product_title):
    title_lower = product_title.lower()
    for club in club_codes:
        if club['club_name'].lower() in title_lower:
            return club
    return None

def get_club_data(product_title, website):
    club_file = os.path.join('club', f"{website.lower()}_club.csv")
    clubs = read_csv(club_file)
    for club in clubs:
        if club['club_name'].lower() in product_title.lower():
            category_ids = club['category_id'].split(',')  
            return {**club, 'category_ids': category_ids}
    return None


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

players = load_players()

websites = {}
for web_config in read_web_config():
    web_name = web_config["web_name"]
    websites[web_name] = {
        "api_url": web_config["api_url"],
        "wp_url": web_config["wp_url"],
        "description_html": web_config["description"],
        "short_description_html": web_config["short_description"]
    }


def save_api_keys(web_name, wp_user, app_password, consumer_key, consumer_secret):
    config = {web_name: {"wp_user": wp_user, "app_password": app_password, "consumer_key": consumer_key, "consumer_secret": consumer_secret}}
    try:
        with open("api_keys.json", "r") as f:
            existing = json.load(f)
    except FileNotFoundError:
        existing = {}
    existing.update(config)
    with open("api_keys.json", "w") as f:
        json.dump(existing, f, indent=4)

def load_api_keys(web_name):
    try:
        with open("api_keys.json", "r") as f:
            config = json.load(f)
            return config.get(web_name)
    except FileNotFoundError:
        messagebox.showerror("Error", "API keys file not found!")
        return None


def get_short_description(website):
    for config in read_web_config():
        if config['web_name'] == website:
            return config['short_description']
    return ""

def extract_season_year(title, is_auto_generate=False):
    match = re.search(r'(\d{2,4})/(\d{2})', title)
    if match:
        part1, part2 = match.groups()

        if len(part1) == 2:
            if is_auto_generate:
                return f"{part1}/{part2}" 
            else:
                year1 = int(part1)
                if year1 <= (datetime.now().year % 100) + 5:
                    full_year1 = 2000 + year1
                else:
                    full_year1 = 1900 + year1
                return f"{full_year1}/{part2}"  #

        elif len(part1) == 4:
            if not is_auto_generate:
                return f"{part1[2:]}/{part2}"
            else:
                return f"{part1[2:]}/{part2}"
    return ""

def get_product_price_and_variations(title, website):
    prices_file = os.path.join('prices', f"{website.lower()}_prices.csv")
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
        variation_list = [map_variation_to_website_size(v.strip()) for v in variations.split(',')] if variations else []
        return best_price['regular_price'], best_price['sale_price'], variation_list
    else:
        return None, None, []

def get_seo_data(website):
    seo_file = os.path.join('seo', f"{website.lower()}_seo.csv")
    seo_data = read_csv(seo_file)
    return random.choice(seo_data)

# === Upload Images
def upload_image_to_wp(file_path, wp_user, app_password, wp_url):
    file_name = os.path.basename(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)
    with open(file_path, 'rb') as f:
        headers = {'Content-Disposition': f'attachment; filename={file_name}', 'Content-Type': mime_type, 'Accept': 'application/json'}
        upload_url = wp_url + "/wp-json/wp/v2/media"
        auth = (wp_user, app_password.replace(" ", ""))
        response = requests.post(upload_url, headers=headers, data=f, auth=auth)
        if response.status_code in [200, 201]:
            return response.json()['source_url']
        else:
            raise Exception(f"Image upload failed: {response.status_code}, {response.text}")

def remove_personalisation_block(html):
    patterns = [
        r'<h2[^>]*>Personalisation<\/h2>.*?(?:<\/ul>|<\/p>)',
        r'<h2[^>]* data-start="\d+" data-end="\d+"[^>]*>Personalisation<\/h2>.*?(?:<\/ul>|<\/p>)',
    ]
    for pattern in patterns:
        html = re.sub(pattern, '', html, flags=re.DOTALL | re.IGNORECASE)
    return html

def upload_image_to_wp(file_path, wp_user, app_password, wp_url):
    file_name = os.path.basename(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)
    with open(file_path, 'rb') as f:
        headers = {
            'Content-Disposition': f'attachment; filename={file_name}',
            'Content-Type': mime_type,
            'Accept': 'application/json'
        }
        upload_url = wp_url + "/wp-json/wp/v2/media"
        auth = (wp_user, app_password.replace(" ", ""))
        response = requests.post(upload_url, headers=headers, data=f, auth=auth)
        if response.status_code in [200, 201]:
            return response.json()['source_url']
        else:
            raise Exception(f"Image upload failed: {response.status_code}, {response.text}")

def select_images():
    global image_paths, image_alts, uploaded_image_urls, images_info
    file_paths = filedialog.askopenfilenames(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.webp")])
    if not file_paths:
        return

    product_title = entry_title.get().strip()
    if not product_title:
        messagebox.showerror("Error", "Please fill in Product Title first!")
        return

    for path in file_paths:
        alt = simpledialog.askstring("Alt Text", f"Alt for {os.path.basename(path)}:", initialvalue=product_title)
        if alt is None or alt.strip() == "": 
            alt = product_title
        image_paths.append(path)  
        image_alts.append(alt)  
        images_info.append({"path": path, "alt": alt}) 

    update_image_display()

def update_image_display():
    for widget in frame_images.winfo_children():
        widget.grid_forget()

    for i, img_info in enumerate(images_info):
        img = Image.open(img_info['path'])
        img.thumbnail((100, 100))
        tk_img = ImageTk.PhotoImage(img)
        lbl = tk.Label(frame_images, image=tk_img)
        lbl.image = tk_img
        lbl.grid(row=i, column=0, padx=5)
        alt_label = tk.Label(frame_images, text=img_info['alt'])
        alt_label.grid(row=i, column=1, padx=5)
        delete_button = tk.Button(frame_images, text="X", command=lambda idx=i: delete_image(idx))
        delete_button.grid(row=i, column=2, padx=5)

def delete_image(idx):
    del image_paths[idx]
    del image_alts[idx]
    del images_info[idx]
    update_image_display()


def auto_generate_sku_tags(*args):
    title = entry_title.get().strip()
    if not title:
        return

    title_lower = title.lower()
    website = website_var.get().strip().upper() 
    season_year = extract_season_year(title, is_auto_generate=True)  
    club = get_club_code(title)  
    if not club:
        return

    shirt_type = 'Shirt'  
    category = 'AD'  
    club_name = club['club_name'].title() 
    club_code = club['name_code']

    if 'away' in title_lower:
        p_type = 'AW'
        shirt_name = 'Away'
    elif 'third' in title_lower:
        p_type = 'TH'
        shirt_name = 'Third'
    elif 'fourth' in title_lower or 'fouth' in title_lower:
        p_type = 'FO'
        shirt_name = 'Fourth'
    elif 'pre match' in title_lower or 'training' in title_lower:
        p_type = 'TN'
        shirt_name = 'Training'
    elif 'goalkeeper' in title_lower:
        p_type = 'GK'
        shirt_name = 'Goalkeeper'
    else:
        p_type = 'HO'
        shirt_name = 'Home'

    if 'kid' in title_lower or 'kids' in title_lower:
        category = 'KD' 
        category_name = 'Kids'
    else:
        category = 'AD'  
        category_name = 'Men'

    if 'kid' in title_lower and 'kit' in title_lower:
        shirt_type = 'Kit'
        category = 'KD'  
    elif 'kid' in title_lower and 'shirt' in title_lower:
        shirt_type = 'Shirt'
        category = 'KD'  
    elif 'men' in title_lower and 'kit' in title_lower:
        shirt_type = 'Kit'
        category = 'AD'  
    elif 'men' in title_lower and 'shirt' in title_lower:
        shirt_type = 'Shirt'
        category = 'AD'  
    elif 'shirt' in title_lower:
        shirt_type = 'Shirt'
        category = 'AD'  
    elif 'kit' in title_lower:
        shirt_type = 'Kit'
        category = 'AD'  

    player_name = 'NO'
    for player in players:
        if player in title_lower:
            player_name = player.upper()  
            break

    prefix = website 
    if player_name != 'No':
        sku = f"{prefix}_{club_code}_{p_type}_{category}_{player_name}_{season_year}"
    else:
        sku = f"{prefix}_{club_code}_{p_type}_{category}_No_{season_year}"

    tags = [club_name, f"{club_name} {season_year}", f"{club_name} {shirt_name} {category_name} {shirt_type} ", f"New Arrivals {season_year}"]
    if player_name != 'No':
        tags.append(player_name.capitalize())

    if player_name != 'No':
        focus_keyphrase = f"{club_name} {season_year} {player_name} {shirt_name} {category_name} Football {shirt_type}"
    else:
        focus_keyphrase = f"{club_name} {season_year} {shirt_name} {category_name} Football {shirt_type}"

    if "football" not in focus_keyphrase.lower():
        focus_keyphrase += " Football"

    entry_sku.delete(0, tk.END)
    entry_sku.insert(0, sku)
    entry_tags.delete(0, tk.END)
    entry_tags.insert(0, ', '.join(tags))
    entry_focus_keyphrase.delete(0, tk.END)
    entry_focus_keyphrase.insert(0, focus_keyphrase)

    regular_price, sale_price, variations = get_product_price_and_variations(title, website)

    if any(player in title_lower for player in players):
        sale_price = float(sale_price) + 10  

    entry_sale_price.delete(0, tk.END)
    entry_sale_price.insert(0, f"{sale_price}")

def map_variation_to_website_size(variation_value):
    size_mapping = {
        "16": "16 (3-4 yrs)",
        "18": "18 (4-5 yrs)",
        "20": "20 (5-6 yrs)",
        "22": "22 (7-8 yrs)",
        "24": "24 (8-9 yrs)",
        "26": "26 (10-11 yrs)",
        "28": "28 (12-13 yrs)",
    }
    
    return size_mapping.get(variation_value, variation_value)


# === Create Product
def create_product():
    title = entry_title.get()
    title_lower = title.lower()
    season_year = extract_season_year(title)
    sku = entry_sku.get()
    focus_keyphrase = entry_focus_keyphrase.get()
    tags = [t.strip() for t in entry_tags.get().split(',') if t.strip()]
    website = website_var.get()

    if not title or not sku:
        messagebox.showerror("Missing Info", "Please fill in Product Title, SKU.")
        return
    
    club = get_club_data(title, website)
    if not club:
        messagebox.showerror("Club Not Found", "Club name not found in club file")
        return

    keys = load_api_keys(website)
    if not keys:
        return

    wp_user = keys["wp_user"]
    app_password = keys["app_password"]
    consumer_key = keys["consumer_key"]
    consumer_secret = keys["consumer_secret"]

    uploaded_image_urls.clear()
    for i, path in enumerate(image_paths):
        try:
            uploaded_url = upload_image_to_wp(path, wp_user, app_password, websites[website]["wp_url"])
            uploaded_image_urls.append(uploaded_url)
        except Exception as e:
            messagebox.showerror("Upload Error", f"Error uploading image {i+1}: {e}")
            return

    if website == "RFS":
        if image_paths:  
            first_image_path = image_paths[0]
            prompt = f"Generate a description for the following image: {first_image_path}"
            
            ai_description = generate_content_from_openai(prompt)

            html_template = websites[website]["description_html"]
            description = html_template.replace("{$formatted_title}", title) \
                                    .replace("{$ai_gen_description}", f"<h2>Description of {title}</h2><p>{ai_description}</p>") \
                                    .replace("{$html_content_about_club}", f"<h2><strong>About {club['club_name']}</strong></h2><p>{club['about_club']}</p>") \
                                    .replace("{$html_content_related_product}", f"<h2><strong>More from {club['club_name']}</strong></h2><p>{club['related_product'].replace('{club_name}', club['club_name']).replace('{title}', title)}</p>") \
                                    .replace("{$year}", season_year)
        else:
            description = websites[website]["description_html"].replace("{$formatted_title}", title).replace("{$year}", season_year)
    else:
        html_template = websites[website]["description_html"]
        description = html_template.replace("{$formatted_title}", title) \
                                .replace("{$html_content_about_club}", f"<h2>Description of {club['club_name']}</h2><p>{club['about_club']}</p>") \
                                .replace("{$html_content_related_product}", f"<h2><strong>Selection of {club['club_name']} Football Club products that may interest you</strong></h2><p>{club['related_product'].replace('{club_name}', club['club_name']).replace('{title}', title)}</p>") \
                                .replace("{$year}", season_year)

    if any(player in title_lower for player in players):
        description = remove_personalisation_block(description)

    short_description = get_short_description(website).replace("{$formatted_title}", title).replace("{club['club_name']}", club['club_name'])

    regular_price, sale_price, variations = get_product_price_and_variations(title, website)
    if not regular_price:
        messagebox.showerror("Error", "Price not found for the given product type.")
        return

    seo = get_seo_data(website)

    images_data = []
    if uploaded_image_urls:
        images_data.append({"src": uploaded_image_urls[0], "alt": image_alts[0]})
        for img_url, alt in zip(uploaded_image_urls[1:], image_alts[1:]):
            images_data.append({"src": img_url, "alt": alt})

    category_ids = club['category_ids']
    sale_price = entry_sale_price.get().strip()  

    if not sale_price:  
        sale_price = float(sale_price)

    data = {
        "name": title,
        "sku": sku,
        "regular_price": regular_price,
        "sale_price": sale_price,
        "description": description,
        "short_description": short_description,
        "categories": [{"id": int(id.strip())} for id in category_ids],
        "tags": [{"name": tag} for tag in tags],
        "images": images_data,
        "meta_data": [
            {"key": "_yoast_wpseo_title", "value": seo['seo_title']},
            {"key": "_yoast_wpseo_metadesc", "value": seo['meta_description']},
            {"key": "_yoast_wpseo_focuskw", "value": focus_keyphrase}
        ]
    }

    if variations:
        data["type"] = "variable"  
        
        data["attributes"] = [
            {
                "id": 3, 
                "position": 0,
                "visible": True,
                "variation": True, 
                "options": variations  
            }
        ]
        
    url = websites[website]["api_url"]
    response = requests.post(url, auth=(consumer_key, consumer_secret), json=data)

    if response.status_code == 201:
        product_id = response.json()['id']

        if variations:
            variation_data = []
            for variation in variations:
                size_number = variation.split()[0]  
                
                variation_sku = f"{sku}_{size_number}"
                
                variation_data.append({
                    "attributes": [{"id": 3, "option": variation}], 
                    "regular_price": regular_price,
                    "sale_price": sale_price,
                    "sku": variation_sku  
                })

            batch_data = {
                "create": variation_data 
            }

            variations_url = f"{websites[website]['api_url']}/{product_id}/variations/batch"
            variation_response = requests.post(variations_url, auth=(consumer_key, consumer_secret), json=batch_data)

            if variation_response.status_code in [201, 200]:
                messagebox.showinfo("Success", f"Product '{title}' created with ID: {product_id}")
            else:
                messagebox.showerror("Error", f"Failed to create variations: {variation_response.status_code}\n{variation_response.text}")
    else:
        messagebox.showerror("Error", f"Failed: {response.status_code}\n{response.text}")



# === GUI
root = tk.Tk()
root.title("WooCommerce Listing App")

website_var = tk.StringVar(value="")
tk.Label(root, text="Website:").pack()
website_dropdown = tk.OptionMenu(root, website_var, *websites)
website_dropdown.pack()

def load_api_fields(website):
    keys = load_api_keys(website)
    if keys:
        wp_user_var.set(keys["wp_user"])
        app_password_var.set(keys["app_password"])
        consumer_key_var.set(keys["consumer_key"])
        consumer_secret_var.set(keys["consumer_secret"])


website_var.trace("w", lambda *args: load_api_fields(website_var.get()))

form = tk.Frame(root)
form.pack(pady=10)

tk.Label(form, text="Product Title").grid(row=0, column=0, sticky="e")
entry_title = tk.Entry(form, width=50)
entry_title.grid(row=0, column=1)

tk.Label(form, text="SKU").grid(row=1, column=0, sticky="e")
entry_sku = tk.Entry(form, width=50)
entry_sku.grid(row=1, column=1)

tk.Label(form, text="Tags (comma)").grid(row=2, column=0, sticky="e")
entry_tags = tk.Entry(form, width=50)
entry_tags.grid(row=2, column=1)

tk.Label(form, text="Focus Keyphrase").grid(row=3, column=0, sticky="e")
entry_focus_keyphrase = tk.Entry(form, width=50)
entry_focus_keyphrase.grid(row=3, column=1)

tk.Label(form, text="Sale Price").grid(row=4, column=0, sticky="e")
entry_sale_price = tk.Entry(form, width=50)
entry_sale_price.grid(row=4, column=1)

tk.Label(root, text="WP User").pack()
wp_user_var = tk.StringVar()
entry_wp_user = tk.Entry(root, textvariable=wp_user_var)
entry_wp_user.pack(pady=5)

tk.Label(root, text="App Password").pack()
app_password_var = tk.StringVar()
entry_app_password = tk.Entry(root, textvariable=app_password_var)
entry_app_password.pack(pady=5)

tk.Label(root, text="Consumer Key").pack()
consumer_key_var = tk.StringVar()
entry_consumer_key = tk.Entry(root, textvariable=consumer_key_var)
entry_consumer_key.pack(pady=5)

tk.Label(root, text="Consumer Secret").pack()
consumer_secret_var = tk.StringVar()
entry_consumer_secret = tk.Entry(root, textvariable=consumer_secret_var)
entry_consumer_secret.pack(pady=5)

tk.Button(root, text="Select Images", command=select_images).pack(pady=5)
frame_images = tk.Frame(root)
frame_images.pack()

tk.Button(root, text="Create Product", command=create_product, bg="green", fg="white").pack(pady=10)

image_paths = []
image_alts = []
uploaded_image_urls = []
images_info = []
entry_title.bind("<KeyRelease>", auto_generate_sku_tags)

root.mainloop()
