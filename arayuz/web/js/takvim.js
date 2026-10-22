/* Kaynak takvimi — DOM/CSS tabanlı çizim, hit-test, sürükleyerek talep.
 * Görsel dil github.com/slanur/calendar-clock-spark'tan uyarlanmıştır.
 * Çekirdek `gun_gorunumu()` çağrısının hazır verisini çizer; alt satır
 * yerleşimi, hazırlık şeritleri vb. burada HESAPLANMAZ (Bölüm 8.2). */

window.Takvim = (function () {
  const SAAT_BAS = 8, SAAT_BIT = 22;
  const TOPLAM_DK = (SAAT_BIT - SAAT_BAS) * 60;
  const SOL_GENISLIK = 176;
  const LANE_YUKSEKLIK = 34;
  const KUTU_YUKSEKLIK = 30;

  let kapsayici, govde;
  let veri = {}, gunIso = null, simdiIso = null, sadeceKullanici = null, doluluk = null;
  let onRezTikla = () => {}, onBosAlanSec = () => {};
  let surukleme = null;

  function dkDenX(dk, genislik) { return SOL_GENISLIK + (dk / TOPLAM_DK) * genislik; }
  function zamanDk(isoZaman, gun) {
    const [tarih, saat] = isoZaman.split("T");
    if (tarih !== gun) return null;
    const [h, m] = saat.split(":").map(Number);
    return (h - SAAT_BAS) * 60 + m;
  }
  function el(tag, cls, parent) {
    const e = document.createElement(tag === "div" || !tag ? "div" : tag);
    if (cls) e.className = cls;
    if (parent) parent.appendChild(e);
    return e;
  }

  function kur(kaydirmaEl, govdeEl, geriCagrilar) {
    kapsayici = kaydirmaEl;
    govde = govdeEl;
    onRezTikla = geriCagrilar.onRezervasyonTiklandi || onRezTikla;
    onBosAlanSec = geriCagrilar.onBosAlanSecildi || onBosAlanSec;
    new ResizeObserver(() => cizYeniden()).observe(kapsayici);
  }

  function goster(yeniVeri, gun, simdi, filtre, yeniDoluluk) {
    veri = yeniVeri || {};
    doluluk = yeniDoluluk || null;
    gunIso = gun;
    simdiIso = simdi;
    sadeceKullanici = filtre || null;
    cizYeniden();
  }

  function sadeceFiltreyiGuncelle(filtre) {
    sadeceKullanici = filtre;
    cizYeniden();
  }

  function cizYeniden() {
    if (!govde) return;
    govde.innerHTML = "";

    const kaynaklar = Object.values(veri);
    if (kaynaklar.length === 0) {
      const bos = el("div", null, govde);
      bos.style.cssText = "padding:40px 20px; text-align:center; color:var(--muted-foreground); font-size:13px;";
      bos.textContent = "Bu gün için kaynak yok";
      return;
    }

    const cetvel = el("div", null, govde);
    cetvel.id = "saat-cetveli";
    for (let saat = SAAT_BAS; saat < SAAT_BIT; saat++) {
      const s = el("span", null, cetvel);
      s.textContent = `${String(saat).padStart(2, "0")}:00`;
    }
    dolulukSeridiCiz();

    // 1. geçiş: boş satır iskeletlerini DOM'a ekle (genişlik ölçülebilsin diye)
    const satirlar = kaynaklar.map((k) => iskeletOlustur(k));

    // Gerçek genişlik ancak DOM'a eklendikten SONRA (layout'tan) doğru okunur;
    // konteyner min-width nedeniyle önceden tahmin etmek yanlış piksel verir.
    const ilkSerit = govde.querySelector(".kaynak-serit");
    const genislik = ilkSerit ? ilkSerit.getBoundingClientRect().width : Math.max(300, kapsayici.clientWidth - SOL_GENISLIK - 40);

    satirlar.forEach(({ serit }, i) => {
      serit.style.backgroundSize = `${(genislik / TOPLAM_DK) * 15}px 100%`;
    });

    // 2. geçiş: gerçek genişlikle rezervasyon/bakım/hazırlık/şimdi çizgisini çiz
    satirlar.forEach(({ k, serit }) => icerigiCiz(k, serit, genislik));
    simdiyiGuncelle();

    kurEtkilesim(genislik);
  }

  // Isı şeridi: her tür için iki saatlik bantların doluluğu ve bant çarpanı.
  // Değerler modülden (`doluluk_seridi`) gelir; burada yalnızca renklendirilir.
  function dolulukSeridiCiz() {
    if (!doluluk || !doluluk.turler || !doluluk.turler.length) return;
    const ds = el("div", null, govde);
    ds.id = "doluluk-seridi";
    doluluk.turler.forEach((t) => {
      const satir = el("div", "ds-satir", ds);
      const etiket = el("div", "ds-etiket", satir);
      etiket.textContent = t.tur;
      const alt = el("span", "ds-alt", etiket);
      alt.textContent = ` · ${t.kaynak_sayisi} kaynak`;
      const bantlar = el("div", "ds-bantlar", satir);
      t.bantlar.forEach((b) => {
        const h = el("div", `ds-hucre seviye-${b.seviye}${b.pik ? " pik" : ""}`, bantlar);
        h.textContent = b.dolu_dk ? `%${b.doluluk_yuzde} · ×${b.bant_carpan}` : "";
        h.title = `${t.tur} ${b.bant}\n${b.dolu_dk}/${b.kapasite_dk} dk dolu (%${b.doluluk_yuzde}) → bant çarpanı ×${b.bant_carpan}` +
          (b.pik ? `\nPik saat: enerji yoğun türde ×${b.pik_carpan}` : "");
      });
    });
  }

  function maxLane(rezervasyonlar) {
    return 1 + Math.max(0, ...rezervasyonlar.map((r) => r.alt_satir), 0);
  }

  function iskeletOlustur(k) {
    const satir = el("div", "kaynak-satir", govde);
    satir.dataset.kaynak = k.kaynak;

    const etiket = el("div", "kaynak-etiket", satir);
    const id = el("div", "kaynak-id", etiket); id.textContent = k.kaynak;
    const ad = el("div", "kaynak-ad", etiket); ad.textContent = `${k.ad || ""} · ${k.tur}`;

    const lanes = maxLane(k.rezervasyonlar || []);
    const yukseklik = lanes * LANE_YUKSEKLIK + 10;

    const serit = el("div", "kaynak-serit grid-15", satir);
    serit.style.height = yukseklik + "px";
    return { k, serit };
  }

  function icerigiCiz(k, serit, genislik) {
    (k.bakimlar || []).forEach((b) => {
      const b1 = zamanDk(b.baslangic, gunIso), b2 = zamanDk(b.bitis, gunIso);
      const bas = Math.max(0, b1 === null ? 0 : b1), bit = Math.min(TOPLAM_DK, b2 === null ? TOPLAM_DK : b2);
      if (bit <= bas) return;
      const x1 = dkDenX(bas, genislik), x2 = dkDenX(bit, genislik);
      const kutu = el("div", "bakim-kutu hatch", serit);
      kutu.style.cssText = `left:${x1 - SOL_GENISLIK}px; width:${x2 - x1}px;`;
      kutu.title = `Bakım ${b.baslangic.slice(11)}–${b.bitis.slice(11)}`;
    });

    (k.hazirlik_seritleri || []).forEach((hs) => {
      const b1 = zamanDk(hs.baslangic, gunIso), b2 = zamanDk(hs.bitis, gunIso);
      if (b1 === null || b2 === null) return;
      const x1 = dkDenX(Math.max(0, b1), genislik), x2 = dkDenX(Math.min(TOPLAM_DK, b2), genislik);
      const serit2 = el("div", "hazirlik-serit hatch-prep", serit);
      serit2.style.cssText = `left:${x1 - SOL_GENISLIK}px; width:${Math.max(2, x2 - x1)}px;`;
      serit2.title = "Hazırlık";
    });

    (k.rezervasyonlar || []).forEach((r) => cizRezervasyon(r, serit, genislik));
    (k.bekleme_kayitlari || []).forEach((bk) => cizBekleme(bk, serit, genislik));
  }

  // Yalnızca "şimdi" çizgisini taşır; oynatma modunda her karede çağrılır.
  function simdiyiGuncelle(yeniSimdi) {
    if (yeniSimdi !== undefined) simdiIso = yeniSimdi;
    if (!govde) return;
    const seritler = [...govde.querySelectorAll(".kaynak-serit")];
    let dk = null;
    if (simdiIso && seritler.length) {
      const [simdiTarih, simdiSaat] = simdiIso.split("T");
      if (gunIso === simdiTarih) {
        const [h, m] = simdiSaat.split(":").map(Number);
        const aday = (h - SAAT_BAS) * 60 + m;
        if (aday >= 0 && aday <= TOPLAM_DK) dk = aday;
      }
    }
    if (dk === null) {
      govde.querySelectorAll(".simdi-cizgi").forEach((c) => c.remove());
      return;
    }
    const genislik = seritler[0].getBoundingClientRect().width;
    const sol = dkDenX(dk, genislik) - SOL_GENISLIK + "px";
    seritler.forEach((serit) => {
      const cizgi = serit.querySelector(".simdi-cizgi") || el("div", "simdi-cizgi", serit);
      cizgi.style.left = sol;
    });
  }

  function cizRezervasyon(r, serit, genislik) {
    const b1 = Math.max(0, zamanDk(r.baslangic, gunIso) ?? 0);
    const b2 = Math.min(TOPLAM_DK, zamanDk(r.bitis, gunIso) ?? TOPLAM_DK);
    const x1 = dkDenX(b1, genislik), x2 = dkDenX(b2, genislik);

    const kutu = el("div", `rez-kutu durum-${r.durum}`, serit);
    kutu.style.cssText = `left:${x1 - SOL_GENISLIK}px; width:${Math.max(4, x2 - x1)}px; top:${5 + r.alt_satir * LANE_YUKSEKLIK}px;`;
    if (sadeceKullanici && r.kullanici !== sadeceKullanici) kutu.style.opacity = "0.25";

    const satir1 = el("div", "r1", kutu);
    satir1.textContent = `${r.id} · ${r.kullanici}${r.paket ? " · " + r.paket : ""}`;
    const satir2 = el("div", "r2", kutu);
    satir2.textContent = `${r.baslangic.slice(11)}–${r.bitis.slice(11)} · ${r.ucret} KP`;
    if (r.paket) el("div", "paket-cizgi", kutu);

    kutu.addEventListener("click", (ev) => { ev.stopPropagation(); onRezTikla(r.id, ev.clientX, ev.clientY); });
    kutu.addEventListener("mouseenter", (ev) => Tooltip.goster(ev.clientX, ev.clientY, `${r.id} · ${r.kullanici}\n${r.baslangic.slice(11)}–${r.bitis.slice(11)} · ${r.ucret} KP · ${r.durum}`));
    kutu.addEventListener("mousemove", (ev) => Tooltip.konumla(ev.clientX, ev.clientY));
    kutu.addEventListener("mouseleave", () => Tooltip.gizle());
  }

  function cizBekleme(bk, serit, genislik) {
    const b1 = Math.max(0, zamanDk(bk.baslangic, gunIso) ?? 0);
    const b2 = Math.min(TOPLAM_DK, zamanDk(bk.bitis, gunIso) ?? TOPLAM_DK);
    const x1 = dkDenX(b1, genislik), x2 = dkDenX(b2, genislik);
    const kutu = el("div", "bekleme-kutu", serit);
    kutu.style.cssText = `left:${x1 - SOL_GENISLIK}px; width:${Math.max(4, x2 - x1)}px;`;
    if (x2 - x1 > 50) kutu.textContent = `${bk.id} · sıra ${bk.sira}`;
  }

  function kurEtkilesim(genislik) {
    let onizlemeEl = null;

    function konumBul(serit, clientX) {
      const r = serit.getBoundingClientRect();
      let dk = ((clientX - r.left) / r.width) * TOPLAM_DK;
      return Math.max(0, Math.min(TOPLAM_DK, dk));
    }

    govde.querySelectorAll(".kaynak-serit").forEach((serit) => {
      const kaynakId = serit.closest(".kaynak-satir").dataset.kaynak;

      serit.addEventListener("pointerdown", (ev) => {
        if (ev.target.closest(".rez-kutu")) return;
        const dk = konumBul(serit, ev.clientX);
        const dkYuvarlanmis = Math.round(dk / 15) * 15;
        surukleme = { kaynakId, serit, dk1: dkYuvarlanmis, dk2: dkYuvarlanmis + 15 };
        serit.setPointerCapture(ev.pointerId);
      });

      serit.addEventListener("pointermove", (ev) => {
        if (!surukleme || surukleme.serit !== serit) return;
        const dk = konumBul(serit, ev.clientX);
        let dkYuvarlanmis = Math.round(dk / 15) * 15;
        dkYuvarlanmis = Math.max(dkYuvarlanmis, surukleme.dk1 + 15);
        surukleme.dk2 = dkYuvarlanmis;
        if (!onizlemeEl) onizlemeEl = el("div", "surukleme-onizleme", serit);
        const x1 = dkDenX(Math.min(surukleme.dk1, surukleme.dk2), genislik);
        const x2 = dkDenX(Math.max(surukleme.dk1, surukleme.dk2), genislik);
        onizlemeEl.style.cssText = `left:${x1 - SOL_GENISLIK}px; width:${x2 - x1}px;`;
      });

      function bitir() {
        if (!surukleme || surukleme.serit !== serit) return;
        const { kaynakId: kid, dk1, dk2 } = surukleme;
        surukleme = null;
        if (onizlemeEl) { onizlemeEl.remove(); onizlemeEl = null; }
        const dkBas = Math.min(dk1, dk2), dkBit = Math.max(dk1, dk2 === dk1 ? dk1 + 15 : dk2);
        const taban = new Date(gunIso + "T00:00:00");
        const b = new Date(taban.getTime() + (SAAT_BAS * 60 + dkBas) * 60000);
        const e = new Date(taban.getTime() + (SAAT_BAS * 60 + dkBit) * 60000);
        onBosAlanSec(kid, isoYerel(b), isoYerel(e));
      }
      serit.addEventListener("pointerup", bitir);
      serit.addEventListener("pointerleave", (ev) => { if (ev.buttons === 0) bitir(); });
    });
  }

  function isoYerel(d) {
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
  }

  const Tooltip = {
    goster(x, y, metin) {
      const t = document.getElementById("tooltip");
      t.textContent = metin;
      t.style.display = "block";
      this.konumla(x, y);
    },
    konumla(x, y) {
      const t = document.getElementById("tooltip");
      t.style.left = x + 14 + "px";
      t.style.top = y + 14 + "px";
    },
    gizle() { document.getElementById("tooltip").style.display = "none"; },
  };

  return { kur, goster, sadeceFiltreyiGuncelle, cizYeniden, simdiyiGuncelle };
})();
