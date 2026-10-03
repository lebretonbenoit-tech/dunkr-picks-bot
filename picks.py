import requests
import os
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
ODDS_API_KEY = os.environ["ODDS_API_KEY"]

ODDS_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
ESPN_STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"

def send_message(text):
    url = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage"
    requests.post(url, data={"chat_id": CHANNEL_ID, "text": text})

def get_odds():
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }
    response = requests.get(ODDS_URL, params=params)
    return response.json()

def get_standings():
    response = requests.get(ESPN_STANDINGS_URL)
    data = response.json()
    records = {}
    try:
        for group in data["children"]:
            for entry in group["standings"]["entries"]:
                name = entry["team"]["displayName"]
                wins = next((s["value"] for s in entry["stats"] if s["name"] == "wins"), 0)
                losses = next((s["value"] for s in entry["stats"] if s["name"] == "losses"), 0)
                records[name] = {"wins": wins, "losses": losses}
    except (KeyError, TypeError):
        pass
    return records

def analyze_games(odds_data, standings):
    candidates = []

    for game in odds_data:
        home_team = game.get("home_team")
        away_team = game.get("away_team")
        bookmakers = game.get("bookmakers", [])

        if not bookmakers:
            continue

        outcomes = bookmakers[0]["markets"][0]["outcomes"]
        home_odds = next((o["price"] for o in outcomes if o["name"] == home_team), None)
        away_odds = next((o["price"] for o in outcomes if o["name"] == away_team), None)

        if home_odds is None or away_odds is None:
            continue

        favorite = home_team if home_odds < away_odds else away_team
        underdog = away_team if home_odds < away_odds else home_team
        favorite_odds = min(home_odds, away_odds)
        underdog_odds = max(home_odds, away_odds)

        fav_record = standings.get(favorite, {"wins": 0, "losses": 0})
        dog_record = standings.get(underdog, {"wins": 0, "losses": 0})

        candidates.append({
            "favorite": favorite,
            "underdog": underdog,
            "favorite_odds": favorite_odds,
            "underdog_odds": underdog_odds,
            "fav_wins": fav_record["wins"],
            "fav_losses": fav_record["losses"],
            "dog_wins": dog_record["wins"],
            "dog_losses": dog_record["losses"]
        })

    return candidates

def pick_lock(candidates):
    locks = [c for c in candidates if c["favorite_odds"] < 1.40]
    if not locks:
        return None
    return min(locks, key=lambda c: c["favorite_odds"])

def pick_value(candidates, exclude):
    values = [c for c in candidates if 1.60 <= c["favorite_odds"] <= 2.20 and c != exclude]
    if not values:
        return None
    return values[0]

def pick_longshot(candidates, exclude_list):
    longshots = [c for c in candidates if c["underdog_odds"] >= 3.00 and c not in exclude_list]
    if not longshots:
        return None
    return max(longshots, key=lambda c: c["underdog_odds"])

def format_lock(pick):
    msg = "LOCK OF THE DAY\n\n"
    msg += pick["favorite"] + " to beat " + pick["underdog"] + "\n"
    msg += "Odds: " + str(pick["favorite_odds"]) + "\n\n"
    msg += "Analysis:\n"
    msg += "- " + pick["favorite"] + " record: " + str(int(pick["fav_wins"])) + "-" + str(int(pick["fav_losses"])) + "\n"
    msg += "- " + pick["underdog"] + " record: " + str(int(pick["dog_wins"])) + "-" + str(int(pick["dog_losses"])) + "\n"
    msg += "- Odds reflect a clear favorite"
    return msg

def format_value(pick):
    msg = "VALUE PICK OF THE DAY\n\n"
    msg += pick["favorite"] + " to beat " + pick["underdog"] + "\n"
    msg += "Odds: " + str(pick["favorite_odds"]) + "\n\n"
    msg += "Analysis:\n"
    msg += "- " + pick["favorite"] + " record: " + str(int(pick["fav_wins"])) + "-" + str(int(pick["fav_losses"])) + "\n"
    msg += "- " + pick["underdog"] + " record: " + str(int(pick["dog_wins"])) + "-" + str(int(pick["dog_losses"])) + "\n"
    msg += "- Moderate odds suggest a balanced but favorable spot"
    return msg

def format_longshot(pick):
    msg = "LONGSHOT OF THE DAY\n\n"
    msg += pick["underdog"] + " to beat " + pick["favorite"] + "\n"
    msg += "Odds: " + str(pick["underdog_odds"]) + "\n\n"
    msg += "Analysis:\n"
    msg += "- " + pick["underdog"] + " record: " + str(int(pick["dog_wins"])) + "-" + str(int(pick["dog_losses"])) + "\n"
    msg += "- " + pick["favorite"] + " record: " + str(int(pick["fav_wins"])) + "-" + str(int(pick["fav_losses"])) + "\n"
    msg += "- High odds underdog worth watching"
    return msg

def main():
    odds_data = get_odds()

    if isinstance(odds_data, dict) and odds_data.get("message"):
        send_message("DUNKR PICKS: no odds data available today (" + str(odds_data.get("message")) + ")")
        return

    if not odds_data:
        return

    standings = get_standings()
    candidates = analyze_games(odds_data, standings)

    if not candidates:
        return

    lock = pick_lock(candidates)
    value = pick_value(candidates, lock)
    longshot = pick_longshot(candidates, [lock, value])

    if lock:
        send_message(format_lock(lock))
    if value:
        send_message(format_value(value))
    if longshot:
        send_message(format_longshot(longshot))

if __name__ == "__main__":
    main()
