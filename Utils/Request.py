import logging
import pathlib
import shutil

import requests

from Config.Constants import APPLICATION_CACHE_DIR
from Utils.Settings import Preferences


def cached_image(url: str, cache_file: str,  cache_dir: str = None) -> str:
    if cache_dir is None:
        cache_dir = Preferences.get("application_cache_dir", APPLICATION_CACHE_DIR, str)

    file = pathlib.Path(cache_dir) / cache_file
    if not file.exists():
        logging.getLogger('cached_image').debug(f'Requesting non-existing file: {url}')
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(file, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
        else:
            logging.getLogger('cached_image').error(f"Failed fetching file for: {url}")
    else:
        # logging.getLogger('cached_image').debug(f'Cache hit for file {cache_file}')
        pass
    return str(file)