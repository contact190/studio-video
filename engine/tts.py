"""Voix off locale et gratuite (Kokoro via sherpa-onnx). Anglais uniquement pour l'instant ;
pour le français ou la darija, générer la voix ailleurs (Magnific, OpenAI) et passer le
fichier audio dans le plan (champ "audio" de la ligne).

Les mots absents du dictionnaire sont sautés en silence par le moteur : le script
signale ces mots, à ajouter dans tts/lexicon-extra.txt.
"""
import sys, re, wave, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import MODELS, ROOT

VOICES = {  # kokoro-multi-lang-v1_0
    'af_heart': 3, 'af_bella': 2, 'af_nicole': 6, 'af_sarah': 9, 'af_sky': 10,
    'am_adam': 11, 'am_echo': 12, 'am_eric': 13, 'am_fenrir': 14, 'am_liam': 15, 'am_michael': 16, 'am_onyx': 17, 'am_puck': 18,
    'bf_emma': 21, 'bf_isabella': 22, 'bm_george': 26, 'bm_lewis': 27,
}
_tts = _lex = None
M = MODELS / 'kokoro-multi-lang-v1_0'


def _lexicon_path():
    out = Path('/tmp/studio-lexicon-us-en.txt')
    extra = (ROOT / 'tts' / 'lexicon-extra.txt').read_text(encoding='utf-8')
    if not out.exists() or out.stat().st_mtime < (ROOT / 'tts' / 'lexicon-extra.txt').stat().st_mtime:
        out.write_text(extra + (M / 'lexicon-us-en.txt').read_text(encoding='utf-8'), encoding='utf-8')
    return out


def missing_words(text):
    global _lex
    if _lex is None:
        _lex = {l.split(' ', 1)[0].lower() for l in _lexicon_path().read_text(encoding='utf-8').splitlines() if l}
    ws = {w.lower() for w in re.findall(r"[A-Za-z']+", text)}
    return sorted(w for w in ws if w not in _lex and not w.isdigit())


def synth(text, out_path, voice='am_michael', speed=1.05):
    """Génère un WAV (silences de début/fin retirés). Renvoie la durée en secondes."""
    global _tts
    import sherpa_onnx
    if _tts is None:
        cfg = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
            kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                model=str(M / 'model.onnx'), voices=str(M / 'voices.bin'), tokens=str(M / 'tokens.txt'),
                data_dir=str(M / 'espeak-ng-data'), lexicon=str(_lexicon_path()), dict_dir=str(M / 'dict'), lang='en-us'),
            num_threads=2), max_num_sentences=1)
        _tts = sherpa_onnx.OfflineTts(cfg)
    miss = missing_words(text)
    if miss:
        raise ValueError(f"Mots absents du dictionnaire de la voix (ils seraient sautés) : {', '.join(miss)}. "
                         f"Ajoute-les dans tts/lexicon-extra.txt ou reformule.")
    sid = VOICES.get(voice, voice if isinstance(voice, int) else 16)
    a = _tts.generate(text, sid=sid, speed=speed)
    s = np.array(a.samples, dtype=np.float32)
    nz = np.where(np.abs(s) > 0.01)[0]
    if len(nz):
        s = s[max(0, nz[0] - 600): nz[-1] + 2400]
    with wave.open(str(out_path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(a.sample_rate)
        w.writeframes((np.clip(s, -1, 1) * 32767).astype('<i2').tobytes())
    return len(s) / a.sample_rate


if __name__ == '__main__':
    print(synth(sys.argv[1], sys.argv[2], *(sys.argv[3:4] or [])))
