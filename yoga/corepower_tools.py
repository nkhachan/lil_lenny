from agents import function_tool
import requests, os

from dotenv import load_dotenv
load_dotenv()

DUBOCE_CENTER_ID = "ce3fac73-dd61-4f3f-9005-f72202bac828"

import os
import requests
import json


def reload_cognito_jwt():
    """
    Authenticate with AWS Cognito and set the AccessToken as the COREPOWER_JWT environment variable.

    Loads credentials from environment variables:
    - COREPOWER_USERNAME: Cognito username (email)
    - COREPOWER_PASSWORD: Cognito password

    Returns:
        str: The JWT token
    """
    # Load credentials from environment
    username = os.environ["COREPOWER_USERNAME"]
    password = os.environ["COREPOWER_PASSWORD"]

    # Hard-coded values
    client_id = "5l74ttc4m9etagg1jh8n5b8vic"
    region = "us-west-1"
    env_var_name = "COREPOWER_JWT"

    url = f"https://cognito-idp.{region}.amazonaws.com/"
    headers = {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
        "Accept": "*/*"
    }
    payload = {
        "AuthFlow": "USER_PASSWORD_AUTH",
        "AuthParameters": {
            "USERNAME": username,
            "PASSWORD": password
        },
        "ClientId": client_id
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()
    data = response.json()

    # Extract the JWT
    jwt_token = data["AuthenticationResult"]["IdToken"]

    # Set as environment variable
    os.environ[env_var_name] = jwt_token
    print(f"{env_var_name} set successfully.")

    return jwt_token


@function_tool
def get_yoga_classes(
    start_time_utc: str,
    end_time_utc: str,
) -> dict:
    """
    Fetch CorePower Yoga classes between start_time_utc and end_time_utc.
    Returns classes filtered by center ID and category IDs.
    """
    url = "https://api2.corepoweryoga.com/elastic"
    access_token = os.environ["COREPOWER_JWT"]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    body = {
        "query": {
            "bool": {
                "filter": [
                    {
                        "bool": {
                            "should": [
                                {
                                    "range": {
                                        "start_time_utc": {
                                            "gte": start_time_utc,
                                            "lte": end_time_utc
                                        }
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    },
                    {
                        "terms": {
                            "center.id": [DUBOCE_CENTER_ID]
                        }
                    },
                    {
                        "terms": {
                            "class.category.id": [102, 18, 25, 56, 57]
                        }
                    }
                ]
            }
        }
    }

    r = requests.post(url, headers=headers, json=body, timeout=10)
    r.raise_for_status()
    return r.json()

@function_tool
def get_yoga_reservations(
) -> dict:
    """
    Fetch CorePower Yoga reservations.
    """
    url = "https://api2.corepoweryoga.com/reservations"
    access_token = os.environ["COREPOWER_JWT"]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()


@function_tool
def make_yoga_reservation(
    session_id: int,
    center_id: str = DUBOCE_CENTER_ID,
    check_overlap: bool = False,
) -> dict:
    """
    Make a CorePower Yoga reservation for a specific session.

    Args:
        session_id: The ID of the yoga class session to reserve
        center_id: The CorePower center ID (defaults to your center)
        check_overlap: Whether to check for overlapping reservations
    """
    url = "https://api2.corepoweryoga.com/reservation"
    access_token = os.environ["COREPOWER_JWT"]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-api-version": "2.0",
    }

    body = {
        "centerId": center_id,
        "sessionId": session_id,
        "checkOverlap": check_overlap,
    }

    r = requests.post(url, headers=headers, json=body, timeout=10)
    r.raise_for_status()
    return r.json()


@function_tool
def remove_yoga_reservation(
    reservation_id: int,
) -> dict:
    """
    Cancel a CorePower Yoga reservation.

    Args:
        reservation_id: The ID of the reservation to cancel
    """
    url = f"https://api2.corepoweryoga.com/reservation/{reservation_id}"
    access_token = os.environ["COREPOWER_JWT"]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "x-api-version": "2.0",
    }

    r = requests.delete(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()

