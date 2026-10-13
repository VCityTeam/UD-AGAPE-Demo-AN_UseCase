"""Print the source metadata the documents of gratteciel-documents.ttl are built from.

Usage:
    python source_metadata.py "File:<Wikimedia Commons file name>" ... merimee:<REF> ...

For a Wikimedia Commons file: media and page URLs, upload date, and the
author, date, credit (e.g. a Numelyo digital ID), licence and description
recorded by Commons. For a Mérimée record (POP, French Ministry of Culture):
title, dating, architects, protection, label, addresses, coordinates, history
and the date the record was put online.

Example:
    python source_metadata.py "File:Plan façade Nord de l'hôtel de ville de Villeurbanne.png" merimee:PA00118150
"""

import json
import re
import sys
import urllib.parse
import urllib.request

USER_AGENT = "UD-AGAPE-Demo-AN_UseCase/1.0 (https://github.com/VCityTeam/UD-AGAPE-Demo-AN_UseCase)"
MERIMEE_FIELDS = ["TICO", "DENO", "SCLE", "DATE", "AUTR", "DPRO", "PPRO", "PROT", "LABEL", "DLAB",
                  "ADRS", "COM", "INSEE", "DMIS", "DMAJ", "POP_COORDONNEES", "HIST"]


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def strip_html(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text or "")).strip()


def commons(titles):
    query = urllib.parse.urlencode({"action": "query", "prop": "imageinfo", "iiprop": "url|timestamp|extmetadata",
                                    "titles": "|".join(titles), "format": "json"})
    pages = json.loads(fetch(f"https://commons.wikimedia.org/w/api.php?{query}"))["query"]["pages"]
    for page in pages.values():
        print(f"== {page['title']}")
        if "imageinfo" not in page:
            print("   not found")
            continue
        info = page["imageinfo"][0]
        meta = info["extmetadata"]
        print(f"   file:     {info['url'].split('?')[0]}")
        print(f"   page:     {info['descriptionurl']}")
        print(f"   uploaded: {info['timestamp']}")
        for key in ("DateTimeOriginal", "Artist", "Credit", "LicenseShortName", "ImageDescription"):
            print(f"   {key}: {strip_html(meta.get(key, {}).get('value'))}")


def merimee(reference):
    url = f"https://pop.culture.gouv.fr/notice/merimee/{reference}"
    text = fetch(url).replace('\\"', '"')
    print(f"== Mérimée {reference} ({url})")
    for field in MERIMEE_FIELDS:
        match = re.search(r'"%s":(\{[^}]*\}|\[[^\]]*\]|"(?:[^"\\]|\\.)*")' % field, text)
        if match and match.group(1) not in ("[]", '""'):
            print(f"   {field}: {match.group(1)[:600]}")


def main(arguments):
    titles = [a for a in arguments if a.startswith("File:")]
    if titles:
        commons(titles)
    for argument in arguments:
        if argument.startswith("merimee:"):
            merimee(argument.split(":", 1)[1])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
