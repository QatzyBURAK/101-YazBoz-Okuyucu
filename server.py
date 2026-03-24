import os
import json
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler

# .env dosyasından yükle (varsa)
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

from api.analyze import hesapla

from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    # Gelistirme icin: GEMINI_API_KEY ortam degiskeni tanimli olmali
    # Ornek: set GEMINI_API_KEY=YOUR_KEY (Windows) veya export GEMINI_API_KEY=YOUR_KEY (Linux/Mac)
    raise RuntimeError("GEMINI_API_KEY ortam degiskeni tanimli degil!")

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
        return None, None, {}

    boundary_bytes = ("--" + boundary).encode()
    parts = body.split(boundary_bytes)

    image_data = None
    mime = "image/jpeg"
    fields = {}

    for part in parts:
        if b"\r\n\r\n" not in part:
            continue
        headers, data = part.split(b"\r\n\r\n", 1)
        data = data.rstrip(b"\r\n--")
        headers_str = headers.decode("utf-8", errors="ignore")

        if "filename" in headers_str:
            if "image/png" in headers_str:
                mime = "image/png"
            elif "image/webp" in headers_str:
                mime = "image/webp"
            image_data = data
        else:
            # Form alanı
            import re
            m = re.search(r'name="([^"]+)"', headers_str)
            if m:
                fields[m.group(1)] = data.decode("utf-8", errors="ignore")

    return image_data, mime, fields


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"  {args[0]} {args[1]}")

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            with open("index.html", "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/api/analyze":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        content_type = self.headers.get("Content-Type", "")
        body = self.rfile.read(content_length)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        try:
            image_data, mime_type, fields = parse_multipart(body, content_type)
            if not image_data:
                raise Exception("Resim alinamadi")

            print(f"  Resim alindi ({len(image_data)} bytes), Gemini'ye gonderiliyor...")

            client = genai.Client(api_key=GEMINI_API_KEY)
            image_part = types.Part.from_bytes(data=image_data, mime_type=mime_type or "image/jpeg")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[PROMPT, image_part]
            )

            raw = response.text.strip()
            print(f"  Gemini yaniti:\n{raw}\n")

            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            else:
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start != -1 and end > start:
                    raw = raw[start:end]

            data = json.loads(raw)
            result = hesapla(data)
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

        except Exception as e:
            print(f"  HATA: {e}")
            self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


if __name__ == "__main__":
    port = 5000
    print(f"Server calisiyor: http://localhost:{port}")
    print("Durdurmak icin CTRL+C\n")
    HTTPServer(("", port), Handler).serve_forever()
