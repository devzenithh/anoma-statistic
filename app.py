from flask import Flask, render_template, request, redirect, url_for, session
import requests

app = Flask(__name__)
app.secret_key = "anoma-secret"

API_BASE = "https://api.prod.testnet.anoma.net/api/v1"

# simpan visitor unique berdasarkan IP
unique_visitors = set()

@app.before_request
def track_visitors():
    ip = request.remote_addr
    if ip not in unique_visitors:
        unique_visitors.add(ip)

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        token = request.form.get("bearer")
        session["bearer"] = token
        return redirect(url_for("stats"))
    return render_template("home.html", visitors=len(unique_visitors))


@app.route("/stats")
def stats():
    bearer = session.get("bearer")
    if not bearer:
        return redirect(url_for("home"))

    headers = {"Authorization": f"Bearer {bearer}", "Accept": "*/*"}

    user_data = requests.get(f"{API_BASE}/user", headers=headers).json()
    garapon_data = requests.get(f"{API_BASE}/garapon", headers=headers).json()

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
    serve(app, host="0.0.0.0", port=port)
