# StoryToText UI/UX Design Brief for Stitch

## 1. Belgenin Amaci

Bu belge, mevcut `story_to_text` urununun sifirdan yeniden tasarlanmis bir web tabanli micro SaaS versiyonu icin UI/UX briefigidir. Amac:

- Portfolyo icin guclu, premium gorunen bir urun deneyimi tanimlamak
- Stitch gibi UI tasarim araclarina verilebilecek kadar net ekran ve akis tanimi sunmak
- Mevcut teknik urun yeteneklerini koruyup bunu odeme sistemli bir SaaS deneyimine cevirmek
- Hem pazarlama sayfalarini hem de uygulama ici deneyimi tek bir tasarim sisteminde toplamak

Bu brief, tasarim odaklidir. Kod implementasyonu tarif etmez; urun davranisi, bilgi mimarisi ve ekran beklentilerini tanimlar.

## 2. Urun Ozeti

### Calisma Adi

StoryToText

Alternatif marka isimleri:

- ClipScribe
- ReelScript
- VidTranscript

Bu brief icin `StoryToText` ismi kullanilacaktir.

### Kisa Urun Tanimi

StoryToText, kullanicilarin Instagram Reels, TikTok videolari, YouTube videolari veya dogrudan yukledikleri medya dosyalarindan hizli sekilde transcript cikarmasini saglayan web tabanli bir transcription SaaS urunudur. Urun ayni zamanda API key ile cagrilabilen bir developer arayuzu sunar ve Codex, Claude benzeri agent/workflow araclarina tool olarak baglanabilir.

### Temel Deger Onerisi

- Tek linkle sosyal video transcript alma
- YouTube dahil coklu video kaynagindan transcript alma
- Profil bazli toplu transcript cikarabilme
- Dosya yukleyerek batch transcription
- Viral videolardan hook, script ve talking point cikarmaya uygun temiz metin elde etme
- Hemen kopyalanabilir, indirilebilir ve islenebilir metin cikisi
- Teknik olmayan kullanicilar icin yalnizca URL veya dosya ile calisan kolay deneyim
- Gelistiriciler ve AI-agent workflow'lari icin API key tabanli kullanim
- Transcript'i AI araclarina kolayca aktarilabilir bir ham girdi haline getirme

### Urun Vaadi

"Turn viral videos into prompt-ready text for your content workflow."

## 3. Problem Tanimi

Hedef kullanicilar sosyal medya videolarindan metin cikarmak istiyor fakat mevcut surecler su sorunlari yasatiyor:

- Videoyu ayri bir aracla indirmek gerekiyor
- Sonra baska bir araca yukleyip transcript almak gerekiyor
- Toplu islem yapmak zor
- Sonuc bazen duzensiz, indirilemez veya tekrar kullanilabilir formatta olmuyor
- Profesyonel bir SaaS deneyimi yerine daginik araclar kullaniliyor
- Bunu agentic workflow'lara baglamak isteyen gelistiriciler icin hazir bir tool/API yuzeyi bulunmuyor
- Viral icerik arastirmasi yapan creator'lar icin videodan kullanisli metin cikarmak fazla manuel kaliyor
- AI ile yeni script, caption veya hook uretmek isteyenler icin temiz input toplamak zaman aliyor

StoryToText bu sorunu tek urunde cozer:

- URL yapistir
- Gerekirse profil tarat
- Transcript al
- Kopyala, indir, yeniden kullan
- Gerekiyorsa API key ile agent veya otomasyon akisindan cagir
- Transcript'i AI ile yeni icerik uretim akisinin girdisi olarak kullan

## 4. Hedef Kullanicilar

Ana hedef kitle, viral icerik ureten veya viral icerikleri AI workflow'larinda analiz edip yeniden yazan creator'lardir. Ikincil kitle, bunu ekip icinde operasyonellestiren studio/agency yapilari ve developer kullanicilardir.

### Persona 1: AI-First Creator / Faceless Operator

Ihtiyaclari:

- Viral Reels, TikTok ve YouTube videolarindan transcript almak
- Transcript'i Claude, Codex veya benzeri AI araclarina verip yeni script uretmek
- Hook, opening line, structure ve talking points cikarmak
- Hacimli icerik operasyonunu hizlandirmak

### Persona 2: Solo Creator / Personal Brand

Ihtiyaclari:

- Kendi videolarini metne cevirmek
- Kendi konusma tarzi ve icerik yapisini tekrar kullanmak
- Videolardan caption, carousel, thread, newsletter ve short script cikarmak
- Icerik arsivini aranabilir hale getirmek

### Persona 3: Content Studio / Agency Operator

Ihtiyaclari:

- Birden fazla hesabin videolarini hizli analiz etmek
- Rakip arastirmasi ve format analizi yapmak
- Niche icinde hangi hook ve script yapilarinin calistigini bulmak
- Toplu export alip ekibe dagitmak

### Persona 4: Repurposing Editor / Growth Operator

Ihtiyaclari:

- Client videolarini yazili icerige cevirmek
- Kisa surede deliverable uretmek
- Upload ve export odakli basit, guvenilir bir arac kullanmak
- Uzun transcript'ten yeni kisa icerik parcaciklari uretmek icin temiz girdi almak

### Persona 5: Developer / AI Automation Builder

Ihtiyaclari:

- Bir LLM agent veya internal tool icinden video transcript almak
- API key ile guvenli sekilde cagrilabilir bir servis kullanmak
- JSON formatinda sonuc almak
- Codex, Claude veya benzeri araclara kolay entegre olabilmek

### Temel kullanim senaryolari

- Viral rakip videolarin transcript'ini alip AI ile yeni script varyasyonlari uretmek
- Kendi videolarini transcriptleyip caption, hooks ve repurposed content cikarmak
- Belirli niche hesaplari batch import ile tarayip icerik pattern'lerini incelemek
- Transcript sonucunu agent pipeline'inda ham girdi olarak kullanmak

## 5. Urun Kapsami

Bu bolumde in-scope olarak listelenen tum ozellikler ayni anda production'a cikacak launch kapsamidir. Bu brief, kademeli rollout veya v1/v2 ayrimi uzerine kurulu degildir.

### Mevcut cekirdek kabiliyetler

Bu brief, mevcut uygulamanin gercek yeteneklerini temel alir:

- Tekil Instagram Reel URL transcription
- Tekil TikTok video URL transcription
- Instagram profilinden public Reels cekip toplu transcription
- TikTok profilinden public videolari cekip toplu transcription
- Lokal video veya audio dosyasi yukleyip transcription
- Dil secimi
- Model secimi
- Transcript sonucu
- JSON ve TXT export

### Bu yeni urun vizyonu icin eklenecek kabiliyetler

- Tekil YouTube video URL transcription
- YouTube playlist veya channel importu
- API key yonetimi
- REST API ile transcription job baslatma
- Job status / result endpoint'leri
- Codex / Claude / benzeri agentler icin tool wrapper veya MCP katmani
- API kullanim metrikleri ve limit takibi

