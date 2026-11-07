# Hissa qo‘shish

Python 3.10+ va Linux kerak. Kodni o‘zgartirishdan oldin alohida branch yarating.

Tekshirish:

```bash
python3 -m unittest discover -s tests -v
bash -n start.sh install.sh unlockabz
```

Office ochish testlari uchun loyiha virtual muhiti va `requirements.txt` kerak. Testlarda shaxsiy hujjat, haqiqiy handshake yoki topilgan parollarni commit qilmang. Yangi funksiyaga mos test va README izohini qo‘shing.

Pull requestda nima o‘zgargani va qanday tekshirilganini yozing. Xato haqida xabar berishda OS, Python va Hashcat versiyalarini ko‘rsating; parollar, handshake va maxfiy hujjatlarni biriktirmang.

Toza manba arxivi:

```bash
python3 scripts/package.py
```

Faqat skriptdagi ruxsat etilgan loyiha fayllari `dist/UnlockAbz-github.zip` ichiga yoziladi.
