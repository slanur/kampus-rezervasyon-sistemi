/* Python <-> JS köprüsü. QWebChannel'ı Promise tabanlı küçük bir API'ye sarar. */

window.K = (function () {
  let kopru = null;
  let hazirCozucu = null;
  const hazir = new Promise((cozucu) => { hazirCozucu = cozucu; });

  const durumDegistiDinleyiciler = [];
  const dosyaDegistiDinleyiciler = [];
  const komutOncesiKancalar = [];

  new QWebChannel(qt.webChannelTransport, function (kanal) {
    kopru = kanal.objects.kopru;
    kopru.durumDegisti.connect(() => durumDegistiDinleyiciler.forEach((f) => f()));
    kopru.dosyaDegisti.connect((ad) => dosyaDegistiDinleyiciler.forEach((f) => f(ad)));
    hazirCozucu();
  });

  function ayristir(ham) {
    const veri = JSON.parse(ham);
    if (veri.hata) throw new Error(veri.hata);
    return veri.sonuc;
  }

  return {
    hazir,
    onDurumDegisti(fn) { durumDegistiDinleyiciler.push(fn); },
    onDosyaDegisti(fn) { dosyaDegistiDinleyiciler.push(fn); },
    onKomutOncesi(fn) { komutOncesiKancalar.push(fn); },

    // secenekler.kancasiz: komut-öncesi kancaları atla (kancanın kendi çağrıları için)
    async cagir(yontem, args, secenekler) {
      await hazir;
      if (!(secenekler && secenekler.kancasiz)) {
        for (const kanca of komutOncesiKancalar) await kanca(yontem);
      }
      const ham = await new Promise((cozucu) => {
        kopru.cagir(JSON.stringify({ yontem, args: args || {} }), cozucu);
      });
      return ayristir(ham);
    },

    async dosyaSec() {
      await hazir;
      const ham = await new Promise((cozucu) => kopru.dosyaSec(cozucu));
      if (!ham) return null;
      return ayristir(ham);
    },

    async dosyaYukle(yol) {
      await hazir;
      const ham = await new Promise((cozucu) => kopru.dosyaYukle(yol, cozucu));
      return ayristir(ham);
    },

    async ilkDosya() {
      await hazir;
      return new Promise((cozucu) => kopru.ilkDosya(cozucu));
    },

    async gunluk() {
      await hazir;
      return new Promise((cozucu) => kopru.gunluk((ham) => cozucu(JSON.parse(ham))));
    },

    async kullaniciDetayi(id) {
      await hazir;
      const ham = await new Promise((cozucu) => kopru.kullaniciDetayi(id, cozucu));
      return ayristir(ham);
    },

    async yukluMu() {
      await hazir;
      return new Promise((cozucu) => kopru.yukluMu(cozucu));
    },

    async geriAlYapilabilir() {
      await hazir;
      return new Promise((cozucu) => kopru.geriAlYapilabilir(cozucu));
    },
  };
})();
