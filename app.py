from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests, time

app = Flask(__name__)
app.secret_key = "anoma-secret"

API_BASE = "https://api.prod.testnet.anoma.net/api/v1"

# Track unique visitors by IP
unique_visitors = set()


@app.before_request
def track_visitors():
    ip = request.remote_addr
    if ip not in unique_visitors:
        unique_visitors.add(ip)


def fetch_with_retry(url, headers, retries=5, delay=2):
    """
    Fetch data from API with retry and error handling.
    Returns JSON or error dict. If fails after retries, returns None.
    """
    messages = []
    for attempt in range(retries):
        resp = requests.get(url, headers=headers)

        if resp.status_code == 200:
            try:
                return resp.json(), messages
            except ValueError:
                messages.append("Invalid JSON response from server.")
                return None, messages

        elif resp.status_code == 401:
            return {"error": "invalid_token"}, messages

        else:
            messages.append(f"Attempt {attempt+1}/{retries} failed with status {resp.status_code}")
            time.sleep(delay)

    return None, messages


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        token = request.form["bearer"]
        headers = {"Authorization": f"Bearer {token}"}

        # Validate token with retry (5x)
        user_data, messages = fetch_with_retry(f"{API_BASE}/user", headers, retries=5)

        if not user_data:
            return render_template("home.html", error="⚠️ Server error after multiple retries.", logs=messages)

        if user_data.get("error") == "invalid_token":
            return render_template("home.html", error="❌ Your Token is Invalid", logs=messages)

        # Valid token → save to session
        session["bearer"] = token
        return redirect(url_for("stats"))

    return render_template("home.html")


@app.route("/stats")
def stats():
    bearer = session.get("bearer")
    if not bearer:
        return redirect(url_for("home"))

    headers = {"Authorization": f"Bearer {bearer}", "Accept": "*/*"}

    # Fetch user data
    user_data, _ = fetch_with_retry(f"{API_BASE}/user", headers, retries=5)
    if not user_data or user_data.get("error") == "invalid_token":
        return redirect(url_for("home"))

    # Fetch garapon data
    garapon_data, _ = fetch_with_retry(f"{API_BASE}/garapon", headers, retries=5)
    if not garapon_data or garapon_data.get("error") == "invalid_token":
        return redirect(url_for("home"))

    # Count stats
    stats = {"white": 0, "blue": 0, "red": 0, "gold": 0}
    for c in garapon_data.get("coupons", []):
        if c["prize_amount"] == 100:
            stats["white"] += 1
        elif c["prize_amount"] == 2500:
            stats["blue"] += 1
        elif c["prize_amount"] == 10000:
            stats["red"] += 1
        elif c["prize_amount"] == 50000:
            stats["gold"] += 1

    total = sum(stats.values())
    return render_template(
        "stats.html",
        user=user_data,
        stats=stats,
        total=total,
        visitors=len(unique_visitors)
    )


if __name__ == "__main__":
    from waitress import serve
    import os
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Server running on http://127.0.0.1:{port}")
    serve(app, host="0.0.0.0", port=port)