### SaaS olarak eklenecek katmanlar

- Kullanici hesaplari
- Dashboard
- Job history
- Kullanim limiti ve kredi mantigi
- Pricing
- Subscription billing
- Stripe checkout / customer portal
- Upgrade ve paywall ekranlari
- Basit onboarding
- API keys
- Developer docs
- Integrations / tool setup
- Web ve API kullanimini tek cati altinda gosteren usage modeli

### Bilincli olarak launch scope disinda tutulanlar

- Video editing
- Otomatik subtitle burn-in
- Social scheduling
- Team collaboration
- Shared workspaces
- AI summary, rewrite, translation gibi ikinci derece ozellikler
- Chrome extension
- Mobile app
- Tam kapsamli generic automation platform'u
- YouTube tarafinda channel analytics veya kanal yonetimi

## 6. Urun Hedefleri

- Ilk bakista guven veren premium bir SaaS hissi yaratmak
- Landing page ziyaretcisini hizli sekilde "try now" veya "start free" e yonlendirmek
- Kullanicinin ilk transcript sonucuna 2-3 dakika icinde ulasmasini saglamak
- Tek seferlik tool gorunumunden cikarak tekrar kullanilabilir bir panel urunu gibi hissettirmek
- Billing ve usage mantigi sayesinde urunun monetize edilebilir oldugunu net gostermek
- Portfolyoda "real product thinking" seviyesi gostermek
- Web uygulamasi ile developer product'in ayni marka altinda birlikte cozuldugunu gostermek
- Urunun creator economy icinde gercek bir growth/content operations araci gibi konumlandigini gostermek

## 7. Tasarim Ilkeleri

### Genel ton — Uc kelimede: Editorial. Warm. Credible.

- Premium ama soguk degil — guven hissi, kurumsal buz degil
- Teknik ama korkutucu degil — developer icerigi ile consumer icerigi ayni cati altinda dogal
- Hiz odakli ama guven hissi veren — kullanici her an "sistem calisiyor" hissetmeli
- Creator economy ile uyumlu ama "generic AI startup" gibi gorunmeyen — urun gorsel dili kendi kisiligine sahip

### UI karakteri

- Temiz, editorial, kontrollu — her eleman mekanini hak etmis olmali
- Kart, tablo ve timeline yapilarini dengeli kullanan — ama hepsi ayni boyutta grid'e dizilmis degil, ritim ve varyasyon onemli
- Net hiyerarsiye sahip — kullanici 2 saniye icinde sayfadaki en onemli aksiyonu bulmali
- Bol bosluk kullanan — whitespace premium sinyalidir, bos alan degil
- Fazla renkli olmayan ama karakterli — tek accent renk cerrahi hassasiyetle, tipografi marka sesi

### Kacinilacak gorunus (anti-pattern listesi)

- Asiri mor/pembe AI template estetikleri (HuggingFace-klon gorunum)
- Kripto dashboard hissi (karanlik tema + neon cizgiler)
- Asiri kalabalik analytics paneli (Mixpanel/Amplitude etkisi)
- Ucuz growth-hack landing page dili (FOMO sayaclari, sahte testimonial)
- Flat, beyaz, hicbir karakter olmayan "clean" (steril ≠ premium)
- Her yere gradient serpilmis "modern" look (gradient = tembel dekorasyon)
- 3D illustration / isometric graphic / abstract blob kullanimi

## 8. Bilgi Mimarisi

### Public marketing alani

- Home / Landing
- Features
- Use Cases
- Pricing
- API
- Integrations
- Docs
- FAQ
- Login
- Sign Up

### Authenticated app alani

- Dashboard
- New Transcription
- Jobs / History
- Transcript Detail
- Billing
- Settings
- API Keys
- Developer Docs
- Integrations

## 9. Ana Kullanici Akislari

### Akis 1: Ilk ziyaretci -> landing -> sign up -> ilk transcript

1. Kullanici landing page'e gelir.
2. Hero alaninda urunun ne yaptigini 5 saniye icinde anlar.
3. Demo gorsel veya urun preview'u gorur.
4. "Start free" CTA'sina tiklar.
5. Hızli sign up yapar.
6. Kisa onboarding ekraninda nasil kullanmak istedigini secer:
   - Single link
   - Profile batch
   - Upload files
   - Viral research
7. Dashboard'a iner.
8. Ilk transcription job'unu olusturur.
9. Job progress ekranini gorur.
10. Transcript detail ekranina ulasir.
11. Copy/export aksiyonlarindan birini kullanir.
12. Free limit dolmaya yakinsa upgrade prompt'u gorur.

### Akis 2: Tek URL ile transcript alma

1. Kullanici "New Transcription" ekranina girer.
2. Kaynak tipi olarak "Single URL" secer.
3. Input alanina Instagram, TikTok veya YouTube URL'si yapistirir.
4. Opsiyonel olarak dil secer.
5. Opsiyonel olarak advanced ayarda model secer.
6. "Transcribe now" CTA'sina basar.
7. Sistem asamalari stepper ile gosterir:
   - Validating link
   - Fetching video
   - Extracting audio
   - Transcribing
   - Preparing export
8. Islem tamamlaninca transcript detail ekranina yonlenir.

### Akis 3: Profil bazli toplu transcript

1. Kullanici kaynak tipi olarak "Profile" secer.
2. Platform secimi yapar:
   - Instagram
   - TikTok
   - YouTube channel / playlist
3. Username girer.
4. Sistem profili tarar ve bulunacak video sayisi tahmini gosterir.
5. Kullanici isi baslatir.
6. Progress ekraninda toplam sayi, tamamlanan sayi ve kalan sure tahmini gorur.
7. Tamamlaninca sonuc listesi acilir.
8. Kullanici istedigi videonun transcript detail sayfasina girer veya bulk export indirir.

### Akis 4: Dosya yukleyerek transcript alma

1. Kullanici "Upload Files" secenegine girer.
2. Dosyalari surukle-birak ile yukler.
3. Dosya isimleri, boyutlar ve durumlari gorunur.
4. Dil secimi yapar.
5. Isi baslatir.
6. Her dosya icin satir bazli status gorur.
7. Tum sonuc bitince tek tek veya toplu export alir.

### Akis 5: Free user -> paywall -> checkout -> premium

1. Kullanici free limitine yaklasir veya limit asar.
2. Upgrade modal veya billing page acilir.
3. Plan karsilastirma kartlari gorur.
4. Ihtiyacina gore plan secer.
5. Stripe checkout'a gider.
6. Basarili odeme sonrasi billing success ekranina doner.
7. Dashboard'da yeni plan ve kullanim limiti gorunur.

### Akis 6: Mevcut kullanici -> billing management

1. Kullanici Settings veya Billing sayfasina gider.
2. Aktif plan, yenilenme tarihi, mevcut kullanim ve fatura gecmisi gorur.
3. "Manage subscription" ile Stripe customer portal'a gider.
4. Plan degistirir, kart gunceller veya iptal eder.

