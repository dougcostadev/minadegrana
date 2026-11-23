(function () {
  "use strict";
  var REDES = [
    { k: "yt", curto: "YT", nome: "YouTube", campos: function (r) { return [["Título", r.youtube.titulo], ["Descrição", r.youtube.descricao], ["Tags", r.youtube.tags]]; } },
    { k: "tt", curto: "TT", nome: "TikTok", campos: function (r) { return [["Legenda", r.tiktok]]; } },
    { k: "ig", curto: "IG", nome: "Instagram", campos: function (r) { return [["Legenda", r.instagram]]; } }
  ];
  var FAIXAS = ["livres", "feitos", "descartados"], ORDENS = ["novos", "vistos", "curtos"];
  var $ = function (id) { return document.getElementById(id); };
  var aviso = $("aviso"), controles = $("controles"), explica = $("explica"), grade = $("grade"),
      resumo = $("resumo"), busca = $("busca"), selStreamer = $("streamer"), selOrdem = $("ordem");
  var db = null, docs = [], aberto = null, desenhado = null, gravando = {};
  var ver = { rede: "todas", faixa: "livres", ordem: "novos", streamer: "", busca: "" };
  try {
    var salvo = JSON.parse(localStorage.getItem("biblioteca-ver") || "{}");
    if (salvo.rede === "todas" || REDES.some(function (r) { return r.k === salvo.rede; })) ver.rede = salvo.rede;
    if (FAIXAS.indexOf(salvo.faixa) >= 0) ver.faixa = salvo.faixa;
    if (ORDENS.indexOf(salvo.ordem) >= 0) ver.ordem = salvo.ordem;
  } catch (e) {}
  selOrdem.value = ver.ordem;

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
  function avisar(texto) { aviso.textContent = texto; aviso.hidden = !texto; }
  function lembrar() {
    try { localStorage.setItem("biblioteca-ver", JSON.stringify({ rede: ver.rede, faixa: ver.faixa, ordem: ver.ordem })); } catch (e) {}
  }
  function semAcento(t) { return (t || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, ""); }

  function falta(x, rede) {
    var p = x.c.postado || {};
    return rede === "todas" ? !(p.yt && p.tt && p.ig) : !p[rede];
  }
  function faixaDe(x, rede) {
    if (x.c.descartado) return "descartados";
    return falta(x, rede) ? "livres" : "feitos";
  }
  function detalhe(c) {
    var partes = [c.nome || c.canal || ""];
    if (c.duracao_s) partes.push(c.duracao_s + "s");
    if (c.views) partes.push(Number(c.views).toLocaleString("pt-BR") + " views na live");
    return partes.join(" · ");
  }

  function gravar(x, patch, desfazer) {
    if (!db) return;
    gravando[x.id] = (gravando[x.id] || Promise.resolve()).then(function () {
      return db.doc("cortes/" + x.id).update(patch);   // uma gravação por vez em cada documento
    }).then(null, function () {
      desfazer();
      desenhar(true);
      avisar("Não consegui salvar a alteração. Tente de novo em instantes.");
    });
  }
  function marcar(x, rede, valor) {
    x.c.postado = x.c.postado || {};
    var antes = !!x.c.postado[rede], patch = { postado: {} };
    x.c.postado[rede] = valor;
    patch.postado[rede] = valor;
    desenhar(true);
    gravar(x, patch, function () { x.c.postado[rede] = antes; });
  }
  function descartar(x, valor) {
    var antes = !!x.c.descartado;
    x.c.descartado = valor;
    desenhar(true);
    gravar(x, { descartado: valor }, function () { x.c.descartado = antes; });
  }

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

  function campos(x, rede) {
    var caixa = el("div", { class: "campos" });
    rede.campos(x.c.redes).forEach(function (par, i) {
      var pre = el("pre", { class: "texto", tabindex: "0", id: "t-" + x.id + "-" + rede.k + "-" + i, text: par[1] });
      var botao = el("button", { type: "button", class: "copiar", text: "Copiar" });
      botao.addEventListener("click", function () { copiar(botao, pre); });
      caixa.appendChild(el("div", { class: "campo" }, [
        el("div", { class: "campo-topo" }, [el("span", { class: "rotulo", text: par[0] }), botao]), pre]));
    });
    return caixa;
  }
  function botaoRede(x, r) {
    var posto = !!(x.c.postado && x.c.postado[r.k]);
    var b = el("button", { type: "button", class: "marca-rede marca-" + r.k + (posto ? " on" : ""), "aria-pressed": posto ? "true" : "false",
      text: posto ? "Postado no " + r.nome + " (desfazer)" : "Marcar como postado no " + r.nome });
    b.addEventListener("click", function () { marcar(x, r.k, !posto); });
    return b;
  }

  function painel(x) {
    var c = x.c, corpo = el("section", { class: "painel", id: "painel", "aria-label": "Clipe selecionado" });
    var lado = el("div", { class: "painel-lado" }, [
      el("h2", { text: c.gancho || c.titulo_base || "" }),
      el("p", { class: "detalhe", text: detalhe(c) }),
      c.aviso ? el("p", { class: "alerta", text: c.aviso }) : null]);
    if (c.asset) {
      var baixa = el("button", { type: "button", class: "baixar", text: "Baixar vídeo" });
      baixa.addEventListener("click", function () { baixar(baixa, c); });
      lado.appendChild(el("div", { class: "acoes" }, [baixa,
        el("a", { class: "abrir", href: "/_blob/" + c.asset, target: "_blank", rel: "noopener", text: "Abrir vídeo" })]));
    } else {
      lado.appendChild(el("p", { class: "sem-video", text: c.video_removido ? "Vídeo apagado depois de postado nas três redes, para liberar espaço. Os textos continuam aqui." : "Este clipe não tem vídeo anexado." }));
    }
    var some = el("button", { type: "button", class: "leve", text: c.descartado ? "Restaurar clipe" : "Descartar clipe" });
    some.addEventListener("click", function () { descartar(x, !c.descartado); });
    var fecha = el("button", { type: "button", class: "leve", text: "Fechar" });
    fecha.addEventListener("click", function () { aberto = null; desenhar(true); });
    lado.appendChild(el("div", { class: "acoes" }, [some, fecha]));

    var video = null;
    if (c.asset) {
      video = el("video", { class: "previa", controls: "", preload: "none", playsinline: "", src: "/_blob/" + c.asset });
      if (c.capa) video.setAttribute("poster", "/_blob/" + c.capa);
    }
    corpo.appendChild(el("div", { class: "painel-topo" }, [video, lado]));

    var redes = el("div", { class: "redes" });
    REDES.filter(function (r) { return ver.rede === "todas" || r.k === ver.rede; }).forEach(function (r) {
      redes.appendChild(el("section", { class: "rede rede-" + r.k }, [
        el("h3", { text: r.nome }), campos(x, r), botaoRede(x, r)]));
    });
    corpo.appendChild(redes);
    return corpo;
  }

  function ficha(x) {
    var c = x.c, p = c.postado || {};
    var selos = el("span", { class: "selos" });
    REDES.forEach(function (r) {
      selos.appendChild(el("span", { class: "selo selo-" + r.k + (p[r.k] ? " on" : ""), text: r.curto,
        title: r.nome + (p[r.k] ? ": postado" : ": não postado") }));
    });
    var capa = c.capa ? el("img", { class: "capa", src: "/_blob/" + c.capa, alt: "", loading: "lazy" }) : el("span", { class: "capa" });
    var b = el("button", { type: "button", class: "ficha" + (aberto === x.id ? " aberta" : ""), id: "c-" + x.id,
      "aria-expanded": aberto === x.id ? "true" : "false" }, [
      capa,
      el("span", { class: "ficha-gancho", text: c.gancho || c.titulo_base || "" }),
      el("span", { class: "ficha-nome", text: (c.nome || "") + (c.duracao_s ? " · " + c.duracao_s + "s" : "") }),
      selos]);
    b.addEventListener("click", function () {
      aberto = aberto === x.id ? null : x.id;
      desenhar(true);
      var alvo = document.getElementById(aberto ? "painel" : "c-" + x.id);
      if (alvo && alvo.scrollIntoView) alvo.scrollIntoView({ block: "nearest" });
    });
    return b;
  }

  var TEXTO = {
    livres: ["Nenhum clipe disponível com esse filtro.", "ainda não postados"],
    feitos: ["Nenhum clipe postado com esse filtro.", "já postados"],
    descartados: ["Nenhum clipe descartado.", "descartados (dá para restaurar)"]
  };

  function desenhar(forcar) {
    var chave = JSON.stringify([ver, aberto, docs.map(function (x) {
      return [x.id, x.c.asset, x.c.postado, x.c.descartado];
    })]);
    if (!forcar && chave === desenhado) return;
    desenhado = chave;

    // filtro de streamer acompanha os clipes que existem
    var nomes = {};
    docs.forEach(function (x) { if (x.c.nome) nomes[x.c.nome] = (nomes[x.c.nome] || 0) + 1; });
    var lista = Object.keys(nomes).sort(function (a, b) { return a.localeCompare(b, "pt-BR"); });
    if (selStreamer.options.length !== lista.length + 1) {
      selStreamer.textContent = "";
      selStreamer.appendChild(el("option", { value: "", text: "Todos" }));
      lista.forEach(function (n) { selStreamer.appendChild(el("option", { value: n, text: n + " (" + nomes[n] + ")" })); });
      selStreamer.value = ver.streamer;
    }

    var ativos = docs.filter(function (x) { return !x.c.descartado; });
    REDES.forEach(function (r) {
      var n = ativos.filter(function (x) { return falta(x, r.k); }).length;
      $("n-" + r.k).textContent = n ? String(n) : "";
    });
    var termo = semAcento(ver.busca.trim());
    var filtrados = docs.filter(function (x) {
      if (ver.streamer && x.c.nome !== ver.streamer) return false;
      return !termo || semAcento((x.c.gancho || "") + " " + (x.c.titulo_base || "") + " " + (x.c.nome || "")).indexOf(termo) >= 0;
    });
    var porFaixa = { livres: [], feitos: [], descartados: [] };
    filtrados.forEach(function (x) { porFaixa[faixaDe(x, ver.rede)].push(x); });
    FAIXAS.forEach(function (f) { $("n-" + f).textContent = porFaixa[f].length ? String(porFaixa[f].length) : ""; });
    controles.querySelectorAll(".seg").forEach(function (b) {
      var ativo = b.dataset.rede ? b.dataset.rede === ver.rede : b.dataset.faixa === ver.faixa;
      b.classList.toggle("ativo", ativo);
      b.setAttribute("aria-pressed", ativo ? "true" : "false");
    });

    var itens = porFaixa[ver.faixa].slice().sort(function (a, b) {
      if (ver.ordem === "vistos") return (b.c.views || 0) - (a.c.views || 0);
      if (ver.ordem === "curtos") return (a.c.duracao_s || 999) - (b.c.duracao_s || 999);
      return (b.c.criado_em || "") < (a.c.criado_em || "") ? -1 : (b.c.criado_em || "") > (a.c.criado_em || "") ? 1 : 0;
    });
    if (aberto && !itens.some(function (x) { return x.id === aberto; })) aberto = null;
    grade.textContent = "";
    itens.forEach(function (x) {
      grade.appendChild(ficha(x));
      if (aberto === x.id) grade.appendChild(painel(x));
    });

    var todosPostados = ativos.filter(function (x) { return !falta(x, "todas"); }).length;
    resumo.textContent = docs.length
      ? ativos.length + " clipes prontos · " + (ativos.length - todosPostados) + " com rede faltando · " + todosPostados + " postados nas três redes"
      : "";
    var onde = ver.rede === "todas" ? "" : " no " + REDES.filter(function (r) { return r.k === ver.rede; })[0].nome;
    explica.hidden = false;
    explica.textContent = itens.length
      ? itens.length + (itens.length === 1 ? " clipe " : " clipes ") + TEXTO[ver.faixa][1] + onde + ". Toque num clipe para ver o vídeo e os textos."
      : TEXTO[ver.faixa][0];
    controles.hidden = !docs.length;
    if (!docs.length) {
      explica.hidden = true;
      avisar("A biblioteca está vazia. Os clipes de cada rodada aparecem aqui, com o vídeo para baixar e os textos de cada rede.");
    } else {
      avisar("");
    }
  }

  controles.addEventListener("click", function (ev) {
    var b = ev.target.closest(".seg");
    if (!b) return;
    if (b.dataset.rede) ver.rede = b.dataset.rede;
    if (b.dataset.faixa) ver.faixa = b.dataset.faixa;
    lembrar();
    desenhar(true);
  });
  selOrdem.addEventListener("change", function () { ver.ordem = selOrdem.value; lembrar(); desenhar(true); });
  selStreamer.addEventListener("change", function () { ver.streamer = selStreamer.value; desenhar(true); });
  var espera = null;
  busca.addEventListener("input", function () {
    clearTimeout(espera);
    espera = setTimeout(function () { ver.busca = busca.value; desenhar(true); }, 150);
  });

  function receber(snap) {
    clearTimeout(relogio);
    docs = snap.docs.filter(function (d) { return d.exists; })
      .map(function (d) { return { id: d.id, c: JSON.parse(JSON.stringify(d.data())) }; })
      .filter(function (x) { return x.c && x.c.redes; });
    desenhar(false);
  }

  var relogio = setTimeout(function () {
    avisar("Ainda não consegui carregar os clipes. A página continua tentando.");
  }, 10000);
  if (!window.claude || !window.claude.use) {
    clearTimeout(relogio);
    avisar("Os clipes aparecem quando esta página é aberta pelo link do Claude.");
    return;
  }
  window.claude.use("db").then(function (base) {
    if (!base) {
      clearTimeout(relogio);
      avisar("Não foi possível abrir a biblioteca nesta visualização. Abra a página pelo link do Claude, com a sua conta.");
      return;
    }
    db = base;
    db.collection("cortes").limit(1000).onSnapshot(receber, function (e) {
      clearTimeout(relogio);
      avisar("Não foi possível ler os clipes agora (" + ((e && e.code) || "erro") + "). Recarregue a página em instantes.");
    });
  });
})();
