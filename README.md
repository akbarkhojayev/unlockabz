# UnlockAbz

**Terminal uchun parol tiklash tooli · Python 3.10+ · Ubuntu / Kali / Debian**

Office fayllari va Wi-Fi handshake parollarini raqamli ro‘yxatlar bilan tekshiradigan terminal tool.

## Ishga tushirish

GitHub’dan yuklab olingan loyiha papkasida terminal oching. Kerak bo‘lsa skriptlarga bajarish ruxsatini bering:

```bash
chmod +x start.sh install.sh unlockabz
```

Keyin:

```bash
./start.sh
```

Yetishmagan dasturlar avtomatik o‘rnatiladi. Birinchi safar internet va sudo paroli kerak bo‘lishi mumkin. Keyin menyu ochiladi.

**Ubuntu, Kali va Debian uchun.** Faqat o‘zingizning yoki tekshirishga ruxsat berilgan fayl va tarmoqlarda ishlating.

## Qanday ishlatiladi?

1. Menyudan **1** ni tanlang.
2. Fayl yo‘lini yozing yoki faylni terminalga sudrab tashlang.
3. Parollar ro‘yxatini tanlang.
4. Tekshiruv tugashini kuting. Natija va parol terminalda ko‘rinadi.

**Ctrl+C** — tekshiruvni to‘xtatish. **Enter** — menyuga qaytish. **0** — orqaga yoki chiqish.

## Parollar ro‘yxati

| Tanlov | Tekshiriladigan parollar |
| --- | --- |
| 1 | `1` dan `9999` gacha — tayyor TXT fayldan |
| 2 | `10000000` dan `99999999` gacha — tekshirish vaqtida yaratiladi |

Ikkinchi variant uchun arxiv yoki 810 MB TXT kerak emas. Boshi nol bilan boshlanadigan `0001`, `01234567` kabi parollar bu ro‘yxatlarda yo‘q.

**Wi-Fi handshake uchun 2-variantni tanlang:** WPA paroli kamida 8 belgi bo‘ladi.

## Qaysi fayllar ishlaydi?

- **DOCX, XLSX, PPTX** — qo‘llanadigan Office Agile shifrlash turlari.
- **HC22000** — WPA/WPA2 handshake yoki PMKID.
- **CAP, PCAP, PCAPNG** — ichida yaroqli handshake yoki PMKID bo‘lsa.

PDF, ZIP, RAR va eski Office shifrlashlari hozir qo‘llanmaydi. Haqiqiy Wi-Fi handshake bilan yakuniy sinov hali bajarilmagan.

## Natijalar qayerda?

Menyudagi **4-band** oldingi tekshiruvlar va ularning papkalarini ko‘rsatadi.

Har tekshiruv `jobs/` ichida alohida saqlanadi:

- `passwords.txt` — parol topilsa.
- `unlocked.*` — Office hujjati ochilsa.
- `result.json` — tekshiruv hisoboti.

Asl fayl o‘zgarmaydi. Parollar saqlangan papkalarni ommaga ulashmang.

## Tozalash va yordam

- **2-band:** kerakli dasturlar va CPU/GPU holati.
- **3-band:** vaqtinchalik fayllarni tozalash; parollar va ochilgan hujjatlar saqlanadi.
- `./start.sh --no-animation` — animatsiyasiz ochish.
- `./start.sh --help` — qo‘shimcha buyruqlar.

Tekshiruv CPU’da uzoq davom etishi mumkin. Ro‘yxatda topilmasa, parol boshqa bo‘lishi mumkin. To‘xtatilgan tekshiruv qayta boshlanganda boshidan ishlaydi.

O‘rnatishda xato bo‘lsa, internet va sudo ruxsatini tekshirib `./start.sh` ni qayta bajaring.

## Loyiha tuzilishi

```text
UnlockAbz/
├── start.sh              # Asosiy ishga tushirish
├── install.sh            # Yetishmagan komponentlarni o‘rnatish
├── unlockabz             # Muqobil ishga tushirish buyrug‘i
├── unlockabz.py          # Menyu va jarayonlarni boshqarish
├── engine.py             # Hashcat va Office bilan ishlash
├── terminal_ui.py        # Terminal dizayni
├── launcher.py           # Mahalliy desktop yorlig‘i
├── numbers-1-9999.txt     # Birinchi ro‘yxat
├── requirements.txt      # Python kutubxonasi
├── tests/                # Avtomatik tekshiruvlar
└── scripts/package.py    # GitHub uchun toza arxiv
```

Desktop yorlig‘ini yaratish: `python3 launcher.py`.

## Dasturchilar uchun

```bash
.venv/bin/python -m unittest discover -s tests -v
bash -n start.sh install.sh unlockabz
python3 scripts/package.py
```

Arxiv: `dist/UnlockAbz-github.zip`. Unga shaxsiy fayllar, natijalar, parollar, virtual muhit va katta arxivlar kiritilmaydi. `.gitignore` ham shu fayllarni Git’dan chiqaradi. Commit qilishdan oldin `git status`ni ko‘rib chiqing.

Hissa qo‘shish: [CONTRIBUTING.md](CONTRIBUTING.md).
