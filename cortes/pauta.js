(function () {
  "use strict";
  var FUSO = "America/Sao_Paulo";
  var REDES = [
    { k: "yt", curto: "YT", nome: "YouTube", campos: function (r) { return [["Título", r.youtube.titulo], ["Descrição", r.youtube.descricao], ["Tags", r.youtube.tags]]; } },
    { k: "tt", curto: "TT", nome: "TikTok", campos: function (r) { return [["Legenda", r.tiktok]]; } },
    { k: "ig", curto: "IG", nome: "Instagram", campos: function (r) { return [["Legenda", r.instagram]]; } }
  ];
  var FAIXAS = ["agora", "proximos", "feitos", "descartados"];
  var $ = function (id) { return document.getElementById(id); };
  var aviso = $("aviso"), controles = $("controles"), explica = $("explica"), lista = $("lista");
  var db = null, docs = [], abertos = {}, desenhado = null, gravando = {};
  var ver = { rede: "todas", faixa: "agora" };
  try {
    var salvo = JSON.parse(localStorage.getItem("pauta-ver") || "{}");
    if (salvo.rede === "todas" || REDES.some(function (r) { return r.k === salvo.rede; })) ver.rede = salvo.rede;
    if (FAIXAS.indexOf(salvo.faixa) >= 0) ver.faixa = salvo.faixa;
  } catch (e) {}

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
  function fmt(opcoes) { opcoes.timeZone = FUSO; return new Intl.DateTimeFormat("pt-BR", opcoes); }
  function diaDe(d) { // AAAA-MM-DD no fuso de Brasília
    var o = {};
    fmt({ year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(d)
      .forEach(function (x) { o[x.type] = x.value; });
    return o.year + "-" + o.month + "-" + o.day;
  }
  function hora(iso) { return fmt({ hour: "2-digit", minute: "2-digit" }).format(new Date(iso)); }
  function quando(x, hoje, amanha) {
    var h = hora(x.c.postar_em);
    if (x.dia === hoje) return "hoje " + h;
    if (x.dia === amanha) return "amanhã " + h;
    var sem = fmt({ weekday: "short" }).format(new Date(x.dia + "T12:00:00-03:00")).replace(".", "");
    return sem + " " + x.dia.slice(8) + "/" + x.dia.slice(5, 7) + " " + h;
  }
  function avisar(texto) { aviso.textContent = texto; aviso.hidden = !texto; }

  function pendente(x, rede) {
    var p = x.c.postado || {};
    return rede === "todas" ? !(p.yt && p.tt && p.ig) : !p[rede];
  }
  function faixaDe(x, rede, hoje) {
    if (x.c.descartado) return "descartados";
    if (!pendente(x, rede)) return "feitos";
    return x.dia <= hoje ? "agora" : "proximos";
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
  function midia(c) {
    if (!c.asset) return el("p", { class: "sem-video", text: "Vídeo não anexado: use o arquivo enviado na conversa." });
    var botao = el("button", { type: "button", class: "baixar", text: "Baixar vídeo" });
    botao.addEventListener("click", function () { baixar(botao, c); });
    return el("div", { class: "acoes" }, [botao,
      el("a", { class: "abrir", href: "/_blob/" + c.asset, target: "_blank", rel: "noopener", text: "Abrir vídeo" })]);
  }
  function capa(c, classe) {
    return c.capa ? el("img", { class: classe, src: "/_blob/" + c.capa, alt: "", loading: "lazy" }) : el("div", { class: classe });
  }
  function botaoDescartar(x) {
    var b = el("button", { type: "button", class: "leve", text: x.c.descartado ? "Restaurar corte" : "Descartar corte" });
    b.addEventListener("click", function () { descartar(x, !x.c.descartado); });
    return b;
  }

  function linha(x, hoje, amanha) {
    var c = x.c, p = c.postado || {}, atrasado = x.dia < hoje && !c.descartado && pendente(x, ver.rede);
    var chips = el("div", { class: "chips" });
    REDES.forEach(function (r) {
      var chip = el("button", { type: "button", class: "chip chip-" + r.k + (p[r.k] ? " on" : ""),
        "aria-pressed": p[r.k] ? "true" : "false",
        "aria-label": r.nome + (p[r.k] ? ": postado" : ": falta postar"), text: r.curto });
      chip.addEventListener("click", function (ev) { ev.stopPropagation(); marcar(x, r.k, !p[r.k]); });
      chips.appendChild(chip);
    });
    var topo = el("div", { class: "linha-topo" }, [
      capa(c, "mini"),
      el("div", { class: "linha-texto" }, [
        el("p", { class: "quando" + (atrasado ? " atrasado" : ""), text: quando(x, hoje, amanha) + (atrasado ? " · atrasado" : "") + " · " + (c.nome || "") }),
        el("p", { class: "gancho", text: c.gancho || c.titulo_base || "" })]),
      chips]);
    var art = el("article", { class: "corte", id: "c-" + x.id }, [topo]);
    var umaRede = ver.rede !== "todas";
    var aberto = umaRede ? ver.faixa !== "feitos" : !!abertos[x.id];

    if (!umaRede) {
      var alterna = el("button", { type: "button", class: "leve abre", "aria-expanded": aberto ? "true" : "false",
        text: aberto ? "Fechar" : "Abrir textos e vídeo" });
      alterna.addEventListener("click", function () { abertos[x.id] = !abertos[x.id]; desenhar(true); });
      art.appendChild(alterna);
    }
    if (!aberto) return art;

    var corpo = el("div", { class: "corpo" });
    if (c.aviso) corpo.appendChild(el("p", { class: "alerta", text: c.aviso }));
    if (umaRede) {
      var rede = REDES.filter(function (r) { return r.k === ver.rede; })[0];
      corpo.appendChild(midia(c));
      corpo.appendChild(campos(x, rede));
      var feito = el("button", { type: "button", class: "principal",
        text: p[rede.k] ? "Desmarcar: não postei no " + rede.nome : "Marquei: postei no " + rede.nome });
      feito.addEventListener("click", function () { marcar(x, rede.k, !p[rede.k]); });
      corpo.appendChild(el("div", { class: "rodape" }, [feito, botaoDescartar(x)]));
    } else {
      if (c.asset) {
        var video = el("video", { class: "previa", controls: "", preload: "none", playsinline: "", src: "/_blob/" + c.asset });
        if (c.capa) video.setAttribute("poster", "/_blob/" + c.capa);
        corpo.appendChild(el("div", { class: "previa-caixa" }, [video, el("div", { class: "previa-lado" }, [
          el("p", { class: "arquivo", text: c.arquivo || "" }), midia(c), botaoDescartar(x)])]));
      } else {
        corpo.appendChild(midia(c));
        corpo.appendChild(botaoDescartar(x));
      }
      var grade = el("div", { class: "redes" });
      REDES.forEach(function (r) {
        grade.appendChild(el("section", { class: "rede rede-" + r.k + (p[r.k] ? " pronta" : "") }, [
          el("h4", { text: r.nome + (p[r.k] ? " · postado" : "") }), campos(x, r)]));
      });
      corpo.appendChild(grade);
    }
    art.appendChild(corpo);
    return art;
  }

  var TEXTO_FAIXA = {
    agora: ["Nada para postar agora.", "para postar: atrasados e os de hoje, do mais antigo para o mais novo."],
    proximos: ["Nada agendado para os próximos dias.", "agendados para os próximos dias."],
    feitos: ["Nenhum corte marcado como postado ainda.", "já postados."],
    descartados: ["Nenhum corte descartado.", "descartados. Eles não entram em nenhuma lista e podem ser restaurados."]
  };

  function desenhar(forcar) {
    var hoje = diaDe(new Date()), amanha = diaDe(new Date(Date.now() + 864e5));
    docs.forEach(function (x) { x.dia = diaDe(new Date(x.c.postar_em)); });
    var chave = JSON.stringify([hoje, ver, abertos, docs.map(function (x) {
      return [x.id, x.c.postar_em, x.c.asset, x.c.postado, x.c.descartado];
    })]);
    if (!forcar && chave === desenhado) return;
    desenhado = chave;

    // contadores
    REDES.forEach(function (r) {
      var n = docs.filter(function (x) { return faixaDe(x, r.k, hoje) === "agora"; }).length;
      $("n-" + r.k).textContent = n ? String(n) : "";
    });
    var porFaixa = { agora: [], proximos: [], feitos: [], descartados: [] };
    docs.forEach(function (x) { porFaixa[faixaDe(x, ver.rede, hoje)].push(x); });
    FAIXAS.forEach(function (f) { $("n-" + f).textContent = porFaixa[f].length ? String(porFaixa[f].length) : ""; });
    controles.querySelectorAll(".seg").forEach(function (b) {
      var ativo = b.dataset.rede ? b.dataset.rede === ver.rede : b.dataset.faixa === ver.faixa;
      b.classList.toggle("ativo", ativo);
      b.setAttribute("aria-pressed", ativo ? "true" : "false");
    });

    var itens = porFaixa[ver.faixa].slice();
    if (ver.faixa === "feitos" || ver.faixa === "descartados") itens.reverse();
    lista.textContent = "";
    itens.forEach(function (x) { lista.appendChild(linha(x, hoje, amanha)); });

    var nomeRede = ver.rede === "todas" ? "" : " no " + REDES.filter(function (r) { return r.k === ver.rede; })[0].nome;
    explica.hidden = false;
    explica.textContent = itens.length
      ? itens.length + (itens.length === 1 ? " corte" : " cortes") + nomeRede + " " + TEXTO_FAIXA[ver.faixa][1]
      : TEXTO_FAIXA[ver.faixa][0];
    controles.hidden = !docs.length;
    if (!docs.length) {
      explica.hidden = true;
      avisar("Nenhum corte na pauta ainda. Os cortes de cada rodada aparecem aqui, com o vídeo para baixar e os textos de cada rede.");
    } else {
      avisar("");
    }
  }

  controles.addEventListener("click", function (ev) {
    var b = ev.target.closest(".seg");
    if (!b) return;
    if (b.dataset.rede) ver.rede = b.dataset.rede;
    if (b.dataset.faixa) ver.faixa = b.dataset.faixa;
    try { localStorage.setItem("pauta-ver", JSON.stringify(ver)); } catch (e) {}
    desenhar(true);
  });

  function receber(snap) {
    clearTimeout(relogio);
    docs = snap.docs.filter(function (d) { return d.exists; })
      .map(function (d) { return { id: d.id, c: JSON.parse(JSON.stringify(d.data())) }; })
      .filter(function (x) { return x.c && x.c.postar_em && x.c.redes; })
      .sort(function (a, b) { return a.c.postar_em < b.c.postar_em ? -1 : a.c.postar_em > b.c.postar_em ? 1 : 0; });
    desenhar(false);
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
    db.collection("cortes").limit(500).onSnapshot(receber, function (e) {
      clearTimeout(relogio);
      avisar("Não foi possível ler os cortes agora (" + ((e && e.code) || "erro") + "). Recarregue a página em instantes.");
    });
  });
})();
