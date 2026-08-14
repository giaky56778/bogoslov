import importlib
import os
import tomllib
from dotenv import load_dotenv

load_dotenv()

with open("config.toml", "rb") as f:
    config = tomllib.load(f)

lang = os.environ.get("LANG_CORPUS", "chu")
langmod = importlib.import_module(f"lang_{lang}")

print(f"Loading for LANG_CORPUS={lang}...")
ms2color = langmod.ms2color
ms2source = langmod.ms2source
udpipe_model = langmod.udpipe_model
strans_models = langmod.strans_models
examples = langmod.examples

# DATABASE_URL = "sqlite+pysqlite:///:memory:"
# DATABASE_URL = "postgresql://bogoslov:xxxxxx@localhost:5732/bogoslov

DATABASE_URL = "postgresql://bogoslov:xxxxxx@db:5432/bogoslov"

static_path = "/corpora/"
host = os.environ.get("DEPLOY_HOST", "127.0.0.1")
port = int(os.environ.get("DEPLOY_PORT", "8780"))
base_url = f"http://{host}:{port}"

ns = {"tei": "http://www.tei-c.org/ns/1.0"}
unit = "lg"

# usability
threshold_lcs = config["threshold_lcs"]
threshold_ngram = config["threshold_ngram"]
threshold_strans = config["threshold_strans"]
threshold_bm25 = config["threshold_bm25"]

# actually lemmatizer
stemmer = config["stemmer"]


# ngrams, see app_ngram.py#39
ng_min = 1
ng_default = 3
ng_max = 3

debug = config["debug"]



API_ADDRESS='/api/v1'
STRANS_TOOLPIT=langmod.strans_toolpit
ALGO_TOOLPIT={
    "regex": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Quisque porta, nunc quis lacinia aliquet, magna neque porttitor elit, vitae pulvinar ipsum turpis in sem. In ut maximus mauris. Morbi ligula velit, mattis ac tortor id, lacinia imperdiet eros. Cras dapibus non mauris quis luctus. Sed rutrum porttitor odio ut congue. Morbi pulvinar risus varius faucibus convallis. Phasellus gravida ante at ligula iaculis tristique. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Curabitur pellentesque quam in bibendum rhoncus. ",
    "lcs": "In vestibulum eleifend eros. Fusce volutpat sapien suscipit magna consectetur, congue auctor libero finibus. Quisque tortor erat, finibus sed tempus sollicitudin, vestibulum vitae leo. Vivamus at convallis mauris. Nullam tempor velit nisl. Nullam et elit tincidunt dui accumsan molestie eget at purus. Vestibulum pulvinar sodales leo, non varius metus imperdiet sit amet. Donec id mi nec nibh porta mollis. ",
    "ngram": "Integer efficitur nibh augue. Morbi diam orci, aliquet ut nulla a, lacinia tempor est. Proin vel vestibulum nisi, et congue mauris. Integer euismod massa dui, quis pretium ex faucibus eu. Nam auctor, dolor eu imperdiet fringilla, dui massa dictum neque, id fringilla ex eros eu purus. Maecenas eget ullamcorper dui, vitae lacinia lacus. Nulla mollis, metus sit amet finibus ultricies, elit lacus mattis est, sed venenatis mauris ex eget nunc. Mauris dictum tincidunt orci eleifend posuere. Nunc fringilla laoreet iaculis. Fusce vitae felis suscipit, semper neque in, congue justo. Donec a sapien dolor. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam erat volutpat. ",
    "bm25": "Praesent cursus imperdiet blandit. Phasellus non ex luctus, condimentum eros efficitur, ornare diam. Duis ex magna, convallis a venenatis sed, venenatis non dui. Mauris aliquet, tellus ut cursus tristique, urna leo interdum tortor, ac hendrerit dui sem eget lectus. Morbi vulputate congue urna, vel bibendum nunc mattis sed. Curabitur eu euismod magna. Sed at lectus bibendum, ornare justo id, venenatis ante. Cras vulputate non dui nec blandit. Vestibulum blandit dapibus erat, eget bibendum justo aliquam a. Donec fringilla at tortor id sollicitudin. "
}

# algo that might not return an entire line as output
ALGO_NOT_FULL_LINE=[
    'lcs'
]

LIMIT_RESULT=25
LINE_EXTRACT_UPPER=20   
LINE_EXTRACT_LOWER=3

TTL = 1200 # [seconds] search result cache lifetime
TTL_CHECKED = 300 # [seconds] purge check interval
MAX_CACHE_SIZE = 1024

# Frontend URL
raw_frontend_url = os.environ.get("FRONTEND_URL")
if not raw_frontend_url:
    raise ValueError("FRONTEND_URL is not define in .env file")
FRONTEND_URL = raw_frontend_url

# Allowed origin (CORS)
raw_origins = os.environ.get("ALLOWED_ORIGINS")
if not raw_origins:
    raise ValueError("ALLOWED_ORIGINS is not define in .env file")
ALLOWED_ORIGINS = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
