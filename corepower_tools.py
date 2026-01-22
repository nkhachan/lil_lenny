from agents import function_tool
import requests, os

from dotenv import load_dotenv
load_dotenv()

@function_tool
def get_corepower_reservations(
) -> dict:
    """
    Fetch CorePower Yoga reservations.
    """
    url = "https://api2.corepoweryoga.com/reservations"
    access_token = os.environ["COREPOWER_KEY"]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()

#print(get_corepower_reservations())