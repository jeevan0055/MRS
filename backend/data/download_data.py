import os
import zipfile
import requests

ML_URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def download_and_extract():
    zip_path = os.path.join(DATA_DIR, "ml-latest-small.zip")
    if not os.path.exists(zip_path):
        print("Downloading MovieLens dataset...")
        response = requests.get(ML_URL, stream=True)
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    print("Extracting dataset...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(DATA_DIR)

    print("Done!")


if __name__ == "__main__":
    download_and_extract()
