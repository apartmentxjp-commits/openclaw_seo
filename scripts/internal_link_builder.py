import os
import re

CONTENT_DIR = "/app/brain/04_Output/Note"

def build_links():
    files = [f for f in os.listdir(CONTENT_DIR) if f.endswith(".md")]
    
    # Simple logic: links between articles in the same municipality
    for target_file in files:
        file_path = os.path.join(CONTENT_DIR, target_file)
        municipality = target_file.split("_")[0]
        
        related = [f for f in files if f.startswith(municipality) and f != target_file]
        
        if not related:
            continue
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        if "## 関連エリアの不動産情報" in content:
            continue # Already linked
            
        link_section = "\n\n## 関連エリアの不動産情報\n"
        for r_file in related[:5]: # Max 5 links
            r_title = r_file.replace("_", " ").replace(".md", "")
            # Hugo relative link
            link_path = f"/post/{r_file.replace('.md', '').lower()}/"
            link_section += f"- [{r_title}]({link_path})\n"
            
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(link_section)
            
    print(f"✅ Internal links updated for {len(files)} files.")

if __name__ == "__main__":
    build_links()
