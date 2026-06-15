import streamlit as st
import azure.cognitiveservices.speech as speechsdk
import os

st.set_page_config(page_title="AI音読アドバイザー", layout="centered")
st.title("🗣️ AI音読アドバイザー")

# ---------------------------------------------------------
# 🌟 画面のトップで奇数・偶数を選ばせる
# ---------------------------------------------------------
attendance_type = st.radio(
    "あなたの 出席番号（または班） を選んでください：",
    ["奇数番号 (1, 3, 5...)", "偶数番号 (2, 4, 6...)"],
    horizontal=True
)

# Secretsの読み込みチェック
try:
    if "奇数" in attendance_type:
        azure_key = st.secrets["KEY_KISU"]
        st.caption("🟢 奇数用のキーを読み込みました")
    else:
        azure_key = st.secrets["KEY_GUSU"]
        st.caption("🟢 偶数用のキーを読み込みました")
        
    azure_region = st.secrets["AZURE_REGION"]
except Exception as e:
    st.error(f"⚠️ StreamlitのSecretsの読み込みでエラーが発生しました: {e}")
    st.info("Secretsに書いた『KEY_KISU』『KEY_GUSU』『AZURE_REGION』の文字がプログラムと一致していない可能性があります。")

# 📖 音読する英文の設定
reference_text = st.text_input("練習する英文：", "Welcome to our school. Let's study English together.")

st.markdown("---")
st.subheader("🎤 録音スタート")

audio_value = st.audio_input("マイクボタンを押して英語を読んでね")

if audio_value:
    st.info("AIが発音を分析中...")
    
    with open("temp_audio.wav", "wb") as f:
        f.write(audio_value.read())
        
    try:
        # Azureの設定
        speech_config = speechsdk.SpeechConfig(subscription=azure_key, region=azure_region)
        audio_config = speechsdk.audio.AudioConfig(filename="temp_audio.wav")
        
        pronunciation_config = speechsdk.PronunciationAssessmentConfig(
            json_string=f'{{"referenceText":"{reference_text}","gradingSystem":"HundredMark","granularity":"Word","phonemeAlphabet":"IPA"}}'
        )
        
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        pronunciation_config.apply_to(speech_recognizer)
        
        result = speech_recognizer.recognize_once_async().get()
        
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            pron_result = speechsdk.PronunciationAssessmentResult.from_result(result)
            st.success(f"🎉 あなたの発音スコア: {int(pron_result.accuracy_score)} 点 / 100点")
        else:
            # 🔴 Azureからの具体的なエラー内容を表示する
            st.error(f"❌ Azure AIからのエラー応答: {result.reason}")
            if result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = speechsdk.CancellationDetails.from_result(result)
                st.warning(f"詳細理由: {cancellation_details.reason}")
                st.warning(f"エラーコード: {cancellation_details.error_code}")
                st.warning(f"エラー詳細: {cancellation_details.error_details}")
                
    except Exception as e:
        # 🔴 プログラム自体のエラー内容を表示する
        st.error(f"❌ プログラムの実行エラー: {e}")
        
    finally:
        if os.path.exists("temp_audio.wav"):
            os.remove("temp_audio.wav")
