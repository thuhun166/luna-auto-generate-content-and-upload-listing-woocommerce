import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from generator import auto_generate_sku_tags
from uploader import upload_image_to_wp
from woo_utils import create_product, load_api_keys
from file_utils import read_web_config

# === GLOBAL STATE ===
image_paths = []
image_alts = []
uploaded_image_urls = []
images_info = []
websites = {}

def load_websites():
    for web_config in read_web_config():
        web_name = web_config["web_name"]
        websites[web_name] = {
            "api_url": web_config["api_url"],
            "wp_url": web_config["wp_url"],
            "description_html": web_config["description"],
            "short_description": web_config["short_description"]
        }
    return websites

def select_images(entry_title, frame_images):
    product_title = entry_title.get().strip()
    if not product_title:
        messagebox.showerror("Error", "Please fill in Product Title first!")
        return

    file_paths = filedialog.askopenfilenames(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.webp")])
    if not file_paths:
        return

    for path in file_paths:
        alt = simpledialog.askstring("Alt Text", f"Alt for {path}:", initialvalue=product_title)
        alt = alt.strip() if alt else product_title
        image_paths.append(path)
        image_alts.append(alt)
        images_info.append({"path": path, "alt": alt})

    update_image_display(frame_images)

def update_image_display(frame_images):
    for widget in frame_images.winfo_children():
        widget.grid_forget()

    for i, img_info in enumerate(images_info):
        from PIL import Image, ImageTk
        img = Image.open(img_info['path'])
        img.thumbnail((100, 100))
        tk_img = ImageTk.PhotoImage(img)
        lbl = tk.Label(frame_images, image=tk_img)
        lbl.image = tk_img
        lbl.grid(row=i, column=0, padx=5)
        alt_label = tk.Label(frame_images, text=img_info['alt'])
        alt_label.grid(row=i, column=1, padx=5)
        delete_button = tk.Button(frame_images, text="X", command=lambda idx=i: delete_image(idx, frame_images))
        delete_button.grid(row=i, column=2, padx=5)

def delete_image(idx, frame_images):
    del image_paths[idx]
    del image_alts[idx]
    del images_info[idx]
    update_image_display(frame_images)

def launch_app():
    global websites
    websites = load_websites()

    root = tk.Tk()
    root.title("WooCommerce Listing App")

    website_var = tk.StringVar(value="")

    tk.Label(root, text="Website:").pack()
    website_dropdown = tk.OptionMenu(root, website_var, *websites)
    website_dropdown.pack()

    # API Key Fields
    wp_user_var = tk.StringVar()
    app_password_var = tk.StringVar()
    consumer_key_var = tk.StringVar()
    consumer_secret_var = tk.StringVar()

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

    # API fields
    tk.Label(root, text="WP User").pack()
    entry_wp_user = tk.Entry(root, textvariable=wp_user_var)
    entry_wp_user.pack(pady=5)

    tk.Label(root, text="App Password").pack()
    entry_app_password = tk.Entry(root, textvariable=app_password_var)
    entry_app_password.pack(pady=5)

    tk.Label(root, text="Consumer Key").pack()
    entry_consumer_key = tk.Entry(root, textvariable=consumer_key_var)
    entry_consumer_key.pack(pady=5)

    tk.Label(root, text="Consumer Secret").pack()
    entry_consumer_secret = tk.Entry(root, textvariable=consumer_secret_var)
    entry_consumer_secret.pack(pady=5)

    # Image Select
    frame_images = tk.Frame(root)
    frame_images.pack()

    tk.Button(root, text="Select Images", command=lambda: select_images(entry_title, frame_images)).pack(pady=5)

    # Create Product Button
    tk.Button(
        root,
        text="Create Product",
        bg="green",
        fg="white",
        command=lambda: create_product(
            entry_title, entry_sku, entry_tags, entry_focus_keyphrase, entry_sale_price,
            website_var.get(), wp_user_var.get(), app_password_var.get(),
            consumer_key_var.get(), consumer_secret_var.get(),
            image_paths, image_alts, uploaded_image_urls, websites
        )
    ).pack(pady=10)

    # Auto-generate SKU
    entry_title.bind("<KeyRelease>", lambda e: auto_generate_sku_tags(
        entry_title, entry_sku, entry_tags, entry_focus_keyphrase,
        entry_sale_price, website_var.get()
    ))

    root.mainloop()
