# 🎯 Okey Yazboz Okuyucu

El yazısıyla yazılmış Okey yazboz kağıdının fotoğrafını yükle, yapay zeka puanları otomatik okusun ve hesaplasın.

## Nasıl Çalışır?

1. Yazboz kağıdının fotoğrafını çek veya galeriden seç
2. **Analiz Et** butonuna bas
3. Takım puanları ve kazanan otomatik gösterilir

## Özellikler

- Gemini 2.5 Flash ile görüntü analizi
- El yazısı tanıma
- İki takım toplam puan karşılaştırması
- Mobil uyumlu arayüz

## Kurulum (Lokal)

### Gereksinimler

- Python 3.9+
- Gemini API key ([Google AI Studio](https://aistudio.google.com/)'dan ücretsiz alınabilir)

### Adımlar

```bash
# Bağımlılıkları yükle
pip install -r requirements.txt

# API key'i ayarla
echo "GEMINI_API_KEY=senin_api_keyin" > .env

# Sunucuyu başlat
python server.py
```

Tarayıcıda aç: [http://localhost:5000](http://localhost:5000)

## Vercel'e Deploy

```bash
npm i -g vercel
vercel
```

Vercel dashboard'dan `GEMINI_API_KEY` ortam değişkenini ekle.

## Proje Yapısı

```
okeyproje/
├── public/
│   └── index.html      # Arayüz
├── api/
│   └── analyze.py      # Vercel serverless fonksiyon
├── server.py           # Lokal geliştirme sunucusu
├── requirements.txt    # Python bağımlılıkları
└── vercel.json         # Vercel konfigürasyonu
```

## Teknolojiler

- **Backend:** Python, Google Gemini API
- **Frontend:** Vanilla HTML/CSS/JS
- **Deploy:** Vercel