### Akis 7: Developer -> API key -> Codex / Claude tool kullanimi

1. Kullanici sign up olur veya mevcut hesaba girer.
2. Dashboard veya Settings altindan API Keys ekranina gider.
3. Yeni API key olusturur.
4. Integrations / Docs ekraninda su seceneklerden birini gorur:
   - cURL
   - JavaScript
   - Python
   - MCP / tool setup
5. API key'i kendi agent ortamina ekler.
6. Agent StoryToText tool'unu cagirarak URL gonderir.
7. Sistem transcription job'u olusturur.
8. Sonuc JSON veya plain text olarak agent'a geri doner.

### Akis 8: YouTube URL ile transcript alma

1. Kullanici "New Transcription" ekranina girer.
2. Single URL modunu secer.
3. YouTube video linkini yapistirir.
4. Dil secimini yapar veya auto'da birakir.
5. Isi baslatir.
6. Sistem video metadata, progress ve transcript sonucunu gosterir.
7. Kullanici transcript'i kopyalar, indirir veya tekrar calistirir.

### Akis 9: Viral research -> transcript -> AI rewrite

1. Kullanici viral oldugunu dusundugu bir Reel, TikTok veya YouTube videosunu sisteme ekler.
2. StoryToText transcript'i uretir.
3. Kullanici transcript'i tek tikla kopyalar veya JSON olarak indirir.
4. Bu ciktiyi Claude, Codex veya baska bir LLM aracina verir.
5. Yeni hook, script angle, caption veya icerik varyasyonlari uretir.

## 10. Ekran Listesi

### 10.1 Landing Page

Amac:

- Urunu aninda anlatmak
- Guven vermek
- CTA'ya yonlendirmek

Zorunlu bolumler:

- Announcement bar
- Header / nav
- Hero
- Product preview section
- Social proof / credibility band
- How it works
- Use cases
- Feature grid
- Pricing teaser
- FAQ
- API preview / developer callout
- Final CTA
- Footer

Hero icerigi:

- Net headline
- Kisa subheadline
- Primary CTA: Start free
- Secondary CTA: Watch demo veya View sample output
- Sag tarafta urun mockup'i

Hero'da desteklenen kaynaklar net gorunmeli:

- Instagram
- TikTok
- YouTube
- Uploads

Ornek headline yonu:

- "Turn viral videos into prompt-ready text."
- "Paste a Reel, TikTok, or YouTube link. Extract the script in minutes."
- "Find the structure behind viral content."

### 10.2 Sign Up / Login

Amac:

- En az friction ile hesaba giris

Beklentiler:

- Minimal form
- Google login opsiyonu dusunulebilir
- Email + password fallback
- Guven unsurlari: free trial bilgisi, no credit card ifadesi
- Developer odakli kullanicilar icin "Need API access?" alt notu eklenebilir

### 10.3 Onboarding

Amac:

- Kullanici niyetini anlamak
- Ilk degeri en hizli sekilde gostermek

Adimlar:

1. Kullanim amaci secimi
   - AI-assisted creator
   - Solo creator
   - Content studio
   - Developer / agent builder
2. Ilk kaynak tipi secimi
   - Single URL
   - Profile Batch
   - Upload Files
   - API / Agent Use
3. Opsiyonel tercih
   - Varsayilan dil
   - Email bildirimleri

Onboarding kisa olmali. Maksimum 2-3 ekran.

### 10.4 Dashboard

Amac:

- Yeni is baslatmak
- Son job'lari gormek
- Kullanim durumunu anlamak

Bolumler:

- Top nav
- Sol tarafta veya ustte ana CTA: New Transcription
- Usage card
- Recent jobs list
- Empty state veya first-run state
- Upgrade banner sadece gerekiyorsa
- API kullanan hesaplar icin usage split karti dusunulebilir: Web jobs / API jobs

Dashboard hissi:

- Analytics agirlikli degil
- Action-first
- Kullaniciyi hemen yeni job'a iter
- Bir creator operations console gibi hissettirmeli

### 10.5 New Transcription

Bu ekran urunun kalbidir.

Modlar:

- Single URL
- Profile Batch
- Upload Files
- API first users icin "View API docs" yan aksiyonu

Beklenen UI pattern:

- Segment control veya tab
- Solda form
- Sagda aciklayici preview / helper panel
- Advanced options collapsible alanda

Form alanlari:

- Source type
- Platform secimi gerekiyorsa
- URL veya username veya file dropzone
- Language
- Advanced: model secimi
- CTA: Transcribe now

Helper panel mesajlari:

- Analyze a viral video
- Build a transcript library for your niche
- Feed the result into your AI workflow

Platform secenekleri:

- Instagram
- TikTok
- YouTube

### 10.6 Job Processing

Amac:

- Kullaniciya bekleme sirasinda guven vermek
- Sistemin dondugu hissini engellemek

Gosterilecekler:

- Job title
- Source info
- Stepper / progress bar
- Estimated time
- Background'da devam ediyor bilgisi
- Opsiyonel: sayfadan ayrilsan da job history'de gorulecegi mesaji

### 10.7 Jobs / History

Amac:

- Eski isleri yeniden bulmak
- Durum takibi yapmak

Liste alanlari:

- Job name
- Source type
- Platform
- Created at
- Status
- Duration / item count
- Origin: Web / API
- Actions: View, Download

Filtreler:

- All
- Completed
- Processing
- Failed

### 10.8 Transcript Detail

Bu ekran premium hissin en kritik noktasi.

Bolumler:

- Header: video title / source / created at
- Action bar:
  - Copy transcript
  - Download TXT
  - Download JSON
  - Re-run
- Main content:
  - Transcript text
  - Opsiyonel segment blocks
- Side panel:
  - Source metadata
  - Language
  - Model used
  - Processing time

UI hedefi:

- Belge okuma hissi vermeli
- Uzun metinde okunabilirlik yuksek olmali
- Export aksiyonlari hep gorunur olmali
- API ile uretilen job'larda response formatinin goruntulenmesi opsiyonel olabilir
- Kopyalama deneyimi AI araclarina hizli handoff mantigina uygun olmali

### 10.9 Pricing

Amac:

- Urunun monetization mantigini cok net gostermek
- Plansiz, kararsiz, karmaşık gorunmemek
- Web kullanim ile API kullaniminin nasil paketlendigini net gostermek

Plan onerisi:

- Free
  - 3 transcription job
  - Dusuk aylik limit
  - Single URL + Upload
  - YouTube single URL dahil
- Starter
  - Solo creator
  - Aylik dakika veya kredi paketi
- Pro
  - Agency / power user
  - Daha yuksek limit
  - Profile batch acik
  - API access acik
- Business
  - Yuksek hacim
  - Priority processing
  - Daha yuksek API throughput

Kartlarda gosterilecek:

- Aylik fiyat
- Kim icin uygun
- Dahil olan haklar
- En onemli limit
- CTA

### 10.10 Billing

Bolumler:

- Current plan
- Usage this month
- Renewal date
- Payment method summary
- Billing history
- Manage subscription CTA
- Web usage vs API usage ayirimi

