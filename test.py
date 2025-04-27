import requests

consumer_key = 'ck_0e14050d8a05d060a837a24fcec2c081399ac418'
consumer_secret = 'cs_4e19cc17539f38edbc18461238760630930aae09'

url = "https://footballkitsdeals.com/wp-json/wc/v3/products/16156/variations"

variation_data = [
    {
        "attributes": [{"id": 3, "option": "16 (3-4 yrs)"}],  
        "regular_price": "19.99",
    }
]

variation_response = requests.post(url, auth=(consumer_key, consumer_secret), json=variation_data)

if variation_response.status_code == 201:
    print("Variations created successfully.")
else:
    print(f"Failed to create variations: {variation_response.status_code}")
    print(variation_response.text)  
