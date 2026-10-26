import os

from dotenv import load_dotenv

from app import create_app

# WEBSITE_HOSTNAME is always set by App Service, RUNNING_IN_PRODUCTION is set by the deployed host
RUNNING_ON_AZURE = os.getenv("WEBSITE_HOSTNAME") is not None or os.getenv("RUNNING_IN_PRODUCTION") is not None

if not RUNNING_ON_AZURE:
    load_dotenv(override=False)

app = create_app()