### 10.11 Settings

Bolumler:

- Profile
- Default transcription language
- Notification preferences
- Security
- Danger zone: delete account

### 10.12 API Keys

Amac:

- Gelistiricinin dakikalar icinde entegrasyona baslamasi

Bolumler:

- API key listesi
- Create new key
- Last used
- Scopes veya basit access labels
- Revoke action
- Copy-once security pattern

### 10.13 Developer Docs / Integrations

Amac:

- StoryToText'i tool olarak kullanmayi olabildigince kolay gostermek

Bolumler:

- Quickstart
- Auth with API key
- Endpoints overview
- Example request / response
- Codex setup
- Claude setup
- MCP or tool configuration sample
- Rate limits / usage notes

## 11. Landing Page Detay Kurgusu

### Header

Linkler:

- Features
- Use Cases
- Pricing
- Login
- Start free

### Hero

Sol kolon:

- Headline
- Subheadline
- CTA'lar
- Kisa trust note

Sag kolon:

- App screenshot veya simulated transcript workflow
- Belki 3 asamali mini flow:
  - Paste URL
  - Processing
  - Transcript Ready

### Social Proof

Gercek customer logosu yoksa su tarz seyler kullan:

- "Built for AI-assisted creators, content operators, and AI-native workflows"
- "Fast export-ready transcripts"
- "Instagram, TikTok, YouTube, and uploaded media in one research workflow"
- "Turn transcripts into prompts, hooks, and new scripts"

Sahte testimonial kullanma. Tasarim guveni sahte veriyle degil net urun diliyle kursun.

### How It Works

3 adim:

1. Add a link or upload files
2. StoryToText fetches and transcribes
3. Copy, export, and feed your AI content workflow

Ikinci bir mini developer strip dusunulebilir:

1. Generate API key
2. Call transcription endpoint
3. Use transcript inside your agent

### Feature Grid

Kart basliklari:

- Single-link transcription
- Batch profile import
- YouTube support
- File upload workflow
- TXT + JSON export
- API + agent integration
- Language controls
- Fast processing pipeline

Landing use case kartlari:

- Viral hook mining
- Competitor script research
- Repurpose your own content
- AI prompt input pipeline

### Pricing Teaser

Landing'de tam tablo yerine kisa ozet verilebilir:

- Free
- Starter
- Pro

Tam detay pricing sayfasinda.

### FAQ

Sorular:

- Which platforms are supported?
- Do I need to log into Instagram or TikTok?
- Can I transcribe YouTube videos?
- Can I upload my own files?
- What export formats do I get?
- Is there a free plan?
- Can I use this from Codex, Claude, or my own scripts?

## 12. Uygulama Ici Davranis Kurallari

### Status mantigi

Her job icin net durum:

- Queued
- Fetching
- Downloading
- Transcribing
- Completed
- Failed

### Empty states

Gerekli empty state alanlari:

- Dashboard no jobs
- Jobs list empty
- No transcript yet
- No billing history

Her empty state bir eylem onerisi icermeli.

### Error states

Ornek hata senaryolari:

- Gecersiz URL
- Private / unavailable profile
- Download failed
- YouTube video unavailable
- Platform temporarily unavailable
- File unsupported
- Plan limit exceeded
- API key invalid
- API quota exceeded

Error copy net olmali:

- Ne oldu
- Kullanici ne yapabilir
- Gerekirse alternatif akış ne

### Upgrade prompts

Agresif olmamali. Yerleri:

- Usage card
- Limit asildiginda modal
- Profile batch premium ise source selection ekraninda kilitli kart

## 13. Icerik ve Copy Rehberi

### Ses tonu

- Kisa
- Net
- Guven veren
- Teknik jargonu minimum kullanan

### CTA dili

Tercih edilen:

- Start free
- Analyze a viral video
- Transcribe now
- Upload files
- View transcript
- Upgrade plan
- Generate API key

Kacinilacak:

- Magic
- Revolutionize
- Supercharge
- AI-powered everything

## 14. Gorsel Yon ve Stil Rehberi

### Marka hissi

Uc kelime: **Editorial. Warm. Credible.**

StoryToText, Stripe'in developer guvenilirligini, Linear'in bilgi yogunlugu zarafetini ve Monocle dergisinin editorial tonunu tek urunde birlestirmeli. Bu urun bir "AI tool" gibi degil, bir "professional content operations platform" gibi gorunmeli.

### Estetik direkleri

1. **Editorial clarity** — Layout bir premium dergi gibi nefes almali. Bol whitespace, guclu tipografik hiyerarsi, gerektiginde asimetrik kompozisyon.
2. **Warm professionalism** — Soguk SaaS mavi/grisi degil. Sicak, ulasilan, insan hissi. Krem kagit duygusu, beyaz ekran degil.
3. **Restrained confidence** — Tek accent renk cerrahi hassasiyetle kullanilmali. Her yere gradient serpmek degil; renk kazanilmali.
4. **Technical credibility** — Kod bloklari, API dokumanlarini ve developer akislari urun icinde dogal gorunmeli, sonradan eklenenlenmis gibi degil.
5. **Creator-native** — Urun creator economy icinde yasayacak ama TikTok klonu gibi gorunmeyecek. Icerigin arkasindaki arac, icerigin kendisi degil.

### Referans estetikler (mood, kopyalama degil)

- **Stripe product pages** — developer guvenilirligi + editorial cilasi
- **Linear app UI** — bilgi yogunlugunu zarafetle yonetme
- **Notion marketing site** — sicaklik + netlik
- **Cal.com design language** — acik, modern, fonksiyonel
- **Readwise Reader** — belge okuma deneyimi (Transcript Detail icin kilit referans)
- **Raycast** — command-bar hissi, developer-native yuzey kalitesi

### Renk sistemi

Kesin hex yerine yon veren araliklar. Tasarimci bu aralik icinde yorumlamali:

| Token | Yon | Referans aralik |
|-------|-----|----------------|
| **Background** | Sicak off-white, soft stone. SAF BEYAZ DEGIL. Gri degil. | #F5F3EE → #FAF9F6 |
| **Surface** | Kartlar ve paneller icin background'dan biraz daha sicak beyaz | #FFFFFF → #FEFDFB |
| **Text primary** | Derin charcoal, saf siyah degil | #1C1917 → #292524 |
| **Text secondary** | Sicak gri | #78716C → #A8A29E |
| **Text muted** | Placeholder, helper text | #D6D3D1 araliği |
| **Accent** | TEK guclu, karakterli renk. Secenekler: deep terracotta, refined teal, warm indigo, veya burnt sienna. Bu renk SADECE CTA, active state ve key highlight'larda gorunur. | Tasarimci secer |
| **Success** | Muted sage green | #6A9B7A araliği |
| **Warning** | Sicak amber | #D4A853 araliği |
| **Error** | Kontrollü, muted red. Alarm kirmizisi degil | #C45C4A araliği |
| **Code/API surfaces** | Developer icerigi ayirmak icin biraz daha serin background | #F8F8FA araliği |

