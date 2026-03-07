import os
import json
from datetime import datetime

class PersonaManager:
    def __init__(self, persona_data):
        self.persona = persona_data
        
    def get_current_phase(self):
        start = datetime.strptime(self.persona.get("start_date", "2025-01-01"), "%Y-%m-%d")
        months = (datetime.now() - start).days // 30
        arcs = self.persona.get("story_arc", [])
        for arc in reversed(arcs):
            if months >= (arc["phase"] - 1) * 3:
                return arc
        return arcs[0] if arcs else {}

    def get_context(self):
        phase = self.get_current_phase()
        return f"""
## あなたが演じるペルソナ
名前: {self.persona['name']} / {self.persona['age']}歳 / {self.persona['gender']}
職業: {self.persona['job']}
一人称: {self.persona['pronoun']}
ジャンル: {self.persona['genre']}
ターゲット: {self.persona['target']}
口調: {self.persona['tone']}
NGワード: {self.persona['ng_words']}

## 現在フェーズ: フェーズ{phase.get('phase', 1)} ({phase.get('name', '')})
今の感情: {phase.get('emotion', '')}
テーマ: {phase.get('content_theme', '')}

## 絶対ルール
- 一人称は「{self.persona['pronoun']}」
- 成功を匂わせすぎない。フェーズ相応の感情で書く。
- NGワード厳禁: 重要です/活用/最適化/効果的/以上です/まとめ
"""

# Education design steps (5 steps)
EDUCATION_STEPS = {
    "STEP_1": "共感の刃 (痛みの言語化)",
    "STEP_2": "価値観の転換 (常識を壊す)",
    "STEP_3": "理想の提示 (具体的な未来)",
    "STEP_4": "壁 (WHATは見せてHOWは隠す)",
    "STEP_5": "次回予告 (期待感の醸成)"
}

def build_noteforge_article(topic, persona):
    mgr = PersonaManager(persona)
    context = mgr.get_context()
    # In a real run, this would call Gemini for each step
    print(f"--- Generating NoteForge Article: {topic} ---")
    print(f"Active Context: {context}")
    print("Designing 5-step education flow...")
    return "Designed Flow"
