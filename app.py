from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import anthropic
import os
import json
import random
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
4. A domande che esulano dal programma di matematica e scienze 11-13, rispondi in modo simpatico che esulano dal programma, anche si strettamente di matematica (come ad esempio la trigonometria)
5. Per il prodotto usa sempre il punto e non la x.

GESTIONE DELLE FIGURE GEOMETRICHE E ASTRAZIONI:
- Quando uno studente avrebbe bisogno di vedere una figura geometrica (triangolo, cerchio, retta, angolo, ecc.), NON descriverla soltanto: guidalo a costruirla da solo con GeoGebra Geometry, lo strumento di disegno disponibile a fianco della chat.
- Usa il tag <DISEGNA> con istruzioni chiare, numerate e nell'ordine in cui vanno eseguite, scritte come comandi pratici per i pulsanti di GeoGebra (es. "Punto", "Segmento", "Poligono", "Angolo", "Retta perpendicolare", "Circonferenza"). Esempio:
  <DISEGNA>
  1. Disegna un punto A in basso a sinistra e un punto B in basso a destra (strumento Punto).
  2. Collega A e B con un segmento.
  3. Disegna un punto C più in alto, poi unisci A-C e B-C per formare il triangolo.
  4. Usa lo strumento Angolo per misurare l'angolo in C.
  </DISEGNA>
- Usa <DISEGNA> con parsimonia, solo quando costruire la figura aiuta davvero a capire (non per ogni minima menzione di geometria).
- Per insiemi (Eulero-Venn): NON usare cerchi sovrapposti con lettere e NON suggerire di disegnarli. Usa invece la notazione algebrica degli insiemi e spiega con esempi concreti (es. "A = {2, 4, 6, 8} sono i numeri pari minori di 10").
- Per concetti astratti (funzioni, proporzionalità): usa esempi numerici concreti prima di qualsiasi generalizzazione.

GESTIONE DELLE TABELLE:
- Anche quando un confronto o un elenco di dati è più chiaro in forma tabellare, usa SEMPRE un elenco. La formattazione delle tabelle html è illeggibile

QUANDO LO STUDENTE SBAGLIA:
- Individua ESATTAMENTE dove si trova l'errore.
- Usa il tag <ERRORE> spiegando il ragionamento errato e perché è sbagliato.
- Poi mostra il procedimento corretto passo per passo.

STRUTTURA DELLE SPIEGAZIONI:
- Prima un esempio concreto e intuitivo, poi la regola generale.
- Risoluzione di esercizi: usa "Passo 1:", "Passo 2:", ecc.
- Chiudi sempre con una domanda di verifica o un mini-esercizio se appropriato.
- Usa **grassetto** per i termini chiave.

MOMENTI WOW (per mantenere alta l'attenzione):
Dopo una spiegazione o un esercizio risolto, NON SEMPRE ma quando ha senso (circa 1 volta ogni 2-3 scambi, mai meccanicamente), chiudi con uno di questi tipi di rilancio, variando il tipo usato:
- Sfida-lampo: una domanda simile ma leggermente diversa, da risolvere "a mente" o in pochi secondi.
- Collegamento sorprendente: come lo stesso concetto si applica a qualcosa di inaspettato nella vita reale, nello sport, nella tecnologia, nella natura.
- Trucco da "iniziato": una scorciatoia, un metodo mentale veloce, o un modo furbo di vedere il problema che i matematici/scienziati usano.
- Domanda capovolta: "e se cambiasse [una variabile]? Cosa pensi succederebbe?" per stimolare intuizione prima di spiegare.
Tieni questi momenti brevi (1-3 frasi), mai forzati, e mai nello stesso schema due volte di fila."""


@app.route("/")
def index():
    return send_file("tutor.html")


# Lista di temi storici - (personaggio/episodio, ambito)
TEMI_STORIA = [
    ("Pitagora", "geometria"),
    ("Talete", "geometria"),
    ("Euclide", "geometria"),
    ("Archimede", "fisica e geometria"),
    ("Ipazia", "astronomia e matematica"),
    ("Fibonacci", "numeri"),
    ("Cartesio", "algebra e geometria"),
    ("Gauss", "numeri e algebra"),
    ("Newton", "fisica e calcolo"),
    ("Eulero", "algebra e analisi"),
    ("Sofia Kovalevskaya", "analisi"),
    ("Ada Lovelace", "informatica e algoritmi"),
    ("Ramanujan", "numeri"),
    ("Emmy Noether", "algebra"),
    ("Al-Khwarizmi", "algebra"),
    ("Leibniz", "calcolo"),
    ("Blaise Pascal", "probabilità"),
    ("Alan Turing", "informatica e logica"),
    ("Georg Cantor", "infinito e insiemi"),
    ("Talete e la misura delle piramidi", "geometria applicata"),
]

STORIA_HISTORY_FILE = "storia_history.json"

def scegli_tema_storia():
    try:
        with open(STORIA_HISTORY_FILE, "r", encoding="utf-8") as f:
            usati_recenti = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        usati_recenti = []

    disponibili = [t for t in TEMI_STORIA if t[0] not in usati_recenti]
    if not disponibili:
        disponibili = TEMI_STORIA  # reset se esauriti

    scelto = random.choice(disponibili)

    usati_recenti.append(scelto[0])
    usati_recenti = usati_recenti[-10:]  # tiene solo gli ultimi 10
    with open(STORIA_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(usati_recenti, f, ensure_ascii=False)

    return scelto


@app.route("/almanacco")
def almanacco():
    oggi = date.today().isoformat()
    # Controlla se esiste già la cache di oggi
    if os.path.exists(ALMANACCO_FILE):
        with open(ALMANACCO_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        if cache.get("data") == oggi:
            return jsonify(cache["contenuto"])

    # Scegli il tema storico in modo casuale (non lasciarlo decidere al modello)
    personaggio, ambito = scegli_tema_storia()

    # Genera un nuovo almanacco per oggi
    prompt = (
        f"Genera l'almanacco scientifico di ({oggi}) per studenti di scuola media (11-13 anni).\n"
        "Rispondi SOLO con un oggetto JSON valido, senza testo prima o dopo, con questa struttura esatta:\n\n"
        "{\n"
        '  "quesito_laterale": "un quesito di pensiero laterale breve, intrigante, con soluzione non ovvia",\n'
        '  "soluzione_quesito": "la spiegazione della soluzione, chiara e breve",\n'
        '  "curiosita": "una curiosità scientifica o matematica sorprendente, 2-3 frasi",\n'
        '  "indovinello": "un indovinello matematico o logico adatto a 11-13 anni",\n'
        '  "soluzione_indovinello": "la risposta dell\'indovinello",\n'
        '  "storia_titolo": "nome del matematico, scoperta o evento storico di oggi",\n'
        '  "storia_testo": "racconto breve (4-5 frasi) di un episodio di storia della matematica, '
        'adatto a 11-13 anni e scritto in modo coinvolgente"\n'
        "}\n\n"
        f"Per storia_titolo e storia_testo, scrivi OBBLIGATORIAMENTE di: {personaggio} "
        f"(ambito: {ambito}). Scegli un aneddoto o episodio specifico e poco scontato legato a questa figura, "
        "evitando il fatto più ovvio/conosciuto se possibile."
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        temperature=1.0,
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
        temperature=1.0,
        system=SYSTEM,
        messages=messages
    )

    return jsonify({"reply": response.content[0].text})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