Kesinlikle KULLANILMAYACAK:
- Neon renkler
- Mor/violet gradient (AI startup klisesi)
- Elektrik mavisi
- Saf beyaz (#FFFFFF) ana background olarak
- Saf siyah (#000000) metin olarak

### Tipografi

Marka kisiliginin %80'i font seciminde yasayacak. Generic font = generic urun.

| Katman | Yon | Onerilecek adaylar (bunlardan biri veya benzeri) |
|--------|-----|------------------------------------------------|
| **Display/Heading** | Karakterli, akilda kalici. Ister editorial serif ister keskin geometric sans olsun — bu font markanin sesi | Fraunces, Instrument Serif, Clash Display, Satoshi, Neue Montreal |
| **Body** | Yuksek okunabilirlik, hafif sicaklik. Profesyonel ama steril degil | Outfit, Plus Jakarta Sans, DM Sans, Geist |
| **Monospace** | Kod bloklari, API response'lari, terminal ciktilari icin | JetBrains Mono, Fira Code, Berkeley Mono |

Kesinlikle KULLANILMAYACAK fontlar: Inter, Roboto, Arial, system-ui, sans-serif, Space Grotesk, Poppins.

Tip olcegi:
- Hero headline: Dramatik buyuk (48-72px desktop)
- Section heading: 28-36px
- Card heading: 20-24px
- Body text: 16-18px (generic 14px kullanma)
- Caption/helper: 13-14px
- Heading ile body arasi kontrast belirgin olmali

### Layout ve spatial sistem

- **Base grid**: 8px
- **Marketing max-width**: ~1200px
- **App max-width**: ~1100px
- **Section padding**: 24-48px (cömert olmali)
- **Card treatment**: Hafif sicak golge (warm shadow), duz border'dan kacin
- **App navigation**: Sol sidebar (collapse edilebilir, mobilde bottom tab bar)
- **Marketing navigation**: Top nav, transparent → solid on scroll

### Golge ve elevation

- **Level 0**: Duz yuzey, border yok veya cok hafif
- **Level 1**: Kartlar — `0 1px 3px rgba(28,25,23,0.06), 0 1px 2px rgba(28,25,23,0.04)`
- **Level 2**: Dropdown, popover — daha belirgin ama asla agir degil
- **Level 3**: Modal — backdrop blur + orta golge
- Sert box-shadow kullanma. Her zaman soft, layered shadow.

### Ikonografi

- Outline stil, 1.5-2px stroke
- Rounded cap
- Platform ikonlari (Instagram, TikTok, YouTube) gercek marka ikonlariyla gosterilmeli
- Custom ikon seti tutarliligi onemli — karistirma

### Motion

Motion felsefesi: **Yuksek etkili anlarda orkestre edilmis animasyon, dagınık micro-interaction'dan daha degerli.**

Oncelikli motion noktalari:
1. **Landing hero**: Product preview reveal — staggered fade-in + subtle slide-up (animation-delay ile)
2. **Job progress stepper**: Her adim gecisinde kontrollu, guven veren animasyon
3. **Page transitions**: App icinde sayfa gecislerinde hafif fade (200-300ms)
4. **Hover states**: Kartlarda subtle lift (translateY -2px + shadow artisi)
5. **Copy to clipboard**: Basarili kopyalama animasyonu (checkmark morph)

Kacinilacak:
- Bounce, wiggle, shake gibi oyuncaksi animasyonlar
- 500ms uzerinde surecek animasyonlar
- Scroll-jacking
- Paralaks overkill

## 15. Tasarimda Ozellikle Gosterilmesi Gereken Portfolyo Noktalari

- Landing ve app arasi ayni marka dilinin kurulmasi
- Job progress deneyiminin dusunulmus olmasi
- Empty, loading, failed, success durumlarinin tasarlanmis olmasi
- Billing ve pricing deneyiminin gercek bir SaaS gibi gorunmesi
- Developer docs ve API key deneyiminin ayni urun diliyle cozulmesi
- Sadece "guzel arayuz" degil, urun dusuncesi oldugunun hissedilmesi
- Viral content research ve AI-rewrite workflow'unun dogal sekilde urune yedirilmis olmasi

## 16. Onerilen Launch Fiyatlandirma Mantigi

Bu tasarim icin varsayim:

- Free:
  - Ayda 3 job
  - Single URL ve upload
  - YouTube single URL dahil
  - Limited export
  - API yok
- Starter: $19/month
  - Daha yuksek dakika limiti
  - Tum exportlar
  - Web app oncelikli kullanim
- Pro: $49/month
  - Instagram, TikTok ve YouTube batch/profile import
  - Daha yuksek kullanim
  - API access
  - Codex / Claude integration docs
- Business: custom veya $149/month
  - Yuksek hacim
  - Priority support
  - Yuksek API throughput
  - Opsiyonel team / service account yapisi

Tasarimda kredi veya dakika mantigi net ve basit gorunmeli. Karmaşik pricing tasarlama.

## 17. Teknik Gerceklerle Uyumlu Tasarim Notlari

Mevcut backend mantigina gore tasarim:

- Giris kaynaklari:
  - Instagram Reel URL
  - TikTok URL
  - YouTube video URL
  - Instagram username
  - TikTok username
  - YouTube channel veya playlist
  - Local media upload
- Ayarlar:
  - Language
  - Model choice
- Cikti:
  - Transcript
  - JSON export
  - TXT export

Developer product tarafinda tasarim varsayimi:

- API auth: Bearer API key
- Minimal endpoint set:
  - `POST /v1/transcriptions`
  - `GET /v1/jobs/{id}`
  - `GET /v1/jobs/{id}/result`
  - `GET /v1/usage`
- Tool/MCP wrapper su ana aksiyonlari expose eder:
  - `transcribe_url`
  - `transcribe_upload`
  - `get_job_status`
  - `get_transcript_result`

Bu nedenle launch tasariminda su ozellikleri ana vaat olarak one cikarma:

- Summary
- Translation
- Multi-user collaboration
- Workspace permissions
- Subtitle style editor

Bunlar urunun bu versiyonunda ana vaat olarak one cikarilmamali.

## 18. Success Metrics

- Landing -> sign up conversion
- Sign up -> first completed transcript rate
- Free -> paid conversion
- Transcript detail page usage
- Export action rate
- Repeat weekly usage
- API key creation rate
- API aktif kullanici orani
- Agent/tool uzerinden gelen transcription job sayisi

## 19. Stitch Icin Yapilandirilmis Tasarim Promptu

Asagidaki metin CO-STAR + TIDD-EC prompt mimarisi ile yapilandirilmistir. Stitch'e bolum bolum veya tek parca olarak verilebilir. Her bolum basliginin Stitch icin ne anlama geldigi aciklanmistir.

---

### CONTEXT (Urun ve is baglami)

> StoryToText is a web-based micro SaaS product that converts social media videos into clean, prompt-ready transcripts. Users paste an Instagram Reel, TikTok video, or YouTube link — or upload their own media files — and receive accurate transcripts they can copy, download (TXT/JSON), and feed directly into AI content workflows.
>
> The product is NOT a single-purpose tool. It is a real subscription SaaS with:
> - User accounts with onboarding
> - A dashboard with job history and usage tracking
> - Tiered pricing (Free / Starter $19/mo / Pro $49/mo / Business $149/mo)
> - Stripe-powered billing and subscription management
> - API key management for developers
> - REST API endpoints for programmatic access
> - Integration guides for AI agents (Codex, Claude, custom MCP tools)
>
> The product has three input modes:
> 1. **Single URL** — paste one Instagram, TikTok, or YouTube link
> 2. **Profile Batch** — enter a username to scan and transcribe all public videos from a profile/channel
> 3. **File Upload** — drag-and-drop video/audio files for transcription
>
> Technical capabilities: language selection, model selection, real-time job progress tracking (queued → fetching → downloading → transcribing → completed/failed), and both web and API usage metering.

### OBJECTIVE (Tasarim hedefi)

> Design a complete, responsive (desktop + mobile) product — including a marketing website AND an authenticated application — that looks and feels like a real, funded, launched SaaS product. Every screen must belong to the same cohesive design system.
>
> The design must demonstrate:
> - Sophisticated product thinking (not just pretty UI, but thoughtful IA and realistic flows)
> - A premium brand identity that is instantly distinguishable from generic AI startup templates
> - Production-grade polish across ALL states: empty, loading, success, error, paywall, first-run
> - Equal care given to consumer screens (landing, dashboard, transcript) AND developer screens (API keys, docs, integrations)

### STYLE (Gorsel kimlik ve estetik yon)

> **Visual identity in three words: Editorial. Warm. Credible.**
>
> Think "Stripe meets Linear meets Monocle magazine." This product lives in the creator economy but dresses like premium software.
>
> **Aesthetic pillars:**
>
> 1. **Editorial clarity** — Layouts breathe like a premium magazine. Generous whitespace, strong typographic hierarchy, asymmetric compositions where they serve the content. The Transcript Detail page should feel like reading a beautifully typeset document.
>
> 2. **Warm professionalism** — NOT cold SaaS blue/gray. The product feels warm, approachable, human. Backgrounds should evoke cream paper, not clinical white screens. Color palette: warm off-white to soft stone backgrounds (#F5F3EE → #FAF9F6 range), deep charcoal text (#1C1917 → #292524 range), warm gray secondary text (#78716C range).
>
> 3. **Restrained confidence** — ONE bold accent color used with surgical precision. Choose from: deep terracotta, refined teal, warm indigo, or burnt sienna. This accent appears ONLY on primary CTAs, active navigation states, and key highlights. Nowhere else. Color is earned, not splashed.
>
> 4. **Technical credibility** — Code blocks, API documentation, endpoint references, and developer setup flows should feel native to the product. They should look as polished as Stripe's developer docs — dark code surfaces with syntax highlighting, clean endpoint tables, copy buttons on every code sample.
>
> 5. **Creator-native context** — Platform icons (Instagram, TikTok, YouTube) serve as visual anchors throughout. The product understands its users' world without becoming another social media clone.
>
> **Typography (critical — this defines the brand):**
> - Display/Headings: A distinctive, characterful typeface — editorial serif (Fraunces, Instrument Serif) OR sharp geometric sans (Clash Display, Satoshi, Neue Montreal). This font IS the brand voice.
> - Body: Warm, highly readable sans-serif (Outfit, Plus Jakarta Sans, DM Sans, or Geist).
> - Monospace: JetBrains Mono or Fira Code for all code/API surfaces.
> - NEVER use: Inter, Roboto, Arial, system fonts, Space Grotesk, or Poppins.
> - Hero headlines should be dramatically large (48-72px). Body text generous (16-18px). Strong contrast between levels.
>
> **Spatial system:**
> - 8px base grid. Generous padding (24-48px on sections).
> - Cards use subtle warm shadows, never flat borders alone.
> - Marketing pages: max-width ~1200px, full-width section backgrounds.
> - App: max-width ~1100px, collapsible sidebar navigation.
>
> **Reference aesthetics (for mood direction, not copying):**
> - Stripe → developer credibility + editorial polish
> - Linear → elegant information density
> - Notion marketing → warmth + clarity
> - Cal.com → open, modern, functional
> - Readwise Reader → document-reading experience for transcripts
> - Raycast → developer-native surface quality

### TONE (Duygusal tepki)

> When someone sees this product for the first time, they should feel:
> - "This is a real product built by someone who understands SaaS."
> - "I trust this enough to enter my credit card."
> - "This tool was designed for professionals like me."
> - "I want to show this to my team / put this in my portfolio."
>
> The tone is confident but not arrogant. Professional but not corporate. Technical but not intimidating. The copy voice is short, direct, and trust-building. No hype words (magic, revolutionize, supercharge, AI-powered everything).

### AUDIENCE (Hedef kullanicilar)

> Primary users (design FOR them):
> 1. **AI-First Creator** — Uses transcripts to feed Claude/Codex for new script generation. Needs speed, clean output, copy-to-clipboard simplicity.
> 2. **Solo Creator / Personal Brand** — Transcribes own videos for repurposing into captions, carousels, newsletters. Values beautiful, trustworthy UI.
> 3. **Content Studio / Agency** — Batch-processes competitor profiles, exports in bulk. Needs table views, filters, batch download.
> 4. **Developer / AI Builder** — Uses API keys and REST endpoints inside agent workflows. Needs clean docs, code samples, and MCP/tool setup guides.
>
> All users share one trait: they value speed-to-output. The product should get them from "I have a video URL" to "I have usable text" in under 3 minutes.

### TASK (Tasarlanacak ekranlar — oncelik sirasinda)

> **Priority 1 — Core experience (design these first, highest fidelity):**
>
> 1. **Landing Page** — Full-length marketing page with ALL sections:
>    - Announcement/promo bar (top)
>    - Header navigation: Features, Use Cases, Pricing, Login, [Start free] CTA button
>    - Hero: left column (headline + subheadline + 2 CTAs + trust note), right column (product preview mockup showing a simulated 3-step flow: Paste URL → Processing → Transcript Ready)
>    - Supported platforms strip (Instagram, TikTok, YouTube, Upload icons)
>    - Social proof band — NO fake testimonials. Use credibility statements: "Built for AI-assisted creators and content operators", "Prompt-ready transcripts in minutes", "Instagram, TikTok, YouTube, and uploads in one workflow"
>    - How it works: 3 steps (Add link → StoryToText transcribes → Copy/export for AI workflow). Optional secondary developer strip (Generate API key → Call endpoint → Use in agent)
>    - Feature grid: 8 cards — Single-link transcription, Batch profile import, YouTube support, File upload, TXT+JSON export, API+agent integration, Language controls, Fast pipeline
>    - Use case cards: Viral hook mining, Competitor script research, Repurpose your own content, AI prompt input pipeline
>    - Pricing teaser (3 plans summary, "See full pricing" link)
>    - FAQ section (7 questions: platforms supported, login requirements, YouTube support, file upload, export formats, free plan, API/agent usage)
>    - Final CTA block
>    - Footer with sitemap links
>
> 2. **Dashboard** — Action-first, NOT analytics-first:
>    - Prominent "New Transcription" CTA (primary action, visually dominant)
>    - Usage card (credits/minutes used this month, visual progress bar)
>    - Recent jobs list (5-7 items, each showing: job name, source platform icon, status badge, timestamp, quick actions)
>    - Empty state for first-time users (illustration + "Create your first transcript" CTA)
>    - Subtle upgrade banner only if approaching limit
>    - Optional: Web vs API usage split for developer accounts
>
> 3. **New Transcription** — The product's centerpiece screen:
>    - Tab/segment control switching between 3 modes: Single URL | Profile Batch | Upload Files
>    - Left side: form area. Right side: contextual helper panel with rotating tips ("Analyze a viral video", "Build a transcript library", "Feed results into your AI workflow")
>    - Single URL mode: large URL input with auto-detected platform icon, language selector, collapsible advanced options (model selection), "Transcribe now" primary CTA
>    - Profile Batch mode: platform selector (Instagram/TikTok/YouTube), username input, estimated video count preview before starting
>    - Upload Files mode: drag-and-drop zone with file list (name, size, status), language selector
>    - "View API docs" secondary link for developer users
>
> 4. **Transcript Detail** — THE most polished screen. This is the money shot:
>    - Header: video title, source platform icon, creation timestamp
>    - Sticky action bar: [Copy transcript] [Download TXT] [Download JSON] [Re-run] — always visible
>    - Main content: transcript text in a beautiful, document-like reading layout. Generous line-height, optimal reading width (~65ch), clear paragraph separation. If segments exist, show them as subtle blocks.
>    - Side panel (desktop): source metadata, detected language, model used, processing duration, word count
>    - Mobile: side panel becomes a collapsible bottom sheet
>    - The reading experience should feel like Readwise Reader or a premium blog — not a code output or log dump
>
> 5. **Pricing Page** — 4-tier comparison:
>    - Free: 3 jobs/month, single URL + upload, YouTube single URL, limited export, no API
>    - Starter ($19/mo): higher minute limit, all exports, web priority
>    - Pro ($49/mo): batch/profile import, higher usage, API access, Codex/Claude integration docs — HIGHLIGHTED as recommended
>    - Business ($149/mo): high volume, priority processing, high API throughput, optional team/service account
>    - Each card: monthly price, "who it's for" tagline, included features list, primary limit callout, CTA button
>    - Annual pricing toggle optional
>
> **Priority 2 — Key flows:**
>
> 6. **Job Processing** — Trust-building waiting experience:
>    - Job title and source info
>    - Visual stepper showing current stage: Validating → Fetching → Downloading → Transcribing → Preparing export
>    - Estimated time remaining
>    - "You can leave this page — find your job in History" reassurance message
>    - Subtle animated indicator (not a spinning wheel — something more refined)
>
> 7. **Jobs / History** — Filterable job list:
>    - Table with columns: Job name, Source type, Platform icon, Created at, Status badge, Duration/item count, Origin (Web/API badge), Actions (View, Download)
>    - Filters: All, Completed, Processing, Failed
>    - Search/filter input
>    - Empty state with CTA
>
> 8. **Sign Up / Login** — Minimal friction:
>    - Clean centered form, minimal fields
>    - Google login option
>    - Email + password fallback
>    - Trust elements: "Free to start", "No credit card required"
>    - "Need API access?" subtle note for developers
>
> 9. **Onboarding** — 2-3 screens maximum:
>    - Step 1: Usage intent selection (AI-assisted creator / Solo creator / Content studio / Developer)
>    - Step 2: First source type preference (Single URL / Profile Batch / Upload / API)
>    - Step 3 (optional): Default language, email notification preferences
>    - Then immediately land on Dashboard with contextual first-run state
>
> 10. **Billing** — Real SaaS billing page:
>     - Current plan card with plan name and renewal date
>     - Usage this month (visual meter)
>     - Web usage vs API usage breakdown
>     - Payment method summary
>     - Billing history table
>     - "Manage subscription" → Stripe Customer Portal
>
> **Priority 3 — Developer & settings:**
>
> 11. **API Keys** — Developer-first management:
>     - API key list table (name, key preview, last used, created date)
>     - "Create new key" button → modal with name input → show full key ONCE with copy button (copy-once security pattern)
>     - Revoke action with confirmation
>     - Clean, minimal, Stripe-like
>
> 12. **Developer Docs / Integrations** — In-product documentation:
>     - Quickstart guide
>     - Authentication section (Bearer API key)
>     - Endpoints: POST /v1/transcriptions, GET /v1/jobs/{id}, GET /v1/jobs/{id}/result, GET /v1/usage
>     - Code samples in tabs: cURL, JavaScript, Python
>     - Codex setup guide
>     - Claude setup guide
>     - MCP / tool configuration sample
>     - Rate limits and usage notes
>     - Each code block: dark surface, syntax highlighting, copy button
>
> 13. **Settings** — Simple preferences:
>     - Profile info
>     - Default transcription language
>     - Notification preferences
>     - Security section
>     - Danger zone: delete account

### DO (Yapilmasi gerekenler)

> - DO make the Transcript Detail page the single most beautiful screen in the entire product — this is the core value delivery moment
> - DO use realistic placeholder content everywhere: actual transcript text (not lorem ipsum), believable video titles ("How I went from 0 to 100K followers in 90 days"), real-looking usernames (@contentcreator)
> - DO design ALL states for every screen: empty, loading/skeleton, success, error, and paywall/upgrade-needed
> - DO make the landing page hero feel alive with a product preview that shows actual UI (not abstract illustration)
> - DO use platform icons (Instagram, TikTok, YouTube) as consistent visual anchors — they help users instantly orient
> - DO make export actions (Copy, Download TXT, Download JSON) ALWAYS visible without scrolling on the Transcript Detail page
> - DO design mobile-responsive versions of at least: Landing Page, Dashboard, New Transcription, Transcript Detail, Pricing
> - DO treat developer screens (API Keys, Docs) with the SAME design quality as consumer screens
> - DO create a consistent component language: every button, card, input, badge, and modal should feel like they belong to one system
> - DO show the pricing page with EXACTLY 4 tiers: Free, Starter ($19/mo), Pro ($49/mo), Business ($149/mo) with Pro highlighted as recommended
> - DO make the stepper/progress visualization for job processing feel trustworthy and informative
> - DO design the sidebar navigation with clear icon + label pairs — maximum 7 items

### DON'T (Kacinilmasi gerekenler)

> - DON'T use purple/violet gradients anywhere — this is the #1 "AI startup template" cliche
> - DON'T use neon, electric, or overly saturated colors
> - DON'T default to dark mode — warm light theme is the primary and only required theme
> - DON'T use 3D illustrations, isometric graphics, AI-generated imagery, or abstract blob shapes
> - DON'T make it look like an analytics/dashboard product — this is action-first, not data-first
> - DON'T use identical-sized card grids for everything — vary the layout rhythm, use asymmetry where it serves hierarchy
> - DON'T overcrowd any screen — visual restraint IS the premium signal
> - DON'T use Inter, Roboto, Arial, system fonts, Space Grotesk, or Poppins
> - DON'T add features not specified: no AI summary, no video editing, no translation, no team collaboration, no chrome extension
> - DON'T use generic stock illustrations or hero images — product UI itself is the hero visual
> - DON'T create busy navigation — every nav item must earn its place
> - DON'T use fake testimonials, fake user counts, or fake social proof — credibility statements only
> - DON'T use hype copy: "magic", "revolutionize", "supercharge", "AI-powered", "10x your workflow"
> - DON'T design a pure-white (#FFFFFF) background for any main surface — always warm it

### EXAMPLES (Beklenen kalite referanslari)

> **Landing page quality target**: Stripe.com level — every section has purpose, typography carries the brand, the product speaks for itself through UI previews, not marketing fluff.
>
> **App UI quality target**: Linear.app level — clean sidebar, information-dense but never cluttered, beautiful table/list views, subtle animations on state changes.
>
> **Transcript reading quality target**: Readwise Reader level — typography-first, generous whitespace, the text is the hero, all actions accessible but not visually dominant.
>
> **Developer docs quality target**: Stripe API docs level — clean code blocks on dark surfaces, tabbed language selection, copy buttons, endpoint tables with type annotations.
>
> **Pricing page quality target**: Cal.com pricing level — clean comparison cards, one plan highlighted, clear hierarchy of "who this is for", no visual noise.

### COMPONENT SYSTEM (Tasarlanacak tutarli parcalar)

> Design these as a unified system where every piece clearly belongs:
>
> - **Buttons**: primary (accent color), secondary (outlined), ghost (text only), destructive (muted red). Consistent border-radius, padding, and sizing.
> - **Inputs**: URL input with auto-detected platform icon, standard text input, select dropdown, file dropzone (dashed border, drag state)
> - **Cards**: job card (in dashboard/history), pricing card (4 tiers), usage card (progress bar), feature card (landing page)
> - **Tables**: job history rows with platform icon + status badge + timestamp + actions
> - **Status badges**: queued (gray), fetching (blue), downloading (blue), transcribing (amber), completed (green), failed (red) — subtle, not loud
> - **Navigation**: top nav for marketing (transparent → solid on scroll), sidebar for app (icon + label, collapsible)
> - **Modals**: upgrade prompt, new API key creation, delete confirmation, error detail
> - **Empty states**: each with a relevant illustration/icon, descriptive text, and a primary action CTA
> - **Toast/notifications**: success (copy confirmation), error (job failed), info (approaching limit)
> - **Progress stepper**: horizontal, 5-6 stages, active stage highlighted with accent color
> - **Tabs/segment control**: for transcription mode switching (Single URL | Profile Batch | Upload)
> - **Code blocks**: dark surface, syntax highlighting, language label, copy button
> - **Platform icons**: Instagram, TikTok, YouTube — used consistently as visual identifiers

### RESPONSIVE BEHAVIOR

> - **Landing page**: fluid grid, sections stack on mobile, hero becomes single column (text → product preview), pricing cards horizontally scroll or stack
> - **App sidebar**: collapses to bottom tab bar on mobile (max 5 items)
> - **Transcript Detail**: full-width reading on mobile, side panel metadata becomes a collapsible bottom sheet
> - **Tables**: horizontal scroll on mobile with sticky first column, or switch to card layout
> - **New Transcription form**: full-width on mobile, helper panel hides or moves below form

---

## 20. Tasarim Ciktisi Beklentisi

Stitch'ten beklenen teslimatlar oncelik sirasinda:

### Tier 1 — Zorunlu, en yuksek fidelity

| # | Ekran | Durum | Responsive |
|---|-------|-------|-----------|
| 1 | Landing Page (tam uzunluk, tum sectionlar) | Default | Desktop + Mobile |
| 2 | Dashboard | Default + Empty state | Desktop + Mobile |
| 3 | New Transcription (3 mod gorunur) | Default | Desktop + Mobile |
| 4 | Transcript Detail | Tamamlanmis job, metin dolu | Desktop + Mobile |
| 5 | Pricing Page (4 plan) | Default | Desktop + Mobile |

### Tier 2 — Onemli akis ekranlari

| # | Ekran | Durum | Responsive |
|---|-------|-------|-----------|
| 6 | Job Processing | Active stepper | Desktop |
| 7 | Jobs / History | Dolu liste + filtreler | Desktop |
| 8 | Sign Up / Login | Default | Desktop + Mobile |
| 9 | Onboarding (2-3 adim) | Her adim | Desktop |
| 10 | Billing | Aktif plan + kullanim | Desktop |

### Tier 3 — Developer & settings

| # | Ekran | Durum | Responsive |
|---|-------|-------|-----------|
| 11 | API Keys | Key listesi + yeni key modali | Desktop |
| 12 | Developer Docs / Integrations | Quickstart + code samples | Desktop |
| 13 | Settings | Default | Desktop |

### Ek durum tasarimlari (her ekran icin gerekli)

Her ekranin su durumlari dusunulmeli:
- **Empty state**: ilk kullanim, hicbir veri yok — aksiyon onerisi ile
- **Loading/skeleton state**: veri yukleniyor — iskelet kartlar/satirlar ile
- **Success state**: islem basarili — onay mesaji veya toast ile
- **Error state**: hata olustu — ne oldugu, ne yapilabilecegi, alternatif akis
- **Paywall/upgrade state**: limit asildi — upgrade prompt, plan karsilastirma

### Component library (tutarli tasarim sistemi)

Tum ekranlar boyunca tutarli kullanilacak parcalar:
- Buttons (primary, secondary, ghost, destructive)
- Input fields (URL input w/ platform icon, text, select, file dropzone)
- Cards (job, pricing, usage, feature)
- Table rows (job history with status badge)
- Status badges (queued, fetching, downloading, transcribing, completed, failed)
- Navigation (marketing top nav, app sidebar, mobile bottom tab bar)
- Modals (upgrade, confirmation, error, new API key)
- Empty states (illustrated, with CTA)
- Toast notifications (success, error, info)
- Progress stepper (5-6 stage horizontal)
- Tabs / segment controls
- Code blocks (dark surface, syntax highlight, copy button)

## 21. Son Not

Bu urun, "video transcription tool" gibi gorunmemeli. Tasarim dili, bilgi mimarisi ve billing yapisi sayesinde gercek bir micro SaaS urunu gibi hissettirmeli. En onemli etki su olmali:

"Bu kisi sadece bir arayuz cizmemis; pazarlama, onboarding, urun akisi ve monetization'i birlikte dusunmus."
