# conllu2vert

Konvertiert CoNLL-U-Dateien in ein Vertical-File, das als Korpus in Sketch
Engine geladen werden kann. Jede Eingabedatei wird zu einem
`<doc file="..." n="...">`-Element; Sätze werden als `<s>`-Elemente
ausgezeichnet. Die Ausgabe ist eine einzige Korpusdatei, in der die Dokumente
in Sketch Engine auswählbar sind.

## Verwendung

```bash
uv sync
uv run conllu2vert
```

Standardmäßig werden alle `*.conllu` und `*.tsv` aus `src/data/input` gelesen und nach
`src/data/output/czerofive.vert` geschrieben. Zusätzlich entsteht die passende
Registry-Vorlage `src/data/output/czerofive.registry`.

Beispiel mit expliziten Pfaden:

```bash
uv run conllu2vert \
  --input-dir src/data/input \
  --output src/data/output/czerofive.vert \
  --registry src/data/output/czerofive.registry
```

Einzelne Dateien lassen sich auch direkt übergeben:

```bash
uv run conllu2vert src/data/input/Dk5-B_conllu.tsv --no-registry
```

## Optionen

| Option | Bedeutung |
| --- | --- |
| `FILE ...` | Explizite CoNLL-U-Dateien; sonst alle `*.conllu`/`*.tsv` aus `--input-dir` |
| `-i, --input-dir` | Eingabeverzeichnis (Default: `src/data/input`) |
| `-o, --output` | Vertical-Datei (Default: `<output-dir>/<corpus-name>.vert`) |
| `--output-dir` | Verzeichnis für Default-Ausgabe (Default: `src/data/output`) |
| `--corpus-name` | Name für Ausgabe, Registry-PATH und Standardpfade (Default: `czerofive`) |
| `--registry` | Pfad der Registry-Datei |
| `--no-registry` | Keine Registry erzeugen |
| `--maintainer` | `MAINTAINER` in der Registry |
| `--info` | `INFO` in der Registry |
| `--name` | `NAME` in der Registry |
| `--language` | `LANGUAGE` in der Registry |
| `--indexed-path` | `PATH` für indizierte Daten (Default: `/corpora/<corpus-name>/indexed/`) |
| `--vertical-path` | `VERTICAL` in der Registry (Default: `/corpora/<corpus-name>/vertical/source`) |
| `--strict` | Bei fehlerhaften Token-Zeilen abbrechen statt überspringen |
| `-q, --quiet` | Nur Fehler ausgeben |

## Format

Die Spaltenreihenfolge im Vertical-File ist:

```
word    lemma    tag    feats    deprel    sense
```

Dokumente werden global von 1 an nummeriert:

```
<doc file="Dk5-B" n="1">
<s id="Dk5-B_s1">
pērōzgarīh	pērōzgarīh	NOUN	Animacy=Inan	root	victoriousness
...
</s>
</doc>
<doc file="GA-K20" n="2">
...
</doc>
```

Die Registry wird aus derselben Attributliste erzeugt und passt daher exakt
zur Ausgabe:

```
MAINTAINER "thomas.jurczyk@googlemail.com"
INFO "C05corpus"
NAME "C05 Corpus"
PATH czerofive
ENCODING "UTF-8"
LANGUAGE "Pahlavi"

PATH   '/corpora/czerofive/indexed/'
VERTICAL  '/corpora/czerofive/vertical/source'

INFOHREF "XXX"
TAGSETDOC "XXX"

FULLREF "doc.file,doc.n"

ATTRIBUTE word
ATTRIBUTE lemma
ATTRIBUTE tag
ATTRIBUTE feats
ATTRIBUTE deprel
ATTRIBUTE sense

STRUCTURE doc {
    ATTRIBUTE file
    ATTRIBUTE n
}

STRUCTURE s {
    ATTRIBUTE id
}
```

`INFOHREF` und `TAGSETDOC` bleiben als Platzhalter (`XXX`) stehen und können
manuell ergänzt werden. Die Pfade lassen sich über die CLI oder direkt in der
Registry an die eigene Serverumgebung anpassen.

## Konvertierungsregeln

- Nur echte Oberflächen-Tokens werden übernommen. Multiword-Tokens (`1-2`) und
  leere Knoten (`4.1`) werden übersprungen, weil die einzelnen Oberflächen-Tokens
  bereits vorhanden sind.
- Zeilen mit `_` als Token-ID werden als normale Tokens übernommen. Die
  Token-ID wird im Vertical-Format ohnehin nicht ausgegeben, und die Zeilen
  stehen bereits an der richtigen Position im Satz. Sie werden im Report als
  `tokens without numeric id` ausgewiesen.
- Das Attribut `file` ist der Dateiname ohne Endung und ohne `_conllu`-Suffix,
  z. B. `ADM-MK` für `ADM-MK_conllu.tsv`. Jede Eingabedatei ergibt genau ein
  Dokument; `# text_id` wird dafür nicht verwendet und darf leer sein oder sich
  wiederholen.
- `n` wird global über alle Dokumente fortlaufend ab 1 vergeben.
- `# sent_id` bestimmt die Satz-ID; fehlt sie oder ist sie `_`, wird
  `<file>_s<N>` generiert. Kollidiert eine generierte ID mit einer echten ID
  derselben Datei, wird die nächste freie Nummer verwendet.
- Mehrfache Werte in Lemma und Sense (`a|b`, `Sense=x|Sense=y`) werden mit
  `; ` verbunden, z. B. `x; y`.
- Kaputte CSV-quotierte Kommentarzeilen werden repariert bzw. ignoriert,
  ohne als Token zu gelten.
- `feats` bleibt unverändert; dort sind `|`-getrennte Merkmale korrekt.

## Tests

```bash
uv run pytest
```
