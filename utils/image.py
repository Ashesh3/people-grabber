import requests, os, json
from utils.config import config


def get_base_name(url):
    return os.path.basename(url).replace(":", "").replace("?", "").replace("&", "").replace("=", "")


def put_image(url):
    image_data = requests.get(url)
    upload_res = requests.post(
        "https://cache.is-inside.me/upload",
        headers={"key": config["IMAGE_UPLOAD_TOKEN"]},
        files={"file": ("image.png", image_data.content)},
    ).json()
    if not upload_res["success"]:
        raise RuntimeError("Error uploading image: " + json.dumps(upload_res))
    basename = get_base_name(upload_res["url"])
    with open(f"./img_cache/{basename}", "wb") as f:
        f.write(image_data.content)
    return upload_res["url"]


def get_image(url):
    basename = get_base_name(url)
    if os.path.isfile(f"./img_cache/{basename}"):
        f = open(f"./img_cache/{basename}", "rb")
        return f.read()
    else:
        image = requests.get(url)
        with open(f"./img_cache/{basename}", "wb") as f:
            f.write(image.content)
        return image.content
