#!/usr/bin/env python3
"""
Fetch latest Render deploy logs for WishTogether.
Usage: python3 render_logs.py <YOUR_RENDER_API_KEY>
"""
import sys
import urllib.request
import urllib.error
import json

SERVICE_ID = "srv-d8qf0alckfvc73e54cjg"
API_BASE   = "https://api.render.com/v1"

def api_get(path, api_key):
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 render_logs.py <RENDER_API_KEY>")
        print("Get your key at: https://dashboard.render.com/u/settings#api-keys")
        sys.exit(1)

    api_key = sys.argv[1]

    print(f"\n🔍 Fetching latest deploys for WishTogether...\n")

    # Get recent deploys
    deploys = api_get(f"/services/{SERVICE_ID}/deploys?limit=3", api_key)

    for entry in deploys:
        d = entry.get("deploy", entry)
        status    = d.get("status", "unknown")
        deploy_id = d.get("id", "")
        commit    = d.get("commit", {})
        msg       = commit.get("message", "")[:60] if commit else ""
        created   = d.get("createdAt", "")[:16].replace("T", " ")

        icon = "✅" if status == "live" else "❌" if status == "failed" else "⏳"
        print(f"{icon} [{status.upper()}] {created}  {msg}")
        print(f"   Deploy ID: {deploy_id}")

        # Fetch logs for failed deploys
        if status == "failed" and deploy_id:
            print(f"\n   📋 Error logs:")
            try:
                logs = api_get(f"/deploys/{deploy_id}/logs", api_key)
                entries = logs if isinstance(logs, list) else logs.get("logs", [])
                for line in entries[-30:]:           # last 30 lines
                    ts  = line.get("timestamp", "")[:19].replace("T", " ")
                    txt = line.get("text", str(line))
                    print(f"   {ts}  {txt}")
            except Exception as e:
                print(f"   (Could not fetch logs: {e})")
        print()

if __name__ == "__main__":
    main()
