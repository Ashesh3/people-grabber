import requests, os, json
from utils.config import config
import boto3
import random
import string
from requests.exceptions import ConnectionError
from pathlib import Path


Path("./img_cache").mkdir(parents=True, exist_ok=True)
s3_client = boto3.client(
    service_name="s3",
    endpoint_url="https://gateway.ap1.storjshare.io",
    region_name="ap-southeast-1",
    aws_access_key_id=config["AWS_ACCESS_KEY"],
    aws_secret_access_key=config["AWS_SECRET_KEY"],
)


def get_id():
    return "".join([random.choice(string.ascii_letters + string.digits) for _ in range(10)])


def get_base_name(url):
    return os.path.basename(url).replace(":", "").replace("?", "").replace("&", "").replace("=", "")


def put_image(url) -> str:
    if not url:
        return ""
    image_data = requests.get(url, verify=False)
    image_key = get_id()
    basename = f"{image_key}.png"
    s3_client.put_object(Body=image_data.content, Bucket="images", Key=f"{image_key}.png")
    with open(f"./img_cache/{basename}", "wb") as f:
        f.write(image_data.content)
    return config["IMAGE_URL_PREFIX"] + basename


def get_image(url):
    basename = get_base_name(url)
    if os.path.isfile(f"./img_cache/{basename[:100]}"):
        f = open(f"./img_cache/{basename[:100]}", "rb")
        return f.read()
    else:
        try:
            image = requests.get(url, verify=False)
        except Exception:
            return False
        if image.status_code != 200:
            return False
        try:
            with open(f"./img_cache/{basename[:100]}", "wb") as f:
                f.write(image.content)
            return image.content
        except OSError:
            return False
