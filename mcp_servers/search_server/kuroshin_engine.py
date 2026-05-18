from flask import Flask, request, jsonify
import httpx
from bs4 import BeautifulSoup
import urllib.parse

app = Flask(__name__)

def google_news_rss_search(query):
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    headers = {"User-Agent": "Mozilla/5.0"}
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(url, headers=headers)
        if resp.status_code != 200: return []
    soup = BeautifulSoup(resp.text, "xml")
    results = []
    for item in soup.find_all('item')[:5]:
        results.append({
            "title": item.title.text if item.title else "N/A",
            "url": item.link.text if item.link else "N/A",
            "content": f"Published: {item.pubDate.text if item.pubDate else 'N/A'}"
        })
    return results

@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/search')
def search():
    query = request.args.get('q')
    if not query: return jsonify({"results": []})
    try:
        results = google_news_rss_search(query)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🔱 KUROSHIN NUCLEAR ENGINE STARTING ON PORT 8091...")
    app.run(host='0.0.0.0', port=8091)
