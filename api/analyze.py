import os
import json
from http.server import BaseHTTPRequestHandler
from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

PROMPT = """Bu bir el yazisiyla yazilmis Okey yazboz kagidinin fotografidir.

Bu kagit iki takim bolumunden olusur:
- Bir takimin adi kagida yazilir, altindaki TUM sayilar o takima aittir.
- Diger takimin adi yazilinca artik o takimin sayilari baslar.

ONEMLI KURALLAR:
- Yatay cizgiler sadece yazim kolayligi icin cizilmistir, oyun siniri DEGILDIR.
- Sutun numaralari (1, 2, 3...) oyun siniri DEGILDIR, sadece kagit sutunlaridir.
- Bir takimin adi yazildiktan sonra diger takimin adi gorulene kadar
  hangi sutunda olursa olsun TUM sayilar o takima aittir.

ADIM 1 - Kagittaki iki takim adini bul.

ADIM 2 - Her takimin TUM sayilarini oku (COKK DIKKATLI):
- Yatay cizgi ustu ve alti fark etmez, hepsini dahil et
- Sayilari soldan saga, yukari asagi tara, hic birini atlama
- 1 ile 7, 0 ile 6, 3 ile 8 karismasi yapma, dikkatli bak
- Negatif sayilar da olabilir
- Belirsiz sayilarda en mantikli degeri tahmin et ama ATLAMA

ADIM 3 - SADECE su JSON formatinda dondur, baska hicbir sey yazma:
{
  "takim1": "LATTE",
  "takim2": "MADDE",
  "TU": [takim1in_tum_sayilari],
  "KB": [takim2nin_tum_sayilari]
}

- takim1 ve takim2 alanlarina kagittaki GERCEK isimleri yaz
- TU = takim1'in sayilari, KB = takim2'nin sayilari
- Sadece tam sayilari yaz, harfleri alma
"""


def parse_multipart(body, content_type):
    boundary = None
    for part in content_type.split(";"):
        part = part.strip()
        if part.startswith("boundary="):
            boundary = part[len("boundary="):].strip()
            break
    if not boundary:
        return None, None

    boundary_bytes = ("--" + boundary).encode()
    parts = body.split(boundary_bytes)

    for part in parts:
        if b"\r\n\r\n" in part:
            headers, data = part.split(b"\r\n\r\n", 1)
            data = data.rstrip(b"\r\n--")
            headers_str = headers.decode("utf-8", errors="ignore")
            mime = "image/jpeg"
            if "image/png" in headers_str:
                mime = "image/png"
            elif "image/webp" in headers_str:
                mime = "image/webp"
            if b"Content-Disposition" in headers and b"filename" in headers:
                return data, mime
    return None, None


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        content_type = self.headers.get("Content-Type", "")
        body = self.rfile.read(content_length)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        try:
            if not GEMINI_API_KEY:
                raise Exception("GEMINI_API_KEY ayarlanmamış")

            image_data, mime_type = parse_multipart(body, content_type)
            if not image_data:
                raise Exception("Resim alınamadı")

            client = genai.Client(api_key=GEMINI_API_KEY)

            image_part = types.Part.from_bytes(
                data=image_data,
                mime_type=mime_type or "image/jpeg"
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[PROMPT, image_part]
            )

            raw = response.text.strip()

            # ```json ``` temizle
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            else:
                # JSON bloğunu bul (başında/sonunda metin varsa)
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start != -1 and end > start:
                    raw = raw[start:end]

            data = json.loads(raw)
            result = hesapla(data)
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

        except Exception as e:
            error = {"error": str(e)}
            self.wfile.write(json.dumps(error, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def _parse_list(lst):
    return [int(x) for x in lst if str(x).lstrip('-').isdigit()]

def hesapla(data):
    takim1 = data.get("takim1", "Takim 1")
    takim2 = data.get("takim2", "Takim 2")

    tu_list = _parse_list(data.get("TU", []))
    kb_list = _parse_list(data.get("KB", []))

    toplam_TU = sum(tu_list)
    toplam_KB = sum(kb_list)

    fark = abs(toplam_TU - toplam_KB)
    if toplam_TU < toplam_KB:
        one_cikan_kisa = "TU"
    elif toplam_KB < toplam_TU:
        one_cikan_kisa = "KB"
    else:
        one_cikan_kisa = "BERA"

    return {
        "takim1": takim1,
        "takim2": takim2,
        "oyunlar": [{"sutun": 1, "TU_toplam": toplam_TU, "KB_toplam": toplam_KB}],
        "toplam": {"TU": toplam_TU, "KB": toplam_KB},
        "one_cikan_kisa": one_cikan_kisa,
        "fark": fark,
    }
