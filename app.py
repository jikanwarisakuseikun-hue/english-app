import streamlit as st
import azure.cognitiveservices.speech as speechsdk
import json
from audio_recorder_streamlit import audio_recorder

st.set_page_config(page_title="AI音読練習", layout="wide")
st.title("📖 AI教科書音読練習アプリ")
st.write("本文をコピペして、マイクボタンを押して読んでみよう！")

# GitHubのSecretsから設定を読み込む
AZURE_KEY = st.secrets["AZURE_KEY"]
AZURE_REGION = st.secrets["AZURE_REGION"]

reference_text = st.text_area("教科書の本文をここに貼り付けてください", "Hello, everyone. Welcome to our school.")

# 録音ボタン（16kHz、モノラルで録音）
audio_bytes = audio_recorder(text="クリックして録音開始（喋り終わると自動で止まります）", pause_threshold=2.0, sample_rate=16000)

if audio_bytes:
    with open("temp_audio.wav", "wb") as f:
        f.write(audio_bytes)
    
    st.audio(audio_bytes, format="audio/wav")

    # Azure AIの設定
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
    audio_config = speechsdk.audio.AudioConfig(filename="temp_audio.wav")
    
    pron_config = speechsdk.PronunciationAssessmentConfig(
        reference_text=reference_text,
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Word
    )

    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config, language="en-US")
    pron_config.apply_to(recognizer)
    
    with st.spinner('AIがあなたの発音を分析中...'):
        result = recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        res_json = json.loads(result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult))
        words = res_json["NBest"][0]["Words"]
        
        st.subheader("🎯 判定結果")
        
        display_html = "<div style='font-size: 28px; line-height: 2.0; font-family: sans-serif;'>"
        for w in words:
            score = w["PronunciationAssessment"]["AccuracyScore"]
            word = w["Word"]
            
            # 80点以上は緑、60点以上は黄、それ未満は赤
            color = "#10b981" if score >= 80 else "#f59e0b" if score >= 60 else "#f43f5e"
            display_html += f"<span style='color: {color}; border-bottom: 3px solid {color}; margin-right: 12px; font-weight: bold;' title='Score: {score}'>{word}</span>"
        
        display_html += "</div>"
        
        st.markdown(display_html, unsafe_allow_html=True)
        st.caption("🟢: 80点以上 (Good!) | 🟡: 60-79点 (Keep trying) | 🔴: 60点未満 (Check again)")
    else:
        st.error("音声がうまく認識できませんでした。マイクの許可を確認し、もう一度はっきり読んでみてください。")
