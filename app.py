import streamlit as st
import azure.cognitiveservices.speech as speechsdk
import os

st.set_page_config(page_title="AI音読アドバイザー", layout="centered")
st.title("🗣️ AI音読アドバイザー")
st.write("教科書の英文を読んで、発音をチェックしてみよう！")

# ---------------------------------------------------------
# 🌟 画面のトップで奇数・偶数を選ばせる（負荷分散スイッチ）
# ---------------------------------------------------------
attendance_type = st.radio(
    "あなたの 出席番号（または班） を選んでください：",
    ["奇数番号 (1, 3, 5...)", "偶数番号 (2, 4, 6...)"],
    horizontal=True
)

# 選択によって、裏側で使うAIのキーを自動で切り替える
if "奇数" in attendance_type:
    azure_key = st.secrets["KEY_KISU"]
else:
    azure_key = st.secrets["KEY_GUSU"]

azure_region = st.secrets["AZURE_REGION"]

# ---------------------------------------------------------
# 📖 音読する英文の設定
# ---------------------------------------------------------
reference_text = st.text_input("練習する英文（先生がここに入力するか、生徒がコピーして貼り付けます）：", "Welcome to our school. Let's study English together.")

st.markdown("---")
st.subheader("🎤 録音スタート")

# Streamlit標準のマイク録音機能
audio_value = st.audio_input("マイクボタンを押して英語を読んでね")

if audio_value:
    st.info("AIが発音を分析中... 少し待ってね 🤖")

    # 録音データを一時的なファイルとして保存
    with open("temp_audio.wav", "wb") as f:
        f.write(audio_value.read())

    try:
        # Azure Speech SDKの設定
        speech_config = speechsdk.SpeechConfig(subscription=azure_key, region=azure_region)
        audio_config = speechsdk.audio.AudioConfig(filename="temp_audio.wav")

        # 発音評価（Pronunciation Assessment）の設定
        pronunciation_config = speechsdk.PronunciationAssessmentConfig(
            json_string=f'{{"referenceText":"{reference_text}","gradingSystem":"HundredMark","granularity":"Word","phonemeAlphabet":"IPA"}}'
       )

        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        pronunciation_config.apply_to(speech_recognizer)

        # AIの判定を実行
        result = speech_recognizer.recognize_once_async().get()

        # 結果の解析
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            pron_result = speechsdk.PronunciationAssessmentResult.from_result(result)

            # スコアの表示
            st.success(f"🎉 あなたの発音スコア: {int(pron_result.accuracy_score)} 点 / 100点")

            # 点数に応じたアドバイス
            score = pron_result.accuracy_score
            if score >= 85:
                st.balloons()
                st.write("🏅 **すばらしい！** ネイティブに近いキレイな発音です。その調子！")
            elif score >= 60:
                st.write("👍 **Nice try!** よく聞き取れました。もう少しはっきりと声を出してみよう。")
            else:
                st.write("📢 **もう一度チャレンジ！** お手本の英文をよく聞いて、1単語ずつていねいに読んでみよう。")

            # 単語ごとの細かいフィードバック
            st.markdown("### 🔍 単語ごとのチェック")
            words_feedback = []
            for word in pron_result.words:
                if word.error_type == "None":
                    words_feedback.append(f"🟢 **{word.word}** (バッチリ！)")
                elif word.error_type == "Mispronunciation":
                    words_feedback.append(f"🔴 **{word.word}** (おしい！発音が少し違うかも)")
                elif word.error_type == "Omission":
                    words_feedback.append(f"⚪ **{word.word}** (聞き取れなかったよ。読み飛ばしたかな？)")
                elif word.error_type == "Insertion":
                    words_feedback.append(f"🟡 **{word.word}** (余分な音が混ざったかも)")

            st.write(" | ".join(words_feedback))

        else:
            st.error("AIがうまく声を聴き取れませんでした。マイクに近づいてもう一度試してね。")

    except Exception as e:
        st.error(f"システムエラーが発生しました。先生に報告してください。")

    finally:
        # 一時ファイルの削除
        if os.path.exists("temp_audio.wav"):
            os.remove("temp_audio.wav")
