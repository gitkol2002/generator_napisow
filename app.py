# Import bibliotek
import streamlit as st
import io
import tempfile
import base64
from pydub import AudioSegment
from dotenv import dotenv_values
from openai import OpenAI

# Konfiguracja strony
st.set_page_config(page_title="Generowanie napisów 🎬", layout="centered")

# Pomocnicze zmienne w session_state
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# Funkcja: konwersja SRT → VTT
def srt_to_vtt(srt_text: str) -> str:
    """
    Zamienia napisy w formacie SRT na VTT.
    """
    vtt_text = "WEBVTT\n\n"
    for line in srt_text.splitlines():
        if "-->" in line:
            line = line.replace(",", ".")
        elif line.strip().isdigit():
            continue
        vtt_text += line + "\n"
    return vtt_text

# Funkcja: player HTML5 z napisami
def video_with_subs(video_path: str, vtt_path: str) -> str:
    """
    Generuje HTML5 <video> z osadzonymi napisami VTT.
    """
    with open(video_path, "rb") as vf:
        video_b64 = base64.b64encode(vf.read()).decode()
    with open(vtt_path, "rb") as sf:
        subs_b64 = base64.b64encode(sf.read()).decode()
    html_code = f"""
    <video width="720" height="480" controls>
        <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
        <track src="data:text/vtt;base64,{subs_b64}" kind="subtitles" srclang="pl" label="Polski" default>
    </video>
    """
    return html_code

# Tytuł
st.markdown("<h1 style='text-align:center;'>🎬 Edytor napisów</h1>", unsafe_allow_html=True)

# Instrukcja
with st.expander("📖 **Instrukcja obsługi** *(kliknij aby rozwinąć)*"):
    st.markdown("""
    ***Wymagane wprowadzenie klucza OpenAI przez użytkownika!***
    1. Wybierz plik wideo (`mp4`, `mp3`, `avi`, `mov`, `mkv`).  
    2. Odtwórz film i audio, sprawdź czy działa.  
    3. Wygeneruj napisy automatycznie (Whisper AI).  
    4. Edytuj napisy jeśli trzeba.  
    5. Zapisz i pobierz w formacie `.srt` lub `.vtt`.  
    6. Podejrzyj film z napisami w playerze HTML5.  
    7. Kliknij ➕ Wczytaj kolejne wideo, aby rozpocząć od nowa.
    """)

# Funkcjonalność
with st.expander("📝 **Funkcjonalność aplikacji** *(kliknij aby rozwinąć)*"):
    st.markdown("""
    Użytkownik może przesłać plik wideo, który jest następnie wyświetlany w aplikacji.
    Z przesłanego wideo wyodrębniamy dźwięk, który również jest dostępny do odsłuchu.
    Wykorzystujemy model speech-to-text, aby automatycznie wygenerować napisy na podstawie dźwięku, które potem są wyświetlane użytkownikowi.
    Użytkownik ma możliwość edytowania wygenerowanych napisów bezpośrednio w aplikacji.
    Poprawione napisy można zapisać do pliku i pobrać w popularnych formatach napisów: SRT oraz VTT.
    Film z dołączonymi napisami jest wyświetlany w odtwarzaczu aplikacji, umożliwiając podgląd efektu końcowego.
    Użytkownik może również pobrać gotowy film z dołączonymi napisami.
    """)

st.divider()

# ----------------------------------------
# Inicjalizacja klienta OpenAI bez klucza
openai_client = st.text_input("🔑 Wpisz swój klucz OpenAI", type="password")

if not openai_client:
    st.warning("Podaj swój własny klucz OpenAI, aby uruchomić aplikację.")
    st.stop()

# Tworzenie klienta OpenAI
openai_client = OpenAI(api_key=openai_client)

# Testowanie klucza OpenAI
try:
    openai_client.models.list()  # test połączenia
    st.success("✅ Klucz zaakceptowany! Możesz korzystać z aplikacji.")
