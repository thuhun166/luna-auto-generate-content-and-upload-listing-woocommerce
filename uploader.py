import os
import requests
import mimetypes

def upload_image_to_wp(file_path, wp_user, app_password, wp_url):
    file_name = os.path.basename(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)

    with open(file_path, 'rb') as f:
        headers = {
            'Content-Disposition': f'attachment; filename={file_name}',
            'Content-Type': mime_type,
            'Accept': 'application/json'
        }
        upload_url = f"{wp_url}/wp-json/wp/v2/media"
        auth = (wp_user, app_password.strip())

        response = requests.post(upload_url, headers=headers, data=f, auth=auth)
        if response.status_code in [200, 201]:
            return response.json()['source_url']
        else:
            raise Exception(f"Image upload failed: {response.status_code}, {response.text}")

def upload_product(data, api_url, consumer_key, consumer_secret):
    response = requests.post(
        api_url,
        auth=(consumer_key, consumer_secret),
        json=data
    )
    if response.status_code == 201:
        return response.json()['id']
    else:
        raise Exception(f"Product upload failed: {response.status_code}, {response.text}")

def upload_variations(product_id, variations_data, api_url, consumer_key, consumer_secret):
    variations_url = f"{api_url}/{product_id}/variations/batch"
    response = requests.post(
        variations_url,
        auth=(consumer_key, consumer_secret),
        json={"create": variations_data}
    )
    if response.status_code in [200, 201]:
        return response.json()
    else:
        raise Exception(f"Variations upload failed: {response.status_code}, {response.text}")
