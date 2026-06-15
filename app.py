import streamlit as st
import azure.cognitiveservices.speech as speechsdk
import json
from audio_recorder_streamlit import audio_recorder

st.set_page_config(page_title="AI音読アドバイザー", layout="wide")

# デザインを整える
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🎓 AI英語音読アドバイザー")
st.write("あなたの英語をAIが細かく分析して、上達のアドバイスを伝えます。")

# 設定読み込み
AZURE_KEY = st.secrets["AZURE_KEY"]
AZURE_REGION = st.secrets["AZURE_REGION"]

# 入力エリア
col_in, col_rec = st.columns([2, 1])
with col_in:
    reference_text = st.text_area("本文を貼り付けてください", "The quick brown fox jumps over the lazy dog.", height=150)

with col_rec:
    st.write("🎙️ 録音ボタン")
    audio_bytes = audio_recorder(text="クリックして録音", pause_threshold=2.5, sample_rate=16000)

if audio_bytes:
    with open("temp_audio.wav", "wb") as f:
        f.write(audio_bytes)
    
    st.audio(audio_bytes, format="audio/wav")

    # Azure設定
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
    audio_config = speechsdk.audio.AudioConfig(filename="temp_audio.wav")
    
    # 粒度を「音素（Phoneme）」レベルまで詳細化
    pron_config = speechsdk.PronunciationAssessmentConfig(
        reference_text=reference_text,
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme
    )

    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config, language="en-US")
    pron_config.apply_to(recognizer)
    
    with st.spinner('AIが詳細分析中... 少々お待ちください'):
        result = recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        res_json = json.loads(result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult))
        
        # 全体スコアの表示
        acc_score = res_json["NBest"][0]["PronunciationAssessment"]["AccuracyScore"]
        flu_score = res_json["NBest"][0]["PronunciationAssessment"]["FluencyScore"]
        comp_score = res_json["NBest"][0]["PronunciationAssessment"]["CompletenessScore"]

        st.subheader("📊 全体評価")
        m1, m2, m3 = st.columns(3)
        m1.metric("正確さ", f"{int(acc_score)}点")
        m2.metric("流暢さ", f"{int(flu_score)}点")
        m3.metric("読み落としなし", f"{int(comp_score)}点")

        # 単語ごとの分析と色分け
        words = res_json["NBest"][0]["Words"]
        st.subheader("🎯 単語ごとの指摘")
        
        display_html = "<div style='font-size: 24px; line-height: 2.2; margin-bottom: 20px;'>"
        advice_list = []

        for w in words:
            word_text = w["Word"]
            p_assess = w["PronunciationAssessment"]
            score = p_assess["AccuracyScore"]
            err_type = p_assess.get("ErrorType", "None")

            # 色の決定
            color = "#10b981" # 緑
            if err_type == "Omission":
                color = "#64748b" # グレー（読み飛ばし）
                advice_list.append(f"⚠️ **{word_text}**: 読み飛ばされているか、声が小さくて聞こえませんでした。")
            elif score < 60:
                color = "#f43f5e" # 赤
                advice_list.append(f"❌ **{word_text}**: 発音が少し違うようです。母音や子音をはっきり発声しましょう。")
            elif score < 85:
                color = "#f59e0b" # 黄
                advice_list.append(f"🤔 **{word_text}**: おしい！もう少しネイティブの発音を意識してみましょう。")

            display_html += f"<span style='color: {color}; border-bottom: 3px solid {color}; margin-right: 10px; font-weight: bold;'>{word_text}</span>"
        
        display_html += "</div>"
        st.markdown(display_html, unsafe_allow_html=True)

        # AIからの具体的なアドバイス
        if advice_list:
            with st.expander("💡 もっと良くするためのアドバイス"):
                for advice in advice_list:
                    st.write(advice)
        else:
            st.success("素晴らしい！完璧な音読です。")

    else:
        st.error("うまく聞き取れませんでした。もう一度、マイクの近くではっきり読んでみてください。")