except Exception as e:
    st.error(f"❌ Błąd: nieprawidłowy klucz OpenAI ({e})")
    st.stop()
# ----------------------------------------

st.divider()    

# Wczytanie pliku wideo
video_file = st.file_uploader(
    "🎥 **Wybierz plik wideo:**",
    type=["mp4", "mov", "avi", "mkv", "mp3", "wav"],
    key=f"uploader_{st.session_state.uploader_key}",
)

if video_file is not None:
    # Wyświetlenie wideo
    st.markdown("<h3 style='color:darkgreen;'>📺 Podgląd wideo</h3>", unsafe_allow_html=True)
    st.video(video_file)

    # Wyodrębnienie audio
    video_file.seek(0)
    audio = AudioSegment.from_file(video_file)
    audio_buffer = io.BytesIO()
    audio.export(audio_buffer, format="mp3")
    audio_buffer.seek(0)
    audio_buffer.name = "audio.mp3"

    st.markdown("<h3 style='color:orange;'>🔊 Odtwarzanie audio</h3>", unsafe_allow_html=True)
    st.audio(audio_buffer, format="audio/mp3")

    # Generowanie napisów (tylko raz dla pliku)
    if "last_file" not in st.session_state or st.session_state.last_file != video_file.name:
        transcript = openai_client.audio.transcriptions.create(
            file=audio_buffer,
            model="whisper-1",
            response_format="srt"
        )
        st.session_state.edited_text = transcript
        st.session_state.last_file = video_file.name
        st.session_state.edit_mode = False
        st.session_state.save_clicked = False

    # Wyświetlanie / edycja napisów
    st.markdown("<h3 style='color:purple;'>💬 Napisy</h3>", unsafe_allow_html=True)
    if st.session_state.edit_mode:
        edited = st.text_area("✏️ Edytuj napisy:", value=st.session_state.edited_text, height=300)
        st.session_state.edited_text = edited
    else:
        st.markdown(st.session_state.edited_text)

    # Przycisk edycji i zapisu
    c1, c2 = st.columns(2)
    with c1:
        if not st.session_state.edit_mode and st.button("✏️ Edytuj napisy", use_container_width=True):
            st.session_state.edit_mode = True
            st.rerun()
    with c2:
        if st.button("💾 Zapisz napisy", use_container_width=True):
            st.session_state.save_clicked = True
            st.session_state.edit_mode = False

    # Pobranie napisów i podgląd wideo z napisami
    if st.session_state.save_clicked:
        srt_text = st.session_state.edited_text
        vtt_text = srt_to_vtt(srt_text)

        st.download_button("⬇️ Pobierz napisy (SRT)", srt_text, "napisy.srt", "application/x-subrip", use_container_width=True)
        st.download_button("⬇️ Pobierz napisy (VTT)", vtt_text, "napisy.vtt", "text/vtt", use_container_width=True)

        # Pliki tymczasowe
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
            video_file.seek(0)
            tmp_video.write(video_file.read())
            tmp_video_path = tmp_video.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".vtt") as vtt_file:
            vtt_file.write(vtt_text.encode("utf-8"))
            vtt_path = vtt_file.name

        st.markdown("<h3 style='color:red;'>▶️ Film z napisami</h3>", unsafe_allow_html=True)
        st.markdown(video_with_subs(tmp_video_path, vtt_path), unsafe_allow_html=True)

        html_page = video_with_subs(tmp_video_path, vtt_path)
        st.download_button("⬇️ Pobierz player HTML", html_page, "video_with_subs.html", "text/html", use_container_width=True)

st.divider()

# Przycisk: Wczytaj kolejne wideo
if st.button("➕ Wczytaj kolejne wideo", type="primary", use_container_width=True):
    for key in ["last_file", "edited_text", "edit_mode", "save_clicked"]:
        st.session_state.pop(key, None)
    st.session_state.uploader_key += 1
    st.rerun()
