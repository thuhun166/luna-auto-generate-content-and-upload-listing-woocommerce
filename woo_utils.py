import tkinter.messagebox as messagebox
from uploader import upload_image_to_wp, upload_product, upload_variations
from generator import extract_season_year, generate_content_from_openai, map_variation_to_website_size
from file_utils import (
    get_club_data,
    get_product_price_and_variations,
    get_seo_data,
    get_short_description,
    read_web_config,
    load_api_keys,
    load_players
)

personalisation_forms = {
    "RFS": "11700",
    "FSS": "11700",
    "XYZ": "11700"
}

def remove_personalisation_block(html):
    import re
    patterns = [
        r'<h2[^>]*>Personalisation<\/h2>.*?(?:<\/ul>|<\/p>)',
        r'<h2[^>]* data-start="\d+" data-end="\d+"[^>]*>Personalisation<\/h2>.*?(?:<\/ul>|<\/p>)',
    ]
    for pattern in patterns:
        html = re.sub(pattern, '', html, flags=re.DOTALL | re.IGNORECASE)
    return html

def create_product(entry_title, entry_sku, entry_tags, entry_focus_keyphrase, entry_sale_price,
                   website, wp_user, app_password, consumer_key, consumer_secret,
                   image_paths, image_alts, uploaded_image_urls, websites):

    title = entry_title.get().strip()
    title_lower = title.lower()
    season_year = extract_season_year(title)
    sku = entry_sku.get().strip()
    tags = [t.strip() for t in entry_tags.get().split(',') if t.strip()]
    focus_keyphrase = entry_focus_keyphrase.get().strip()
    sale_price = entry_sale_price.get().strip()

    if not title or not sku:
        messagebox.showerror("Missing Info", "Please fill in Product Title and SKU.")
        return

    club = get_club_data(title, website)
    if not club:
        messagebox.showerror("Club Not Found", "Cannot find club data.")
        return

    try:
        for path in image_paths:
            url = upload_image_to_wp(path, wp_user, app_password, websites[website]["wp_url"])
            uploaded_image_urls.append(url)
    except Exception as e:
        messagebox.showerror("Upload Error", f"Image upload failed: {e}")
        return

    html_template = websites[website]["description_html"]
    if website == "RFS" and image_paths:
        prompt = f"Generate a description for the following image: {image_paths[0]}"
        ai_description = generate_content_from_openai(prompt)
        ai_block = f"<h2>Description of {title}</h2><p>{ai_description}</p>" if ai_description else ""
        description = html_template.replace("{$formatted_title}", title) \
            .replace("{$ai_gen_description}", ai_block) \
            .replace("{$html_content_about_club}", f"<h2><strong>About {club['club_name']}</strong></h2><p>{club['about_club']}</p>") \
            .replace("{$html_content_related_product}", f"<h2><strong>More from {club['club_name']}</strong></h2><p>{club['related_product'].replace('{club_name}', club['club_name']).replace('{title}', title)}</p>") \
            .replace("{$year}", season_year)
    else:
        description = html_template.replace("{$formatted_title}", title) \
            .replace("{$html_content_about_club}", f"<h2>Description of {club['club_name']}</h2><p>{club['about_club']}</p>") \
            .replace("{$html_content_related_product}", f"<h2><strong>Selection of {club['club_name']} Football Club products that may interest you</strong></h2><p>{club['related_product'].replace('{club_name}', club['club_name']).replace('{title}', title)}</p>") \
            .replace("{$year}", season_year)

    player_names = load_players()
    has_player = any(p in title_lower for p in player_names)
    if has_player:
        description = remove_personalisation_block(description)

    short_description = get_short_description(website).replace("{$formatted_title}", title).replace("{club['club_name']}", club['club_name'])

    regular_price, fallback_sale_price, variations_raw = get_product_price_and_variations(title, website)
    if not regular_price:
        messagebox.showerror("Error", "Cannot find price data.")
        return

    try:
        final_sale_price = sale_price if sale_price else fallback_sale_price
    except:
        final_sale_price = fallback_sale_price

    seo = get_seo_data(website)
    category_ids = club['category_ids']
    images_data = [{"src": url, "alt": alt} for url, alt in zip(uploaded_image_urls, image_alts)]

    meta_data = [
        {"key": "_yoast_wpseo_title", "value": seo['seo_title']},
        {"key": "_yoast_wpseo_metadesc", "value": seo['meta_description']},
        {"key": "_yoast_wpseo_focuskw", "value": focus_keyphrase}
    ]

    badge_id = club.get('badge_id')
    global_forms = []

    if not has_player:
        personalisation_id = personalisation_forms.get(website)
        if personalisation_id:
            global_forms.append(personalisation_id)

    if badge_id:
        if ',' in badge_id:
            global_forms.extend([bid.strip() for bid in badge_id.split(',')])
        else:
            global_forms.append(badge_id)

    if global_forms:
        meta_data.append({
            "key": "tm_meta_cpf",
            "value": {
                "global_forms": global_forms,
                "exclude": "1"
            }
        })

    product_data = {
        "name": title,
        "sku": sku,
        "regular_price": regular_price,
        "sale_price": final_sale_price,
        "description": description,
        "short_description": short_description,
        "categories": [{"id": int(id.strip())} for id in category_ids],
        "tags": [{"name": tag} for tag in tags],
        "images": images_data,
        "meta_data": meta_data
    }

    # === Variations
    variations = [map_variation_to_website_size(v.strip()) for v in variations_raw]
    if variations:
        product_data["type"] = "variable"
        product_data["attributes"] = [{
            "id": 3,
            "position": 0,
            "visible": True,
            "variation": True,
            "options": variations
        }]

    try:
        product_id = upload_product(product_data, websites[website]["api_url"], consumer_key, consumer_secret)
    except Exception as e:
        messagebox.showerror("Upload Error", f"Product upload failed:\n{e}")
        return

    if variations:
        try:
            variation_data = []
            for variation in variations:
                size_number = variation.split()[0]
                variation_sku = f"{sku}_{size_number}"
                variation_data.append({
                    "attributes": [{"id": 3, "option": variation}],
                    "regular_price": regular_price,
                    "sale_price": final_sale_price,
                    "sku": variation_sku
                })
            upload_variations(product_id, variation_data, websites[website]["api_url"], consumer_key, consumer_secret)
        except Exception as e:
            messagebox.showerror("Variation Error", f"Variation creation failed:\n{e}")
            return

    messagebox.showinfo("Success", f"Product '{title}' created with ID: {product_id}")
