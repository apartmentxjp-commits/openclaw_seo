import json
import os

def analyze_traffic(data_path):
    # In a real scenario, this would connect to Google Analytics API or parse logs.
    # For now, we simulate analysis based on provided structured data.
    
    if not os.path.exists(data_path):
        print(f"Error: Analytics data file not found at {data_path}")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Sort pages by sessions
    all_pages = data.get("pages", [])
    top_pages = sorted(all_pages, key=lambda x: x.get("sessions", 0), reverse=True)[:5]
    
    # Sort by CTR (Click-Through Rate)
    high_ctr_pages = sorted(all_pages, key=lambda x: x.get("ctr", 0), reverse=True)[:5]
    
    # Identify low performance (Low sessions AND Low CTR)
    low_performance = [p for p in all_pages if p.get("sessions", 0) < 50 and p.get("ctr", 0) < 0.01]

    report = {
        "top_pages": top_pages,
        "high_ctr_pages": high_ctr_pages,
        "low_performance_pages": low_performance
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    import sys
    # Sample data creation if not exists for demo
    dummy_path = "/app/brain/04_Output/analytics_dummy.json"
    if not os.path.exists(dummy_path):
        dummy_data = {
            "pages": [
                {"url": "/post/世田谷区_三軒茶屋/", "sessions": 500, "ctr": 0.05},
                {"url": "/post/世田谷区_代沢/", "sessions": 300, "ctr": 0.03},
                {"url": "/post/old_article/", "sessions": 10, "ctr": 0.005}
            ]
        }
        os.makedirs(os.path.dirname(dummy_path), exist_ok=True)
        with open(dummy_path, "w") as f:
            json.dump(dummy_data, f)

    path = sys.argv[1] if len(sys.argv) > 1 else dummy_path
    analyze_traffic(path)
