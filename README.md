# conllu2vert

Konvertiert CoNLL-U-Dateien in ein Vertical-File, das als Korpus in Sketch
Engine geladen werden kann. Jede Eingabedatei wird zu einem `<doc>`-Element;
Sätze werden als `<s>`-Elemente ausgezeichnet. Die Ausgabe ist eine einzige
Korpusdatei, in der die Dokumente in Sketch Engine auswählbar sind.

## Verwendung

```bash
uv sync
uv run conllu2vert
```

Standardmäßig werden alle `*.conllu` aus `src/data/input` gelesen und nach
`src/data/output/pahlavi.vert` geschrieben. Zusätzlich entsteht die passende
Registry-Vorlage `src/data/output/pahlavi.registry`.

Beispiel mit expliziten Pfaden:

```bash
uv run conllu2vert \
  --input-dir src/data/input \
  --output src/data/output/pahlavi.vert \
  --registry src/data/output/pahlavi.registry
```

Einzelne Dateien lassen sich auch direkt übergeben:

```bash
uv run conllu2vert src/data/input/Dk5-B_conllu.conllu --no-registry
```

## Optionen

| Option | Bedeutung |
| --- | --- |
| `FILE ...` | Explizite CoNLL-U-Dateien; sonst alle `*.conllu` aus `--input-dir` |
| `-i, --input-dir` | Eingabeverzeichnis (Default: `src/data/input`) |
| `-o, --output` | Vertical-Datei (Default: `<output-dir>/<corpus-name>.vert`) |
| `--output-dir` | Verzeichnis für Default-Ausgabe (Default: `src/data/output`) |
| `--corpus-name` | Name für Ausgabe und Registry (Default: `pahlavi`) |
| `--registry` | Pfad der Registry-Datei |
| `--no-registry` | Keine Registry erzeugen |
| `--corpora-path` | `PATH` in der Registry (Default: `/corpora/<corpus-name>`) |
| `--vertical-path` | `VERTICAL` in der Registry (Default: `/corpora/src/<corpus-name>.vert`) |
| `--strict` | Bei fehlerhaften Token-Zeilen abbrechen statt überspringen |
| `-q, --quiet` | Nur Fehler ausgeben |

## Format

Die Spaltenreihenfolge im Vertical-File ist:

```
word    lemma    tag    feats    deprel    sense
```

Beispiel:

```
<doc id="Dk5">
<s id="Dk5-B_s1">
pērōzgarīh	pērōzgarīh	NOUN	Animacy=Inan	root	victoriousness
...
</s>
</doc>
```

Die Registry wird aus derselben Attributliste erzeugt und passt daher exakt
zur Ausgabe:

```
PATH /corpora/pahlavi
VERTICAL "/corpora/src/pahlavi.vert"
ENCODING "utf-8"

ATTRIBUTE word
ATTRIBUTE lemma
ATTRIBUTE tag
ATTRIBUTE feats
ATTRIBUTE deprel
ATTRIBUTE sense

STRUCTURE doc {
    ATTRIBUTE id
}
STRUCTURE s {
    ATTRIBUTE id
}
```

Vor dem Laden in Sketch Engine die Pfade in der Registry an die eigene
Serverumgebung anpassen und die Vertical-Datei dorthin kopieren.

## Konvertierungsregeln

- Nur echte Oberflächen-Tokens werden übernommen. Multiword-Tokens (`1-2`),
  leere Knoten (`4.1`) und Zeilen ohne numerische ID werden übersprungen.
- `# text_id` bestimmt die Dokument-ID; fehlt sie, wird der Dateiname genutzt.
- `# sent_id` bestimmt die Satz-ID; fehlt sie, wird `<doc>_s<N>` generiert.
- Mehrfache Werte in Lemma und Sense (`a|b`, `Sense=x|Sense=y`) werden mit
  `; ` verbunden, z. B. `x; y`.
- Kaputte CSV-quotierte Kommentarzeilen werden repariert bzw. ignoriert,
  ohne als Token zu gelten.
- `feats` bleibt unverändert; dort sind `|`-getrennte Merkmale korrekt.

## Tests

```bash
uv run pytest
```
