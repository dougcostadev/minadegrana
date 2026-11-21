(function () {
  "use strict";
  var FUSO = "America/Sao_Paulo";
  var REDES = [
    { k: "yt", nome: "YouTube Shorts", campos: function (r) { return [["Título", r.youtube.titulo], ["Descrição", r.youtube.descricao], ["Tags", r.youtube.tags]]; } },
    { k: "tt", nome: "TikTok", campos: function (r) { return [["Legenda", r.tiktok]]; } },
    { k: "ig", nome: "Instagram Reels", campos: function (r) { return [["Legenda", r.instagram]]; } }
  ];
  var $ = function (id) { return document.getElementById(id); };
  var aviso = $("aviso"), secAgenda = $("sec-agenda"), agenda = $("agenda"), atuais = $("cortes"),
      antigosBox = $("anteriores"), antigos = $("cortes-antigos"), nAntigos = $("n-anteriores");
  var db = null, assinatura = null, caixas = {}, contadores = {}, gravando = {};

  function el(tag, props, filhos) {
    var n = document.createElement(tag), k;
    for (k in (props || {})) {
      if (k === "class") n.className = props[k];
      else if (k === "text") n.textContent = props[k];
      else n.setAttribute(k, props[k]);
    }
    (filhos || []).forEach(function (f) { if (f) n.appendChild(f); });
    return n;
  }
  function fmt(opcoes) {
    opcoes.timeZone = FUSO;
    return new Intl.DateTimeFormat("pt-BR", opcoes);
  }
  function diaDe(d) { // AAAA-MM-DD no fuso de Brasília
    var o = {};
    fmt({ year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(d)
      .forEach(function (x) { o[x.type] = x.value; });
    return o.year + "-" + o.month + "-" + o.day;
  }
  function rotuloDia(dia, hoje, amanha) {
    var txt = fmt({ weekday: "long", day: "2-digit", month: "2-digit" }).format(new Date(dia + "T12:00:00-03:00"));
    if (dia === hoje) return "Hoje, " + txt;
    if (dia === amanha) return "Amanhã, " + txt;
    return txt.charAt(0).toUpperCase() + txt.slice(1);
  }
  function hora(iso) { return fmt({ hour: "2-digit", minute: "2-digit" }).format(new Date(iso)); }
  function avisar(texto) { aviso.textContent = texto; aviso.hidden = !texto; }

  function copiar(botao, alvo) {
    var feito = function (texto) {
      botao.textContent = texto;
      botao.classList.add("ok");
      setTimeout(function () { botao.textContent = "Copiar"; botao.classList.remove("ok"); }, 1600);
    };
    var reserva = function () {
      var faixa = document.createRange();
      faixa.selectNodeContents(alvo);
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(faixa);
      feito("Selecionado: copie");
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(alvo.textContent).then(function () { feito("Copiado"); }, reserva);
    } else {
      reserva();
    }
  }

  function baixar(botao, c) {
    var voltar = function (texto) {
      botao.textContent = texto;
      botao.disabled = false;
      setTimeout(function () { botao.textContent = "Baixar vídeo"; }, 3000);
    };
    if (!window.claude || !window.claude.use) { voltar("Use Abrir vídeo"); return; }
    botao.disabled = true;
    botao.textContent = "Preparando…";
    window.claude.use("downloads").then(function (dl) {
      if (!dl) throw { code: "unavailable" };
      return fetch("/_blob/" + c.asset).then(function (r) {
        if (!r.ok) throw { code: "fetch" };
        return r.blob();
      }).then(function (blob) { return dl.save({ filename: c.arquivo, data: blob }); });
    }).then(function () { voltar("Salvo"); }, function (e) {
      voltar(e && e.code === "declined" ? "Cancelado" : "Não deu: use Abrir vídeo");
    });
  }

  function contar(id) {
    var n = REDES.filter(function (r) { return caixas[id][r.k].checked; }).length;
    (contadores[id] || []).forEach(function (s) {
      s.textContent = n === 3 ? "postado" : n + "/3";
      s.classList.toggle("ok", n === 3);
    });
  }

  function marcar(id, rede, caixa) {
    caixa.closest(".rede").classList.toggle("pronta", caixa.checked);
    contar(id);
    if (!db) return;
    var valor = caixa.checked, patch = { postado: {} };
    patch.postado[rede] = valor;
    // uma gravação por vez em cada documento
    gravando[id] = (gravando[id] || Promise.resolve()).then(function () {
      return db.doc("cortes/" + id).update(patch);
    }).then(null, function () {
      caixa.checked = !valor;
      caixa.closest(".rede").classList.toggle("pronta", caixa.checked);
      contar(id);
      avisar("Não consegui salvar a marcação. Tente de novo em instantes.");
    });
  }

  function cartao(id, c, n) {
    caixas[id] = {};
    var redes = el("div", { class: "redes" });
    REDES.forEach(function (rede) {
      var caixa = el("input", { type: "checkbox", id: "p-" + id + "-" + rede.k });
      caixa.checked = !!(c.postado && c.postado[rede.k]);
      caixa.addEventListener("change", function () { marcar(id, rede.k, caixa); });
      caixas[id][rede.k] = caixa;
      var sec = el("section", { class: "rede rede-" + rede.k + (caixa.checked ? " pronta" : "") }, [
        el("header", {}, [el("h4", { text: rede.nome }),
          el("label", { class: "feito" }, [caixa, document.createTextNode(" postado")])])
      ]);
      rede.campos(c.redes).forEach(function (par, i) {
        var pre = el("pre", { class: "texto", tabindex: "0", id: "t-" + id + "-" + rede.k + "-" + i, text: par[1] });
        var botao = el("button", { type: "button", class: "copiar", text: "Copiar" });
        botao.addEventListener("click", function () { copiar(botao, pre); });
        sec.appendChild(el("div", { class: "campo" }, [
          el("div", { class: "campo-topo" }, [el("span", { class: "rotulo", text: par[0] }), botao]), pre]));
      });
      redes.appendChild(sec);
    });

    var midia, acoes;
    if (c.asset) {
      midia = el("video", { class: "mini", controls: "", preload: "none", playsinline: "", src: "/_blob/" + c.asset });
      if (c.capa) midia.setAttribute("poster", "/_blob/" + c.capa);
      var botao = el("button", { type: "button", class: "baixar", text: "Baixar vídeo" });
      botao.addEventListener("click", function () { baixar(botao, c); });
      acoes = el("div", { class: "acoes" }, [botao,
        el("a", { class: "abrir", href: "/_blob/" + c.asset, target: "_blank", rel: "noopener", text: "Abrir vídeo" })]);
    } else {
      midia = c.capa ? el("img", { class: "mini", src: "/_blob/" + c.capa, alt: "Quadro do corte", width: "144", height: "256" })
        : el("div", { class: "mini" });
      acoes = el("p", { class: "sem-video", text: "Vídeo não anexado: use o arquivo enviado na conversa." });
    }
    var item = function (rotulo, valor, classe) {
      return el("div", {}, [el("dt", { text: rotulo }), el("dd", { text: valor, class: classe || "" })]);
    };
    var lista = el("dl", {}, [item("Streamer", c.nome || c.canal || ""), item("Postar", c.postar_em_texto || hora(c.postar_em)),
      item("Arquivo", c.arquivo || "", "arquivo")]);
    if (c.views) lista.appendChild(item("Clipe original", Number(c.views).toLocaleString("pt-BR") + " views"));
    return el("article", { class: "corte", id: "c-" + id }, [
      el("div", { class: "cabeca" }, [midia, el("div", { class: "resumo" }, [
        el("p", { class: "ordem", text: hora(c.postar_em) + (n ? " · corte " + n : "") }),
        el("h3", { text: c.gancho || c.titulo_base || "" }), lista, acoes])]),
      redes]);
  }

  function montar(docs) {
    var hoje = diaDe(new Date()), amanha = diaDe(new Date(Date.now() + 864e5));
    caixas = {}; contadores = {};
    atuais.textContent = ""; antigos.textContent = ""; agenda.textContent = "";
    var grupos = {}, ordemDias = [];
    docs.forEach(function (x) {
      x.dia = diaDe(new Date(x.c.postar_em));
      if (!grupos[x.dia]) { grupos[x.dia] = []; ordemDias.push(x.dia); }
      grupos[x.dia].push(x);
    });
    var futuros = ordemDias.filter(function (d) { return d >= hoje; }).sort();
    var passados = ordemDias.filter(function (d) { return d < hoje; }).sort().reverse();
    var secao = function (dia) {
      var s = el("section", { class: "dia" }, [el("h2", { text: rotuloDia(dia, hoje, amanha) })]);
      grupos[dia].forEach(function (x, i) { s.appendChild(cartao(x.id, x.c, i + 1)); });
      return s;
    };
    futuros.forEach(function (dia) {
      atuais.appendChild(secao(dia));
      grupos[dia].forEach(function (x) {
        var status = el("span", { class: "status" });
        (contadores[x.id] = contadores[x.id] || []).push(status);
        var quando = (dia === hoje ? "hoje" : dia === amanha ? "amanhã" : dia.slice(8) + "/" + dia.slice(5, 7)) + " " + hora(x.c.postar_em);
        agenda.appendChild(el("li", {}, [el("a", { href: "#c-" + x.id }, [
          el("span", { class: "quando", text: quando }),
          el("span", { class: "oque", text: x.c.gancho || x.c.titulo_base || "" }),
          el("span", { class: "quem", text: x.c.nome || "" }), status])]));
      });
    });
    passados.forEach(function (dia) { antigos.appendChild(secao(dia)); });
    Object.keys(caixas).forEach(contar);
    secAgenda.hidden = !futuros.length;
    antigosBox.hidden = !passados.length;
    nAntigos.textContent = passados.length ? "(" + docs.filter(function (x) { return x.dia < hoje; }).length + ")" : "";
    if (!docs.length) avisar("Nenhum corte na pauta ainda. Os cortes de cada rodada aparecem aqui, com o vídeo para baixar e os textos de cada rede.");
    else if (!futuros.length) avisar("Nada agendado de hoje em diante. A próxima rodada traz os cortes do dia.");
    else avisar("");
  }

  function receber(snap) {
    clearTimeout(relogio);
    var docs = snap.docs.filter(function (d) { return d.exists; })
      .map(function (d) { return { id: d.id, c: d.data() }; })
      .filter(function (x) { return x.c && x.c.postar_em && x.c.redes; })
      .sort(function (a, b) { return a.c.postar_em < b.c.postar_em ? -1 : a.c.postar_em > b.c.postar_em ? 1 : 0; });
    var nova = diaDe(new Date()) + ";" + docs.map(function (x) { return x.id + "|" + x.c.postar_em + "|" + (x.c.asset || ""); }).join(",");
    if (nova !== assinatura) { assinatura = nova; montar(docs); return; }
    // só mudaram as marcações: atualiza as caixas sem recriar a página (não interrompe um vídeo tocando)
    docs.forEach(function (x) {
      REDES.forEach(function (r) {
        var caixa = caixas[x.id] && caixas[x.id][r.k];
        if (!caixa || gravando[x.id + r.k]) return;
        caixa.checked = !!(x.c.postado && x.c.postado[r.k]);
        caixa.closest(".rede").classList.toggle("pronta", caixa.checked);
      });
      contar(x.id);
    });
  }

  var relogio = setTimeout(function () {
    avisar("Ainda não consegui carregar os cortes. A página continua tentando.");
  }, 10000);
  if (!window.claude || !window.claude.use) {
    clearTimeout(relogio);
    avisar("Os cortes aparecem quando esta página é aberta pelo link do Claude.");
    return;
  }
  window.claude.use("db").then(function (base) {
    if (!base) {
      clearTimeout(relogio);
      avisar("Não foi possível abrir o banco de cortes nesta visualização. Abra a página pelo link do Claude, com a sua conta.");
      return;
    }
    db = base;
    db.collection("cortes").limit(300).onSnapshot(receber, function (e) {
      clearTimeout(relogio);
      avisar("Não foi possível ler os cortes agora (" + ((e && e.code) || "erro") + "). Recarregue a página em instantes.");
    });
  });
})();
