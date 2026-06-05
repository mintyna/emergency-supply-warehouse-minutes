import whisper
import os
from typing import Dict, Any
from ..config import settings


class WhisperTranscriber:
    def __init__(self):
        self.model = None
        self.model_size = settings.WHISPER_MODEL_SIZE

    def _load_model(self):
        if self.model is None:
            self.model = whisper.load_model(self.model_size)

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        self._load_model()
        
        result = self.model.transcribe(
            audio_path,
            language="zh",
            verbose=False
        )
        
        segments = []
        for seg in result["segments"]:
            segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"]
            })
        
        return {
            "full_text": result["text"],
            "segments": segments,
            "language": result.get("language", "zh")
        }

    def transcribe_with_material_classification(self, audio_path: str) -> Dict[str, Any]:
        transcription = self.transcribe(audio_path)
        
        text = transcription["full_text"]
        
        material_keywords = {
            "医疗物资": ["口罩", "防护服", "呼吸机", "急救包", "药品", "绷带", "消毒液", "护目镜"],
            "生活物资": ["食品", "饮用水", "帐篷", "毛毯", "棉被", "方便面", "压缩饼干"],
            "救援物资": ["救生艇", "救生衣", "绳索", "切割机", "破拆工具", "发电设备", "手电筒"],
            "通讯物资": ["对讲机", "卫星电话", "应急广播", "备用电池"],
            "其他": []
        }
        
        classified_materials = {}
        for category, keywords in material_keywords.items():
            found = [kw for kw in keywords if kw in text]
            if found:
                classified_materials[category] = found
        
        urgency_patterns = ["紧急", "急需", "立即", "马上", "尽快", "时效", "期限", "小时内", "天内", "周内"]
        urgency_matches = [p for p in urgency_patterns if p in text]
        
        return {
            **transcription,
            "material_classification": classified_materials,
            "urgency_requirements": urgency_matches
        }
