/* Ana uygulama — durum yönetimi, panel/form/günlük mantığı, kısayollar.
 * Görsel dil ve etkileşim akışı github.com/slanur/calendar-clock-spark
 * ("Lovable" ile tasarlanmış) projesinden uyarlanmıştır. İş kuralı burada
 * YOKTUR: her işlem `K.cagir(...)` ile Python'daki `Motor`/`Oturum`
 * fonksiyonunu çağırır; JS yalnızca sonucu çizer. */

(function () {

  const S = {
    seciliKullanici: null,
    seciliGun: null, // "YYYY-MM-DD"
    filtreAktif: false,
    mod: "tek", // "tek" | "paket"
    kalemler: [], // [{kaynak, bas:"HH:MM", bit:"HH:MM"}]
    kalemFiyatlari: [], // paralel dizi: {ucret?, kod?}
    seciliRezId: null,
    sonRedParametreler: null,
    oncekiDegerler: {}, // kid -> {bakiye, guvenilirlik}
    paramCache: null,
    gunlukSecimNo: null,
  };

  const Oynat = {
    aktif: false,
    mesgul: false,
    hizNo: 0,
    gorsel: null, // ms — ekranda akan saat
    sonrakiOlay: null, // ms — çekirdekteki bir sonraki olay anı
    sonKare: 0,
    zamanlayici: null,
    calismaBasDk: 8 * 60,
    calismaBitDk: 22 * 60,
  };

  const $ = (id) => document.getElementById(id);
  const HATA_ARAMA_GECIKME = 200;

  // ------------------------------------------------------------------
  // Açık / koyu tema
  // ------------------------------------------------------------------
  const Tema = {
    mevcut() { return document.documentElement.getAttribute("data-tema") || "acik"; },
    uygula(tema) {
      document.documentElement.setAttribute("data-tema", tema);
      try { localStorage.setItem("tema", tema); } catch (e) {}
      const ikon = tema === "koyu" ? "☀" : "☾";
      [$("tema-btn"), $("tema-btn-acilis")].forEach((b) => { if (b) b.textContent = ikon; });
    },
    degistir() { this.uygula(this.mevcut() === "koyu" ? "acik" : "koyu"); },
    kur() {
      this.uygula(this.mevcut());
      [$("tema-btn"), $("tema-btn-acilis")].forEach((b) => b && b.addEventListener("click", () => this.degistir()));
    },
  };
  Tema.kur();

  function saatSecenekleriDoldur() {
    const dl = $("saat-secenekleri");
    for (let h = 8; h <= 22; h++) {
      for (const m of [0, 15, 30, 45]) {
        if (h === 22 && m > 0) continue;
        const o = document.createElement("option");
        o.value = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
        dl.appendChild(o);
      }
    }
  }

  // ------------------------------------------------------------------
  // Açılış / dosya
  // ------------------------------------------------------------------
  function dosyaAcildi() {
    $("acilis-ekrani").classList.add("gizli");
    $("sayfa").style.display = "block";
  }

  async function dosyaAdiGuncelle(ad) {
    oynatSifirla();
    $("dosya-adi").textContent = ad || "Dosya seçilmedi";
    dosyaAcildi();
    S.paramCache = null;
    S.seciliRezId = null;
    const simdi = await K.cagir("simdi");
    S.seciliGun = simdi.split("T")[0];
    gunEtiketiGuncelle();
    await kullanicilariDoldur();
    varsayilanKalemler();
    await tumunuYenile();
  }

  K.onDosyaDegisti((ad) => dosyaAdiGuncelle(ad));
  $("acilis-dosya-btn").addEventListener("click", () => K.dosyaSec());
  $("dosya-degistir-btn").addEventListener("click", async () => { await oynatDurdur(); K.dosyaSec(); });

  K.hazir.then(async () => {
    const yol = await K.ilkDosya();
    if (yol) {
      const sonuc = await K.dosyaYukle(yol);
      if (sonuc && sonuc.dosya) dosyaAdiGuncelle(sonuc.dosya);
    }
  });

  // ------------------------------------------------------------------
  K.onDurumDegisti(() => tumunuYenile());

  async function tumunuYenile() {
    await Promise.all([ustBarYenile(), takvimYenile(), kullaniciPaneliYenile(), gunlukYenile(), rezDetayYenile()]);
    fiyatlariGuncelleGecikmeli();
  }

  // ------------------------------------------------------------------
  // Üst bar
  // ------------------------------------------------------------------
  async function ustBarYenile() {
    if (!(await K.yukluMu())) return;
    saatGoster(await gorunenSimdi());
    $("geri-al-btn").disabled = !(await K.geriAlYapilabilir());
  }

  function saatGoster(iso) {
    const [tarih, saat] = iso.split("T");
    const d = new Date(tarih + "T00:00:00");
    const gunAdi = ["Paz", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt"][d.getDay()];
    $("saat-deger").textContent = `${gunAdi} ${tarih.slice(8, 10)}.${tarih.slice(5, 7)} · ${saat}`;
    $("saat-deger").title = `${tarih.split("-").reverse().join(".")} ${saat}`;
  }

  // Oynatılırken ekranda gösterilen saat, çekirdeğin saatinin önünde akar.
  async function gorunenSimdi() {
    return Oynat.aktif ? msDenIso(Oynat.gorsel) : K.cagir("simdi");
  }

  // ------------------------------------------------------------------
  // Oynatma modu — görsel saat akıcı ilerler; çekirdeğe yalnızca bir olay
  // anına (gelmedi/tamamlandı/haftalık sıfırlama) gelindiğinde, gece
  // atlanırken ve duraklatılınca `saat` komutu gider. Böylece günlük ve geri
  // alma geçmişi saniyede onlarca kayıtla dolmaz.
  // ------------------------------------------------------------------
  const OYNAT_HIZLARI = [
    { dkSn: 5, etiket: "5 dk/sn" },
    { dkSn: 15, etiket: "15 dk/sn" },
    { dkSn: 60, etiket: "1 sa/sn" },
  ];
  const OYNAT_KARE_MS = 200;
  const DURUM_DEGISTIREN = new Set(["saat", "rezervasyon", "paket", "iptal", "giris", "cikis", "bekleme", "kullanici_ekle", "kaynak_ekle", "geri_al"]);

  function isoDenMs(iso) {
    const [t, s] = iso.split("T");
    const [y, a, g] = t.split("-").map(Number);
    const [h, m] = s.split(":").map(Number);
    return new Date(y, a - 1, g, h, m).getTime();
  }
  function msDenIso(ms) { return isoYerel(new Date(ms)); }

  async function oynatSonrakiOlayiAl() {
    const t = await K.cagir("sonraki_olay_zamani", {}, { kancasiz: true });
    Oynat.sonrakiOlay = t ? isoDenMs(t) : null;
  }

  async function oynatBaslat() {
    if (Oynat.aktif || !(await K.yukluMu())) return;
    const p = await parametrelerAl();
    const [[bh, bm], [eh, em]] = p.calisma_saatleri;
    Oynat.calismaBasDk = bh * 60 + bm;
    Oynat.calismaBitDk = eh * 60 + em;
    Oynat.gorsel = isoDenMs(await K.cagir("simdi"));
    await oynatSonrakiOlayiAl();
    Oynat.aktif = true;
    Oynat.sonKare = performance.now();
    Oynat.zamanlayici = setInterval(oynatKare, OYNAT_KARE_MS);
    oynatArayuzGuncelle();
  }

  async function oynatDurdur() {
    if (!Oynat.aktif) return;
    Oynat.aktif = false;
    clearInterval(Oynat.zamanlayici);
    while (Oynat.mesgul) await new Promise((r) => setTimeout(r, 20));
    oynatArayuzGuncelle();
    const cekirdek = isoDenMs(await K.cagir("simdi"));
    const hedef = Math.floor(Oynat.gorsel / 60000) * 60000;
    if (hedef > cekirdek) await K.cagir("saat", { zaman: msDenIso(hedef) }, { kancasiz: true });
    else ustBarYenile();
  }

  function oynatSifirla() {
    Oynat.aktif = false;
    clearInterval(Oynat.zamanlayici);
    oynatArayuzGuncelle();
  }

  function oynatDegistir() { return Oynat.aktif ? oynatDurdur() : oynatBaslat(); }

  async function oynatKare() {
    if (!Oynat.aktif || Oynat.mesgul) return;
    const simdiPerf = performance.now();
    const gecenSn = (simdiPerf - Oynat.sonKare) / 1000;
    Oynat.sonKare = simdiPerf;
    const hedef = Oynat.gorsel + gecenSn * OYNAT_HIZLARI[Oynat.hizNo].dkSn * 60000;

    const d = new Date(hedef);
    const dk = d.getHours() * 60 + d.getMinutes();
    if (dk >= Oynat.calismaBitDk || dk < Oynat.calismaBasDk) {
      const sabah = new Date(d);
      if (dk >= Oynat.calismaBitDk) sabah.setDate(sabah.getDate() + 1);
      sabah.setHours(Math.floor(Oynat.calismaBasDk / 60), Oynat.calismaBasDk % 60, 0, 0);
      await oynatCekirdegeGit(sabah.getTime());
      return;
    }
    if (Oynat.sonrakiOlay !== null && hedef >= Oynat.sonrakiOlay) {
      await oynatCekirdegeGit(Oynat.sonrakiOlay);
      return;
    }
    Oynat.gorsel = hedef;
    const iso = msDenIso(hedef);
    saatGoster(iso);
    Takvim.simdiyiGuncelle(iso);
  }

  async function oynatCekirdegeGit(ms) {
    Oynat.mesgul = true;
    try {
      const takipEdiliyor = S.seciliGun === msDenIso(Oynat.gorsel).slice(0, 10);
      const iso = msDenIso(ms);
      const sonuc = await K.cagir("saat", { zaman: iso }, { kancasiz: true });
      if (sonuc.durum !== "TAMAM") { oynatSifirla(); return; }
      Oynat.gorsel = ms;
      if (sonuc.olaylar && sonuc.olaylar.length) {
        gosterSonuc({ ok: true, title: `${iso.slice(11)} · ${sonuc.olaylar.length} olay`, lines: olaySatirlari(sonuc.olaylar) });
      }
      const yeniGun = iso.slice(0, 10);
      if (takipEdiliyor && yeniGun !== S.seciliGun) {
        S.seciliGun = yeniGun;
        gunEtiketiGuncelle();
        varsayilanKalemler();
      }
      saatGoster(iso);
      await takvimYenile();
      await oynatSonrakiOlayiAl();
    } finally {
      Oynat.sonKare = performance.now();
      Oynat.mesgul = false;
    }
  }

  function oynatArayuzGuncelle() {
    const btn = $("oynat-btn");
    btn.textContent = Oynat.aktif ? "⏸" : "▶";
    btn.classList.toggle("oynuyor", Oynat.aktif);
    $("saat-kutu").classList.toggle("oynuyor", Oynat.aktif);
    const hiz = OYNAT_HIZLARI[Oynat.hizNo].etiket;
    $("oynat-hiz-btn").textContent = hiz;
    $("saat-etiket").textContent = Oynat.aktif ? `Oynatılıyor · ${hiz}` : "Simüle saat";
  }

  K.onKomutOncesi(async (yontem) => {
    if (Oynat.aktif && DURUM_DEGISTIREN.has(yontem)) await oynatDurdur();
  });

  $("oynat-btn").addEventListener("click", (ev) => { ev.currentTarget.blur(); oynatDegistir(); });
  $("oynat-hiz-btn").addEventListener("click", (ev) => {
    ev.currentTarget.blur();
    Oynat.hizNo = (Oynat.hizNo + 1) % OYNAT_HIZLARI.length;
    oynatArayuzGuncelle();
  });

  async function saatiIlerlet(hedefIso) {
    const sonuc = await K.cagir("saat", { zaman: hedefIso });
    if (sonuc.durum === "TAMAM") {
      const olaylar = sonuc.olaylar || [];
      gosterSonuc({
        ok: true, title: `Saat → ${hedefIso.slice(11)}`,
        lines: olaylar.length ? olaySatirlari(olaylar) : ["Olay oluşmadı."],
      });
    } else {
      gosterSonuc({ ok: false, title: "SAAT_GERI", lines: [await K.cagir("hata_aciklamasi", { kod: sonuc.kod })] });
    }
  }
  function olaySatirlari(olaylar) {
    return olaylar.map((o) => o.tur === "OTOMATIK_ATAMA"
      ? `OTOMATIK_ATAMA → ${o.rezervasyon} (${o.kullanici}, ${o.ucret} KP)`
      : `${o.tur} · ${o.rezervasyon || ""} · ${o.kullanici || ""} ${o.guvenilirlik !== undefined ? "güv. " + o.guvenilirlik : ""}`.trim());
  }

  $("artir-15-btn").addEventListener("click", async () => saatiIlerlet(await kaydirilmisSaat(15)));
  $("artir-60-btn").addEventListener("click", async () => saatiIlerlet(await kaydirilmisSaat(60)));
  $("artir-gun-btn").addEventListener("click", async () => saatiIlerlet(await kaydirilmisSaat(240)));
  $("sonraki-olay-btn").addEventListener("click", async () => {
    await oynatDurdur();
    const hedef = await K.cagir("sonraki_olay_zamani");
    if (hedef) saatiIlerlet(hedef);
  });
  $("saate-git-btn").addEventListener("click", async () => {
    await oynatDurdur();
    const mevcut = await K.cagir("simdi");
    const girdi = prompt("Saate git (YYYY-AA-GGTSS:DD)", mevcut);
    if (girdi && girdi.trim()) saatiIlerlet(girdi.trim());
  });
  $("geri-al-btn").addEventListener("click", () => K.cagir("geri_al"));

  async function kaydirilmisSaat(dakika) {
    await oynatDurdur();
    const simdi = await K.cagir("simdi");
    const d = new Date(simdi.replace("T", " ") + ":00");
    d.setMinutes(d.getMinutes() + dakika);
    return isoYerel(d);
  }
  function isoYerel(d) {
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
  }

  // ------------------------------------------------------------------
  // Sonuç banner'ı (tüm işlemler için TEK ortak bileşen)
  // ------------------------------------------------------------------
  function sonucKapat() {
    const saril = $("sonuc-banner-saril");
    saril.style.display = "none";
    saril.innerHTML = "";
  }

  function gosterSonuc({ ok, title, lines = [], kalemler = null, waitable = null, kod = null, mesaj = null, oneriler = null }) {
    const saril = $("sonuc-banner-saril");
    saril.style.display = "block";
    const banner = document.createElement("div");
    banner.className = "sonuc-banner " + (ok ? "ok" : "hata");
    const icerik = document.createElement("div");
    const baslikEl = document.createElement("div");
    baslikEl.className = "sonuc-baslik";
    baslikEl.textContent = title;
    if (kod) baslikEl.appendChild(kodCipi(kod));
    icerik.appendChild(baslikEl);

    if (mesaj) {
      const p = document.createElement("p");
      p.className = "sonuc-mesaj";
      p.textContent = mesaj;
      icerik.appendChild(p);
    }

    if (kalemler) {
      const ul = document.createElement("ul");
      ul.className = "sonuc-satirlar";
      kalemler.forEach((k, i) => {
        const li = document.createElement("li");
        li.className = "sonuc-kalem " + (k.durum === "TAMAM" ? "gecti" : "red");
        li.textContent = `Kalem ${i + 1} · ${k.kaynak || ""} → ${k.durum === "TAMAM" ? "geçti" : k.mesaj || k.kod}`;
        ul.appendChild(li);
      });
      icerik.appendChild(ul);
    } else if (lines.length) {
      const ul = document.createElement("ul");
      ul.className = "sonuc-satirlar";
      lines.forEach((l) => { const li = document.createElement("li"); li.textContent = l; ul.appendChild(li); });
      icerik.appendChild(ul);
    }

    if (waitable) {
      const btn = document.createElement("button");
      btn.className = "btn btn-primary btn-mono";
      btn.style.marginTop = "10px";
      btn.textContent = "Bu aralık için bekleme listesine gir";
      btn.addEventListener("click", async () => {
        const sonuc = await K.cagir("bekleme", waitable);
        if (sonuc.durum === "TAMAM") gosterSonuc({ ok: true, title: `Bekleme kaydı açıldı: ${sonuc.bekleme_id}`, lines: [`Sıra: ${sonuc.sira}`] });
        else gosterSonuc({ ok: false, title: sonuc.kod, lines: [await K.cagir("hata_aciklamasi", { kod: sonuc.kod })] });
      });
      icerik.appendChild(btn);
    }

    if (oneriler) {
      const kutu = document.createElement("div");
      kutu.className = "oneri-kutu";
      if (oneriKutusunuCiz(kutu, oneriler, sonucKapat)) icerik.appendChild(kutu);
    }

    const kapatBtn = document.createElement("button");
    kapatBtn.className = "btn btn-ghost btn-ikon";
    kapatBtn.textContent = "✕";
    kapatBtn.style.cssText = "width:28px;height:28px;flex-shrink:0;";
    kapatBtn.addEventListener("click", sonucKapat);

    banner.appendChild(icerik);
    banner.appendChild(kapatBtn);
    saril.innerHTML = "";
    saril.appendChild(banner);
  }

  // ------------------------------------------------------------------
  // Gün navigasyonu + takvim
  // ------------------------------------------------------------------
  function gunEtiketiGuncelle() {
    if (!S.seciliGun) return;
    const d = new Date(S.seciliGun + "T00:00:00");
    const gunAdi = ["Paz", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt"][d.getDay()];
    $("gun-gosterge").textContent = `${gunAdi} ${d.toLocaleDateString("tr-TR")}`;
    $("talep-altyazi").textContent = `${S.seciliGun} için`;
  }

  async function takvimYenile() {
    if (!(await K.yukluMu()) || !S.seciliGun) return;
    const gunVeri = await K.cagir("gun_gorunumu", { gun: S.seciliGun });
    const simdi = await gorunenSimdi();
    Takvim.goster(gunVeri, S.seciliGun, simdi, S.filtreAktif ? S.seciliKullanici : null);
  }

  function gunDegistir(delta) {
    if (!S.seciliGun) return;
    const d = new Date(S.seciliGun + "T00:00:00");
    d.setDate(d.getDate() + delta);
    S.seciliGun = isoYerel(d).split("T")[0];
    gunEtiketiGuncelle();
    takvimYenile();
    varsayilanKalemler();
  }
  $("gun-geri-btn").addEventListener("click", () => gunDegistir(-1));
  $("gun-ileri-btn").addEventListener("click", () => gunDegistir(1));
  $("bugun-btn").addEventListener("click", async () => {
    const simdi = await gorunenSimdi();
    S.seciliGun = simdi.split("T")[0];
    gunEtiketiGuncelle();
    takvimYenile();
    varsayilanKalemler();
  });
  $("filtre-kutusu").addEventListener("change", (ev) => {
    S.filtreAktif = ev.target.checked;
    takvimYenile();
  });
  $("kaynak-ekle-btn").addEventListener("click", () => kaynakModalAc());

  Takvim.kur($("takvim-kaydir"), $("takvim-govde"), {
    onRezervasyonTiklandi: (id) => { S.seciliRezId = id; rezDetayYenile(); },
    onBosAlanSecildi: (kaynakId, b, e) => {
      modSec("tek");
      S.kalemler = [{ kaynak: kaynakId, bas: b.slice(11), bit: e.slice(11) }];
      kalemleriCiz();
      fiyatlariGuncelleGecikmeli();
      $("gonder-btn").scrollIntoView({ behavior: "smooth", block: "center" });
    },
  });

  // ------------------------------------------------------------------
  // Seçili rezervasyon kartı
  // ------------------------------------------------------------------
  $("rez-detay-kapat").addEventListener("click", () => { S.seciliRezId = null; rezDetayYenile(); takvimYenile(); });

  async function rezDetayYenile() {
    const kart = $("rez-detay-kart");
    if (!S.seciliRezId) { kart.style.display = "none"; return; }
    const detay = await K.cagir("rezervasyon_detayi", { id: S.seciliRezId });
    if (!detay) { kart.style.display = "none"; S.seciliRezId = null; return; }
    kart.style.display = "block";
    $("rez-detay-baslik").textContent = `Rezervasyon ${detay.id}`;

    const liste = await K.cagir("kullanicilar");
    const kullanici = liste.find((u) => u.id === detay.kullanici);
    const govde = $("rez-detay-govde");
    const satir = (etiket, deger) => `<div style="color:var(--muted-foreground);">${etiket}</div><div class="mono">${deger}</div>`;
    govde.innerHTML =
      satir("Kullanıcı", kullanici ? kullanici.ad : detay.kullanici) +
      satir("Kaynak", detay.kaynak) +
      satir("Aralık", `${detay.baslangic.slice(0, 10)} ${detay.baslangic.slice(11)}–${detay.bitis.slice(11)}`) +
      satir("Ücret", `${detay.ucret} KP`) +
      satir("Durum", `<span class="rozet-durum"><span class="nokta nokta-${detay.durum}"></span>${detay.durum}</span>`) +
      (detay.paket ? satir("Paket", detay.paket) : "");

    const onizlemeEl = $("rez-detay-onizleme");
    if (detay.durum === "ONAYLI") {
      const on = await K.cagir("iptal_onizleme", { id: S.seciliRezId });
      if (on) {
        const guvenEk = on.guvenilirlik_delta ? ` · güvenilirlik ${on.guvenilirlik_delta}` : "";
        onizlemeEl.textContent = `İptal edilirse: %${on.oran} iade (${on.iade} KP)${guvenEk}`;
        onizlemeEl.style.display = "block";
      }
    } else onizlemeEl.style.display = "none";
  }

  async function rezEylem(yontem) {
    if (!S.seciliRezId) return;
    const sonuc = await K.cagir(yontem, { rezervasyon: S.seciliRezId });
    if (sonuc.durum === "RED") {
      gosterSonuc({ ok: false, title: `${yontem.toUpperCase()} reddedildi`, lines: [await K.cagir("hata_aciklamasi", { kod: sonuc.kod })] });
      return;
    }
    const lines = [];
    if ("iade" in sonuc) lines.push(`İade: ${sonuc.iade} KP`, `Bakiye: ${sonuc.bakiye} KP`);
    if ("guvenilirlik" in sonuc) lines.push(`Güvenilirlik: ${sonuc.guvenilirlik}`);
    if (sonuc.olaylar) lines.push(...olaySatirlari(sonuc.olaylar));
    gosterSonuc({ ok: true, title: `${S.seciliRezId} · ${yontem} tamam`, lines });
  }
  $("rd-giris-btn").addEventListener("click", () => rezEylem("giris"));
  $("rd-cikis-btn").addEventListener("click", () => rezEylem("cikis"));
  $("rd-iptal-btn").addEventListener("click", () => rezEylem("iptal"));

  // ------------------------------------------------------------------
  // Kullanıcı paneli (+ üst bardaki seçici)
  // ------------------------------------------------------------------
  async function kullanicilariDoldur() {
    const secimKorunur = S.seciliKullanici;
    const liste = await K.cagir("kullanicilar");
    const sel = $("kullanici-secici");
    sel.innerHTML = "";
    liste.forEach((u) => {
      const o = document.createElement("option");
      o.value = u.id;
      o.textContent = `${u.ad} · ${u.rol}`;
      sel.appendChild(o);
    });
    if (secimKorunur && liste.some((u) => u.id === secimKorunur)) sel.value = secimKorunur;
    S.seciliKullanici = sel.value || null;
  }
  $("kullanici-secici").addEventListener("change", (ev) => {
    S.seciliKullanici = ev.target.value || null;
    kullaniciPaneliYenile();
    takvimYenile();
    fiyatlariGuncelleGecikmeli();
  });
  $("kullanici-ekle-btn").addEventListener("click", () => kullaniciModalAc());

  async function kullaniciPaneliYenile() {
    if (!S.seciliKullanici || !(await K.yukluMu())) return;
    const sonuc = await K.kullaniciDetayi(S.seciliKullanici);
    if (sonuc.durum !== "TAMAM") return;

    const parametreler = await parametrelerAl();
    const liste = await K.cagir("kullanicilar");
    const kullanici = liste.find((u) => u.id === S.seciliKullanici);
    $("kp-ad").textContent = kullanici ? kullanici.ad : S.seciliKullanici;
    $("kp-rol").textContent = kullanici ? kullanici.rol : "";
    const kota = kullanici && parametreler.roller[kullanici.rol] ? parametreler.roller[kullanici.rol].haftalik_kota : null;

    $("kp-bakiye").innerHTML = `${sonuc.bakiye} ${kota ? `<small>/ ${kota} KP</small>` : ""}`;
    $("kp-bakiye-bar").style.width = kota ? `${Math.max(0, Math.min(100, (sonuc.bakiye / kota) * 100))}%` : "0%";
    $("kp-guven").innerHTML = `${sonuc.guvenilirlik} <small>/ 100</small>`;
    $("kp-guven-bar").style.width = `${Math.max(0, Math.min(100, sonuc.guvenilirlik))}%`;

    $("kp-sertifikalar").innerHTML = (kullanici && kullanici.sertifikalar ? kullanici.sertifikalar : [])
      .map((c) => `<span class="sertifika-cip">${c}</span>`).join("");

    const rezListe = $("kp-rezliste");
    rezListe.innerHTML = sonuc.rezervasyonlar.length === 0 ? '<p class="liste-bos">Yok</p>' : "";
    sonuc.rezervasyonlar.forEach((r) => {
      const btn = document.createElement("button");
      btn.className = "liste-satir";
      btn.innerHTML = `<span class="nokta nokta-${r.durum}"></span><span style="font-weight:600;">${r.id}</span>` +
        `<span style="color:var(--muted-foreground);">${r.kaynak}</span>` +
        `<span style="color:var(--muted-foreground);">${r.baslangic.slice(11)}–${r.bitis.slice(11)}</span>` +
        `<span style="margin-left:auto;">${r.ucret}</span>`;
      btn.addEventListener("click", () => { S.seciliRezId = r.id; rezDetayYenile(); });
      rezListe.appendChild(btn);
    });

    const beklemeListe = $("kp-beklemeliste");
    const bekleme = await K.cagir("kullanici_bekleme_kayitlari", { id: S.seciliKullanici });
    beklemeListe.innerHTML = bekleme.length === 0 ? '<p class="liste-bos">Yok</p>' : "";
    bekleme.forEach((b) => {
      const d = document.createElement("div");
      d.className = "mono";
      d.style.cssText = "font-size:12px; padding:3px 8px; color:var(--muted-foreground);";
      d.textContent = `${b.id} · ${b.kaynak} · ${b.baslangic.slice(11)}–${b.bitis.slice(11)} · sıra ${b.sira}`;
      beklemeListe.appendChild(d);
    });
  }

  // ------------------------------------------------------------------
  // Talep formu (tek = 1 kalemlik "paket"; mimari basitleşir)
  // ------------------------------------------------------------------
  async function varsayilanKalemler() {
    const kaynaklar = await K.cagir("kaynaklar");
    const ilkKaynak = kaynaklar[0] ? kaynaklar[0].id : "";
    const { bas, bit } = await varsayilanSaatAraligi();
    S.kalemler = [{ kaynak: ilkKaynak, bas, bit }];
    kalemleriCiz();
    fiyatlariGuncelleGecikmeli();
  }

  async function varsayilanSaatAraligi() {
    const simdiIso = await K.cagir("simdi");
    const simdi = new Date(simdiIso.replace("T", " ") + ":00");
    let taban = S.seciliGun === simdiIso.split("T")[0] ? simdi : new Date(S.seciliGun + "T08:00:00");
    const kalan = (15 - (taban.getMinutes() % 15)) % 15;
    taban = new Date(taban.getTime() + kalan * 60000);
    if (taban.getHours() < 8) taban.setHours(8, 0, 0, 0);
    if (taban.getHours() >= 21) taban.setHours(21, 0, 0, 0);
    const bitis = new Date(taban.getTime() + 60 * 60000);
    if (bitis.getHours() > 22 || (bitis.getHours() === 22 && bitis.getMinutes() > 0)) bitis.setHours(22, 0, 0, 0);
    const f = (d) => `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
    return { bas: f(taban), bit: f(bitis) };
  }

  function modSec(mod) {
    S.mod = mod;
    document.querySelectorAll(".segment-opsiyon").forEach((o) => o.classList.toggle("secili", o.dataset.mod === mod));
    $("paket-dugmeler").style.display = mod === "paket" ? "flex" : "none";
    if (mod === "tek") {
      S.kalemler = S.kalemler.slice(0, 1);
    } else if (S.kalemler.length < 2) {
      K.cagir("kaynaklar").then((kaynaklar) => {
        const kid = kaynaklar[1] ? kaynaklar[1].id : kaynaklar[0]?.id;
        S.kalemler.push({ kaynak: kid, bas: S.kalemler[0]?.bas || "11:00", bit: S.kalemler[0]?.bit || "12:00" });
        kalemleriCiz();
        fiyatlariGuncelleGecikmeli();
      });
      return;
    }
    kalemleriCiz();
    fiyatlariGuncelleGecikmeli();
  }
  document.querySelectorAll(".segment-opsiyon").forEach((o) => o.addEventListener("click", () => modSec(o.dataset.mod)));

  async function kalemleriCiz() {
    const kaynaklar = await K.cagir("kaynaklar");
    const govde = $("kalemler-govde");
    govde.innerHTML = "";
    S.kalemler.forEach((kalem, i) => {
      const satir = document.createElement("div");
      satir.className = "kalem-satir";

      const kaynakSel = document.createElement("select");
      kaynakSel.className = "girdi-sm";
      kaynaklar.forEach((k) => {
        const o = document.createElement("option");
        o.value = k.id; o.textContent = `${k.id} · ${k.ad}`;
        if (k.id === kalem.kaynak) o.selected = true;
        kaynakSel.appendChild(o);
      });
      kaynakSel.addEventListener("change", (ev) => { S.kalemler[i].kaynak = ev.target.value; fiyatlariGuncelleGecikmeli(); });

      const basInp = document.createElement("input");
      basInp.className = "girdi-sm mono"; basInp.style.width = "84px"; basInp.setAttribute("list", "saat-secenekleri");
      basInp.value = kalem.bas;
      basInp.addEventListener("input", (ev) => { S.kalemler[i].bas = ev.target.value; fiyatlariGuncelleGecikmeli(); });

      const bitInp = document.createElement("input");
      bitInp.className = "girdi-sm mono"; bitInp.style.width = "84px"; bitInp.setAttribute("list", "saat-secenekleri");
      bitInp.value = kalem.bit;
      bitInp.addEventListener("input", (ev) => { S.kalemler[i].bit = ev.target.value; fiyatlariGuncelleGecikmeli(); });

      const ucretSpan = document.createElement("span");
      ucretSpan.className = "kalem-ucret";
      ucretSpan.id = `kalem-ucret-${i}`;
      ucretSpan.textContent = "— KP";

      satir.append(kaynakSel, basInp, bitInp, ucretSpan);
      govde.appendChild(satir);

      const uyari = document.createElement("div");
      uyari.className = "kalem-uyari";
      uyari.id = `kalem-uyari-${i}`;
      uyari.style.display = "none";
      govde.appendChild(uyari);
    });
  }

  function kodCipi(kod) {
    const cip = document.createElement("span");
    cip.className = "kod-cip";
    cip.textContent = kod;
    return cip;
  }

  function kalemUyarisiGoster(i, mesaj, kod) {
    const el = $(`kalem-uyari-${i}`);
    if (!el) return;
    if (!mesaj) { el.style.display = "none"; el.innerHTML = ""; return; }
    el.innerHTML = "";
    const ikon = document.createElement("span");
    ikon.className = "kalem-uyari-ikon";
    ikon.textContent = "!";
    const metin = document.createElement("span");
    metin.textContent = mesaj;
    metin.appendChild(kodCipi(kod));
    el.append(ikon, metin);
    el.style.display = "flex";
  }

  function oneriEtiketi(o, kaynakGoster) {
    const gun = o.baslangic.slice(0, 10);
    const tarih = gun === S.seciliGun ? "" : `${gun.slice(8, 10)}.${gun.slice(5, 7)} `;
    return `${kaynakGoster ? o.kaynak + " · " : ""}${tarih}${o.baslangic.slice(11)}–${o.bitis.slice(11)}`;
  }

  // Öneri çiplerini `hedef`e çizer; gösterilecek öneri yoksa false döner.
  function oneriKutusunuCiz(hedef, oneriler, secilince) {
    hedef.innerHTML = "";
    const gruplar = [
      { baslik: "Uygun saatler", liste: oneriler.zaman || [], kaynakGoster: false },
      { baslik: "Aynı saatte uygun kaynaklar", liste: oneriler.kaynak || [], kaynakGoster: true },
    ].filter((g) => g.liste.length);
    if (!gruplar.length) return false;

    gruplar.forEach((g) => {
      const grup = document.createElement("div");
      grup.className = "oneri-grup";
      const baslik = document.createElement("div");
      baslik.className = "oneri-baslik";
      baslik.textContent = g.baslik;
      const cipler = document.createElement("div");
      cipler.className = "oneri-cipler";
      g.liste.forEach((o) => {
        const cip = document.createElement("button");
        cip.className = "oneri-cip";
        cip.title = `${o.kaynak} · ${o.kaynak_ad} — forma uygula`;
        const etiket = document.createElement("span");
        etiket.textContent = oneriEtiketi(o, g.kaynakGoster);
        cip.appendChild(etiket);
        if (g.kaynakGoster) {
          const ek = document.createElement("span");
          ek.className = "oneri-ek";
          ek.textContent = o.kaynak_ad;
          cip.appendChild(ek);
        }
        const ucret = document.createElement("span");
        ucret.className = "oneri-ucret";
        ucret.textContent = `${o.ucret} KP`;
        cip.appendChild(ucret);
        cip.addEventListener("click", () => { oneriUygula(o); if (secilince) secilince(); });
        cipler.appendChild(cip);
      });
      grup.append(baslik, cipler);
      hedef.appendChild(grup);
    });
    return true;
  }

  function oneriUygula(o) {
    const gun = o.baslangic.slice(0, 10);
    if (gun !== S.seciliGun) {
      S.seciliGun = gun;
      gunEtiketiGuncelle();
      takvimYenile();
    }
    if (S.mod !== "tek") modSec("tek");
    S.kalemler = [{ kaynak: o.kaynak, bas: o.baslangic.slice(11), bit: o.bitis.slice(11) }];
    kalemleriCiz();
    fiyatlariGuncelleGecikmeli();
  }

  function talepArgumanlari(kalem) {
    return {
      kullanici: S.seciliKullanici,
      kaynak: kalem.kaynak,
      baslangic: `${S.seciliGun}T${kalem.bas}`,
      bitis: `${S.seciliGun}T${kalem.bit}`,
    };
  }

  let fiyatZamanlayici = null;
  let fiyatTuru = 0;
  function fiyatlariGuncelleGecikmeli() {
    clearTimeout(fiyatZamanlayici);
    fiyatZamanlayici = setTimeout(fiyatlariGuncelle, HATA_ARAMA_GECIKME);
  }

  async function fiyatlariGuncelle() {
    if (!S.seciliKullanici || !(await K.yukluMu()) || !S.kalemler.length) return;
    // Yeni bir tur başladıysa eski turun (geç gelen) sonuçları çizilmez.
    const tur = ++fiyatTuru;
    const guncel = () => tur === fiyatTuru;
    let toplam = 0;
    let oneriTalebi = null;
    for (let i = 0; i < S.kalemler.length; i++) {
      const kalem = S.kalemler[i];
      const span = $(`kalem-ucret-${i}`);
      if (!kalem.kaynak || !kalem.bas || !kalem.bit) {
        if (span) span.textContent = "— KP";
        kalemUyarisiGoster(i, null);
        continue;
      }
      try {
        const args = talepArgumanlari(kalem);
        const sonuc = await K.cagir("fiyat", args);
        if (!guncel()) return;
        if (sonuc.durum === "TAMAM") {
          if (span) { span.textContent = `${sonuc.ucret} KP`; span.style.color = "var(--primary)"; span.title = ""; }
          kalemUyarisiGoster(i, null);
          toplam += sonuc.ucret;
        } else {
          const mesaj = await K.cagir("red_aciklamasi", { ...args, kod: sonuc.kod });
          if (!guncel()) return;
          if (span) { span.textContent = "✕"; span.style.color = "var(--destructive)"; span.title = sonuc.kod; }
          kalemUyarisiGoster(i, mesaj, sonuc.kod);
          if (S.mod === "tek" && i === 0) oneriTalebi = args;
        }
      } catch (e) { /* köprü hatası: önizleme sessizce boş kalır */ }
    }
    $("ucret-toplam").textContent = `${toplam} KP`;

    const oneriKutu = $("oneri-kutu");
    if (oneriTalebi) {
      const oneriler = await K.cagir("uygun_araliklar", oneriTalebi);
      if (!guncel()) return;
      oneriKutu.style.display = oneriKutusunuCiz(oneriKutu, oneriler) ? "block" : "none";
    } else {
      oneriKutu.style.display = "none";
      oneriKutu.innerHTML = "";
    }

    const liste = await K.cagir("kullanicilar");
    const kullanici = liste.find((u) => u.id === S.seciliKullanici);
    if (kullanici) {
      $("ozet-bakiye").textContent = `${kullanici.bakiye} KP`;
      const sonrasi = kullanici.bakiye - toplam;
      const el = $("ozet-sonrasi");
      el.textContent = `${sonrasi} KP`;
      el.classList.toggle("negatif", sonrasi < 0);
    }
  }

  $("kalem-ekle-btn").addEventListener("click", async () => {
    if (S.kalemler.length >= 4) return;
    const kaynaklar = await K.cagir("kaynaklar");
    const kid = kaynaklar[S.kalemler.length % kaynaklar.length]?.id;
    S.kalemler.push({ kaynak: kid, bas: "11:00", bit: "12:00" });
    kalemleriCiz();
    fiyatlariGuncelleGecikmeli();
  });
  $("kalem-sil-btn").addEventListener("click", () => {
    if (S.kalemler.length <= 2) return;
    S.kalemler.pop();
    kalemleriCiz();
    fiyatlariGuncelleGecikmeli();
  });

  $("gonder-btn").addEventListener("click", async () => {
    if (!S.seciliKullanici || !(await K.yukluMu()) || !S.kalemler.length) return;
    const parsed = S.kalemler.map((k) => ({ kaynak: k.kaynak, baslangic: `${S.seciliGun}T${k.bas}`, bitis: `${S.seciliGun}T${k.bit}` }));

    if (S.mod === "tek") {
      const p = parsed[0];
      const args = { kullanici: S.seciliKullanici, kaynak: p.kaynak, baslangic: p.baslangic, bitis: p.bitis };
      const sonuc = await K.cagir("rezervasyon", args);
      if (sonuc.durum === "RED") {
        const waitable = ["KESISME", "HAZIRLIK_IHLALI"].includes(sonuc.kod) ? args : null;
        const [mesaj, oneriler] = await Promise.all([
          K.cagir("red_aciklamasi", { ...args, kod: sonuc.kod }),
          K.cagir("uygun_araliklar", args),
        ]);
        gosterSonuc({ ok: false, title: "Rezervasyon reddedildi", kod: sonuc.kod, mesaj, waitable, oneriler });
      } else {
        gosterSonuc({ ok: true, title: `Onaylandı · ${sonuc.rezervasyon_id}`, lines: [`Ücret: ${sonuc.ucret} KP`, `Yeni bakiye: ${sonuc.bakiye} KP`] });
      }
    } else {
      const sonuc = await K.cagir("paket", { kullanici: S.seciliKullanici, kalemler: parsed });
      if (sonuc.durum === "RED") {
        if (sonuc.kod === "PAKET_RED") {
          const kalemler = await Promise.all((sonuc.kalemler || []).map(async (k, i) => {
            const p = parsed[k.sira ?? i];
            const mesaj = k.durum === "TAMAM" || !p ? null
              : await K.cagir("red_aciklamasi", { kullanici: S.seciliKullanici, ...p, kod: k.kod });
            return { kaynak: p?.kaynak, durum: k.durum, kod: k.kod, mesaj };
          }));
          gosterSonuc({ ok: false, title: "Paket reddedildi", kod: sonuc.kod, kalemler });
        } else {
          gosterSonuc({ ok: false, title: "Paket reddedildi", kod: sonuc.kod, mesaj: await K.cagir("hata_aciklamasi", { kod: sonuc.kod }) });
        }
      } else {
        gosterSonuc({ ok: true, title: `Paket onaylandı · ${sonuc.paket_id}`, lines: [`Rezervasyonlar: ${sonuc.rezervasyonlar.join(", ")}`, `Toplam: ${sonuc.toplam} KP`, `Yeni bakiye: ${sonuc.bakiye} KP`] });
        document.querySelectorAll("#kalemler-govde .kalem-ucret").forEach((s) => (s.style.color = "var(--success)"));
      }
    }
  });

  // ------------------------------------------------------------------
  // Olay günlüğü (akordeon)
  // ------------------------------------------------------------------
  async function gunlukYenile() {
    const kayitlar = await K.gunluk();
    const filtre = $("gunluk-filtre").value;
    const arama = $("gunluk-arama").value.trim().toLowerCase();
    const govde = $("gunluk-liste");
    govde.innerHTML = "";
    let gosterilen = 0;
    kayitlar.forEach((k) => {
      const durum = k.sonuc.durum || "";
      if (filtre !== "Tümü" && durum !== filtre) return;
      if (arama && !JSON.stringify(k).toLowerCase().includes(arama)) return;
      gosterilen++;

      const sarmal = document.createElement("div");
      const btn = document.createElement("button");
      btn.className = "log-satir-btn" + (S.gunlukSecimNo === k.no ? " acik" : "");
      const kod = k.sonuc.kod || k.sonuc.durum || "";
      btn.innerHTML =
        `<span class="nokta nokta-${durum === "TAMAM" ? "ONAYLI" : "IPTAL"}"></span>` +
        `<span style="color:var(--muted-foreground);">#${k.no}</span>` +
        `<span style="font-weight:600;">${k.komut.komut || ""}</span>` +
        `<span class="log-sonuc-kisa">${kod}</span>`;
      btn.addEventListener("click", () => {
        S.gunlukSecimNo = S.gunlukSecimNo === k.no ? null : k.no;
        gunlukYenile();
      });
      sarmal.appendChild(btn);

      if (S.gunlukSecimNo === k.no) {
        const detay = document.createElement("div");
        detay.className = "log-detay";
        detay.innerHTML =
          `<div class="log-detay-baslik">komut</div><pre>${JSON.stringify(k.komut)}</pre>` +
          `<div class="log-detay-baslik">sonuç</div><pre>${JSON.stringify({ no: k.no, ...k.sonuc })}</pre>`;
        sarmal.appendChild(detay);
      }
      govde.appendChild(sarmal);
    });
    $("gunluk-sayac").textContent = `${gosterilen} kayıt`;
    // Not: sayfa artık tek parça kaydığı için günlük her yenilendiğinde
    // (yani her işlemden sonra) kullanıcıyı sayfanın en altına zıplatmıyoruz.
  }
  $("gunluk-filtre").addEventListener("change", gunlukYenile);
  $("gunluk-arama").addEventListener("input", gunlukYenile);

  // ------------------------------------------------------------------
  // Modallar
  // ------------------------------------------------------------------
  async function parametrelerAl() {
    if (!S.paramCache) S.paramCache = await K.cagir("parametreler");
    return S.paramCache;
  }
  document.querySelectorAll("[data-kapat]").forEach((btn) => btn.addEventListener("click", () => $(btn.dataset.kapat).classList.add("gizli")));
  document.querySelectorAll(".modal-zemin").forEach((zemin) => zemin.addEventListener("click", (ev) => { if (ev.target === zemin) zemin.classList.add("gizli"); }));

  async function kullaniciModalAc() {
    const p = await parametrelerAl();
    const rolSel = $("ku-rol");
    rolSel.innerHTML = Object.keys(p.roller).sort().map((r) => `<option>${r}</option>`).join("");
    rolSel.onchange = () => { $("ku-bakiye").value = p.roller[rolSel.value].haftalik_kota; };
    rolSel.onchange();
    const sertKutu = $("ku-sertifikalar");
    sertKutu.innerHTML = p.sertifikalar.length
      ? p.sertifikalar.map((s) => `<label><input type="checkbox" value="${s}"/> ${s}</label>`).join("")
      : '<span style="color:var(--muted-foreground); font-size:12px;">(tanımlı değer yok)</span>';
    $("ku-id").value = ""; $("ku-ad").value = ""; $("ku-guven").value = 100;
    $("ku-sonuc").style.display = "none";
    $("kullanici-modal").classList.remove("gizli");
    $("ku-id").focus();
  }
  $("ku-ekle-btn").addEventListener("click", async () => {
    const id = $("ku-id").value.trim();
    const sertifikalar = [...document.querySelectorAll("#ku-sertifikalar input:checked")].map((c) => c.value);
    const sonuc = await K.cagir("kullanici_ekle", {
      id, ad: $("ku-ad").value.trim() || id, rol: $("ku-rol").value,
      sertifikalar, bakiye: Number($("ku-bakiye").value), guvenilirlik: Number($("ku-guven").value),
    });
    const el = $("ku-sonuc");
    el.style.display = "block";
    if (sonuc.durum === "TAMAM") { el.style.color = "var(--success)"; el.textContent = `✓ Kullanıcı ${id} eklendi.`; $("ku-id").value = ""; }
    else { const a = await K.cagir("hata_aciklamasi", { kod: sonuc.kod }); el.style.color = "var(--destructive)"; el.textContent = `✖ ${sonuc.kod} — ${a}`; }
  });

  async function kaynakModalAc() {
    const p = await parametrelerAl();
    const turSel = $("kk-tur");
    turSel.innerHTML = Object.keys(p.turler).sort().map((t) => `<option>${t}</option>`).join("");
    const rolKutu = $("kk-roller");
    rolKutu.innerHTML = Object.keys(p.roller).sort().map((r) => `<label><input type="checkbox" value="${r}"/> ${r}</label>`).join("");
    $("kk-id").value = ""; $("kk-ad").value = "";
    $("kk-sonuc").style.display = "none";
    $("kaynak-modal").classList.remove("gizli");
    $("kk-id").focus();
  }
  $("kk-ekle-btn").addEventListener("click", async () => {
    const id = $("kk-id").value.trim();
    const izinliRoller = [...document.querySelectorAll("#kk-roller input:checked")].map((c) => c.value);
    const sonuc = await K.cagir("kaynak_ekle", { id, ad: $("kk-ad").value.trim() || id, tur: $("kk-tur").value, izinli_roller: izinliRoller });
    const el = $("kk-sonuc");
    el.style.display = "block";
    if (sonuc.durum === "TAMAM") { el.style.color = "var(--success)"; el.textContent = `✓ Kaynak ${id} eklendi.`; $("kk-id").value = ""; }
    else { const a = await K.cagir("hata_aciklamasi", { kod: sonuc.kod }); el.style.color = "var(--destructive)"; el.textContent = `✖ ${sonuc.kod} — ${a}`; }
  });

  // ------------------------------------------------------------------
  // Klavye kısayolları
  // ------------------------------------------------------------------
  document.addEventListener("keydown", (ev) => {
    const yaziAlaninda = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName);
    if (ev.ctrlKey && ev.key === "Enter") { ev.preventDefault(); $("gonder-btn").click(); return; }
    if (ev.ctrlKey && (ev.key === "z" || ev.key === "Z")) { ev.preventDefault(); $("geri-al-btn").click(); return; }
    if (ev.ctrlKey && (ev.key === "f" || ev.key === "F")) { ev.preventDefault(); $("gunluk-arama").focus(); return; }
    if (ev.key === "Escape") { document.querySelectorAll(".modal-zemin").forEach((m) => m.classList.add("gizli")); return; }
    if (yaziAlaninda) return;
    if (ev.key === " ") { ev.preventDefault(); oynatDegistir(); return; }
    if (ev.key === "ArrowLeft") gunDegistir(-1);
    else if (ev.key === "ArrowRight") gunDegistir(1);
    else if (ev.key === "t" || ev.key === "T") $("bugun-btn").click();
    else if (ev.key === "+") $("artir-15-btn").click();
  });

  // ------------------------------------------------------------------
  saatSecenekleriDoldur();
})();
