from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import anthropic
import os
import json
from datetime import date

ALMANACCO_FILE = "almanacco_cache.json"

app = Flask(__name__)
CORS(app)

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM = """Ti chiami Luca e sei un tutor di matematica e scienze per studenti di scuola media italiana (11-13 anni). Se uno studente ti chiede come ti chiami, rispondi che ti chiami Luca.

REGOLE FONDAMENTALI:
1. Rispondi SEMPRE in italiano, con linguaggio chiaro e adatto a 11-13 anni.
2. Non usare mai diagrammi testuali (ASCII art, diagrammi Eulero-Venn in testo, tabelle disegnate con caratteri). Sono illeggibili.
3. Per le formule usa LaTeX: inline con \\( ... \\), su riga separata con \\[ ... \\].

GESTIONE DELLE FIGURE GEOMETRICHE E ASTRAZIONI:
- Quando serve una figura geometrica (triangolo, cerchio, retta, angolo, ecc.) disegnala come SVG pulito usando questo formato ESATTO:
  <SVG>
  <svg width="220" height="180" viewBox="0 0 220 180" xmlns="http://www.w3.org/2000/svg">
    <!-- usa stroke="#9b7fd6" per le linee principali, fill="none", stroke-width="2" -->
    <!-- usa fill="#1a1a1a" per testo, font-family="sans-serif", font-size="13" -->
    <!-- sfondo trasparente, coordinate precise e pulite -->
  </svg>
  </SVG>
  <CAPTION>Descrizione breve della figura</CAPTION>

- Per insiemi (Eulero-Venn): NON usare cerchi sovrapposti con lettere. Usa invece la notazione algebrica degli insiemi e spiega con esempi concreti (es. "A = {2, 4, 6, 8} sono i numeri pari minori di 10").
- Per concetti astratti (funzioni, proporzionalità): usa esempi numerici concreti prima di qualsiasi generalizzazione.

QUANDO LO STUDENTE SBAGLIA:
- Individua ESATTAMENTE dove si trova l'errore.
- Usa il tag <ERRORE> spiegando il ragionamento errato e perché è sbagliato.
- Poi mostra il procedimento corretto passo per passo.

STRUTTURA DELLE SPIEGAZIONI:
- Prima un esempio concreto e intuitivo, poi la regola generale.
- Risoluzione di esercizi: usa "Passo 1:", "Passo 2:", ecc.
- Chiudi sempre con una domanda di verifica o un mini-esercizio se appropriato.
- Usa **grassetto** per i termini chiave."""


@app.route("/")
def index():
    return send_file("tutor.html")


@app.route("/almanacco")
def almanacco():
    oggi = date.today().isoformat()

    # Controlla se esiste già la cache di oggi
    if os.path.exists(ALMANACCO_FILE):
        with open(ALMANACCO_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        if cache.get("data") == oggi:
            return jsonify(cache["contenuto"])

    # Genera un nuovo almanacco per oggi
    prompt = (
        "Genera l'almanacco scientifico di oggi per studenti di scuola media (11-13 anni).\n"
        "Rispondi SOLO con un oggetto JSON valido, senza testo prima o dopo, con questa struttura esatta:\n\n"
        "{\n"
        '  "quesito_laterale": "un quesito di pensiero laterale breve, intrigante, con soluzione non ovvia",\n'
        '  "soluzione_quesito": "la spiegazione della soluzione, chiara e breve",\n'
        '  "curiosita": "una curiosità scientifica o matematica sorprendente, 2-3 frasi",\n'
        '  "indovinello": "un indovinello matematico o logico adatto a 11-13 anni",\n'
        '  "soluzione_indovinello": "la risposta dell\'indovinello",\n'
        '  "storia_titolo": "nome del matematico, scoperta o evento storico di oggi",\n'
        '  "storia_testo": "racconto breve (4-5 frasi) di un episodio di storia della matematica: '
        'un matematico, una scoperta, un aneddoto curioso, adatto a 11-13 anni e scritto in modo coinvolgente"\n'
        "}\n\n"
        "Varia ogni giorno il personaggio o l'episodio storico (es. Pitagora, Talete, Euclide, Archimede, "
        "Ipazia, Fibonacci, Cartesio, Gauss, Newton, Eulero, Sofia Kovalevskaya, Ada Lovelace, Ramanujan, ecc.) "
        "e l'ambito (algebra, geometria, numeri, fisica, astronomia). Evita di ripetere sempre Pitagora e Archimede."
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    testo = response.content[0].text.strip()
    # Rimuove eventuali fence markdown ```json ... ```
    testo = testo.replace("```json", "").replace("```", "").strip()

    contenuto = json.loads(testo)

    with open(ALMANACCO_FILE, "w", encoding="utf-8") as f:
        json.dump({"data": oggi, "contenuto": contenuto}, f, ensure_ascii=False)

    return jsonify(contenuto)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    messages = data.get("messages", [])

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM,
        messages=messages
    )

    return jsonify({"reply": response.content[0].text})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
