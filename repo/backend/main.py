from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import os
import shutil
import tempfile
from datetime import datetime

from .config import settings
from .core import (
    WhisperTranscriber,
    SpeakerDiarizer,
    MaterialCodeExtractor,
    MeetingSummarizer,
    EmailSender
)
from .models import (
    MeetingProcessRequest,
    MeetingProcessResponse,
    EmailSendRequest,
    WarehouseLayoutData
)

app = FastAPI(
    title="应急物资储备库布局优化会议系统",
    description="处理供应链专家讨论，生成布局调整和补库计划",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

whisper_transcriber = WhisperTranscriber()
speaker_diarizer = SpeakerDiarizer()
material_extractor = MaterialCodeExtractor()
meeting_summarizer = MeetingSummarizer()
email_sender = EmailSender()

UPLOAD_DIR = tempfile.mkdtemp(prefix="meeting_audio_")


@app.get("/")
async def root():
    return {
        "name": "应急物资储备库布局优化会议系统",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/api/meeting/transcribe", response_model=MeetingProcessResponse)
async def transcribe_meeting(
    audio_file: UploadFile = File(None),
    manual_transcript: Optional[str] = None
):
    try:
        if audio_file:
            file_path = os.path.join(UPLOAD_DIR, audio_file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(audio_file.file, buffer)
            
            transcription_result = whisper_transcriber.transcribe_with_material_classification(file_path)
        elif manual_transcript:
            segments = [{"start": 0, "end": len(manual_transcript) / 5, "text": manual_transcript}]
            transcription_result = {
                "full_text": manual_transcript,
                "segments": segments,
                "material_classification": {},
                "urgency_requirements": []
            }
            
            text = manual_transcript
            material_keywords = {
                "医疗物资": ["口罩", "防护服", "呼吸机", "急救包", "药品", "绷带", "消毒液", "护目镜"],
                "生活物资": ["食品", "饮用水", "帐篷", "毛毯", "棉被", "方便面", "压缩饼干"],
                "救援物资": ["救生艇", "救生衣", "绳索", "切割机", "破拆工具", "发电设备", "手电筒"],
                "通讯物资": ["对讲机", "卫星电话", "应急广播", "备用电池"],
            }
            classified = {}
            for cat, kws in material_keywords.items():
                found = [kw for kw in kws if kw in text]
                if found:
                    classified[cat] = found
            transcription_result["material_classification"] = classified
            
            urgency_patterns = ["紧急", "急需", "立即", "马上", "尽快", "时效", "期限", "小时内", "天内", "周内"]
            transcription_result["urgency_requirements"] = [p for p in urgency_patterns if p in text]
        else:
            raise HTTPException(status_code=400, detail="请提供音频文件或手动输入的会议文本")

        return MeetingProcessResponse(
            success=True,
            message="音频转写完成",
            data=transcription_result
        )
    except Exception as e:
        return MeetingProcessResponse(
            success=False,
            message=f"转写失败: {str(e)}"
        )


@app.post("/api/meeting/analyze", response_model=MeetingProcessResponse)
async def analyze_meeting(data: Dict[str, Any]):
    try:
        segments = data.get("segments", [])
        full_text = data.get("full_text", "")
        classified_materials = data.get("material_classification", {})
        urgency_requirements = data.get("urgency_requirements", [])

        diarization_result = speaker_diarizer.diarize("", segments)
        speaker_segments = diarization_result["speaker_segments"]
        
        role_classification = speaker_diarizer.classify_speaker_roles(speaker_segments, segments)
        merged_segments = speaker_diarizer.merge_transcription_with_roles(
            segments,
            role_classification["role_segments"]
        )

        material_extraction = material_extractor.extract_material_codes(full_text)
        enriched_segments = material_extractor.extract_with_context(merged_segments)

        summary = meeting_summarizer.generate_summary(
            full_text=full_text,
            classified_materials=classified_materials,
            urgency_requirements=urgency_requirements,
            speaker_roles=role_classification["speaker_roles"],
            extracted_materials=material_extraction["matched_materials"]
        )

        meeting_minutes = meeting_summarizer.generate_meeting_minutes(
            merged_segments=enriched_segments,
            summary=summary
        )

        return MeetingProcessResponse(
            success=True,
            message="会议分析完成",
            data={
                "speaker_roles": role_classification["speaker_roles"],
                "merged_segments": enriched_segments,
                "extracted_materials": material_extraction,
                "summary": summary,
                "meeting_minutes": meeting_minutes
            }
        )
    except Exception as e:
        return MeetingProcessResponse(
            success=False,
            message=f"分析失败: {str(e)}"
        )


@app.post("/api/meeting/process-full", response_model=MeetingProcessResponse)
async def process_full_meeting(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(None),
    manual_transcript: Optional[str] = None,
    send_email: bool = False
):
    try:
        if audio_file:
            file_path = os.path.join(UPLOAD_DIR, audio_file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(audio_file.file, buffer)
            
            transcription_result = whisper_transcriber.transcribe_with_material_classification(file_path)
        elif manual_transcript:
            segments = [{"start": 0, "end": len(manual_transcript) / 5, "text": manual_transcript}]
            transcription_result = {
                "full_text": manual_transcript,
                "segments": segments,
                "material_classification": {},
                "urgency_requirements": []
            }
            
            text = manual_transcript
            material_keywords = {
                "医疗物资": ["口罩", "防护服", "呼吸机", "急救包", "药品", "绷带", "消毒液", "护目镜"],
                "生活物资": ["食品", "饮用水", "帐篷", "毛毯", "棉被", "方便面", "压缩饼干"],
                "救援物资": ["救生艇", "救生衣", "绳索", "切割机", "破拆工具", "发电设备", "手电筒"],
                "通讯物资": ["对讲机", "卫星电话", "应急广播", "备用电池"],
            }
            classified = {}
            for cat, kws in material_keywords.items():
                found = [kw for kw in kws if kw in text]
                if found:
                    classified[cat] = found
            transcription_result["material_classification"] = classified
            
            urgency_patterns = ["紧急", "急需", "立即", "马上", "尽快", "时效", "期限", "小时内", "天内", "周内"]
            transcription_result["urgency_requirements"] = [p for p in urgency_patterns if p in text]
        else:
            raise HTTPException(status_code=400, detail="请提供音频文件或手动输入的会议文本")

        segments = transcription_result["segments"]
        full_text = transcription_result["full_text"]
        classified_materials = transcription_result["material_classification"]
        urgency_requirements = transcription_result["urgency_requirements"]

        diarization_result = speaker_diarizer.diarize("", segments)
        speaker_segments = diarization_result["speaker_segments"]
        
        role_classification = speaker_diarizer.classify_speaker_roles(speaker_segments, segments)
        merged_segments = speaker_diarizer.merge_transcription_with_roles(
            segments,
            role_classification["role_segments"]
        )

        material_extraction = material_extractor.extract_material_codes(full_text)
        enriched_segments = material_extractor.extract_with_context(merged_segments)

        summary = meeting_summarizer.generate_summary(
            full_text=full_text,
            classified_materials=classified_materials,
            urgency_requirements=urgency_requirements,
            speaker_roles=role_classification["speaker_roles"],
            extracted_materials=material_extraction["matched_materials"]
        )

        meeting_minutes = meeting_summarizer.generate_meeting_minutes(
            merged_segments=enriched_segments,
            summary=summary
        )

        email_result = None
        if send_email:
            email_result = email_sender.send_to_emergency_admin(
                meeting_minutes=meeting_minutes,
                summary=summary
            )

        return MeetingProcessResponse(
            success=True,
            message="会议完整处理完成",
            data={
                "transcription": transcription_result,
                "speaker_roles": role_classification["speaker_roles"],
                "merged_segments": enriched_segments,
                "extracted_materials": material_extraction,
                "summary": summary,
                "meeting_minutes": meeting_minutes,
                "email_result": email_result
            }
        )
    except Exception as e:
        return MeetingProcessResponse(
            success=False,
            message=f"处理失败: {str(e)}"
        )


@app.post("/api/email/send")
async def send_email(request: EmailSendRequest):
    try:
        result = email_sender.send_meeting_minutes(
            to_emails=request.to_emails,
            meeting_minutes=request.meeting_minutes,
            summary=request.summary
        )
        return result
    except Exception as e:
        return {"success": False, "message": f"邮件发送失败: {str(e)}"}


@app.get("/api/warehouse/layout")
async def get_warehouse_layout():
    default_layout = {
        "zones": [
            {"id": "A", "name": "医疗物资区", "color": "#e74c3c", "position": {"x": -15, "z": -10}},
            {"id": "B", "name": "生活物资区", "color": "#3498db", "position": {"x": 15, "z": -10}},
            {"id": "C", "name": "救援物资区", "color": "#f39c12", "position": {"x": -15, "z": 10}},
            {"id": "D", "name": "通讯物资区", "color": "#2ecc71", "position": {"x": 15, "z": 10}},
            {"id": "E", "name": "出库区", "color": "#9b59b6", "position": {"x": 0, "z": -20}},
        ],
        "shelves": [
            {"id": 1, "zone": "A", "position": {"x": -18, "y": 0, "z": -8}, "size": {"x": 4, "y": 3, "z": 1}, "level": 5, "materials": ["口罩", "防护服"]},
            {"id": 2, "zone": "A", "position": {"x": -12, "y": 0, "z": -8}, "size": {"x": 4, "y": 3, "z": 1}, "level": 5, "materials": ["急救包", "药品"]},
            {"id": 3, "zone": "B", "position": {"x": 12, "y": 0, "z": -8}, "size": {"x": 4, "y": 3, "z": 1}, "level": 5, "materials": ["食品", "饮用水"]},
            {"id": 4, "zone": "B", "position": {"x": 18, "y": 0, "z": -8}, "size": {"x": 4, "y": 3, "z": 1}, "level": 5, "materials": ["帐篷", "毛毯"]},
            {"id": 5, "zone": "C", "position": {"x": -18, "y": 0, "z": 12}, "size": {"x": 4, "y": 3, "z": 1}, "level": 5, "materials": ["救生艇", "救生衣"]},
            {"id": 6, "zone": "C", "position": {"x": -12, "y": 0, "z": 12}, "size": {"x": 4, "y": 3, "z": 1}, "level": 5, "materials": ["切割机", "发电设备"]},
            {"id": 7, "zone": "D", "position": {"x": 12, "y": 0, "z": 12}, "size": {"x": 4, "y": 3, "z": 1}, "level": 5, "materials": ["对讲机", "卫星电话"]},
            {"id": 8, "zone": "D", "position": {"x": 18, "y": 0, "z": 12}, "size": {"x": 4, "y": 3, "z": 1}, "level": 5, "materials": ["应急广播", "备用电池"]},
        ],
        "emergency_kits": [
            {"id": 1, "position": {"x": -15, "y": 1, "z": -15}, "type": "医疗急救包", "status": "ready"},
            {"id": 2, "position": {"x": 15, "y": 1, "z": -15}, "type": "生活应急包", "status": "ready"},
            {"id": 3, "position": {"x": -15, "y": 1, "z": 15}, "type": "救援应急包", "status": "ready"},
            {"id": 4, "position": {"x": 15, "y": 1, "z": 15}, "type": "通讯应急包", "status": "ready"},
            {"id": 5, "position": {"x": 0, "y": 1, "z": 0}, "type": "综合应急包", "status": "ready"},
        ],
        "exits": [
            {"id": 1, "name": "主出口", "position": {"x": 0, "z": -22}},
            {"id": 2, "name": "侧出口1", "position": {"x": -22, "z": 0}},
            {"id": 3, "name": "侧出口2", "position": {"x": 22, "z": 0}},
        ]
    }
    return default_layout


@app.post("/api/warehouse/layout/update")
async def update_warehouse_layout(layout_data: WarehouseLayoutData):
    try:
        return {
            "success": True,
            "message": "仓库布局已更新",
            "data": layout_data.dict()
        }
    except Exception as e:
        return {"success": False, "message": f"布局更新失败: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
