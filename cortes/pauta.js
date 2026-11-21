(function () {
  function selecionar(el) {
    var faixa = document.createRange();
    faixa.selectNodeContents(el);
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(faixa);
  }
  document.querySelectorAll(".copiar").forEach(function (botao) {
    botao.addEventListener("click", function () {
      var alvo = document.getElementById(botao.dataset.alvo);
      var feito = function (texto) {
        botao.textContent = texto;
        botao.classList.add("ok");
        setTimeout(function () { botao.textContent = "Copiar"; botao.classList.remove("ok"); }, 1600);
      };
      var reserva = function () { selecionar(alvo); feito("Selecionado: copie"); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(alvo.textContent).then(function () { feito("Copiado"); }, reserva);
      } else {
        reserva();
      }
    });
  });
  document.querySelectorAll(".feito input").forEach(function (caixa) {
    var marcar = function () { caixa.closest(".rede").classList.toggle("pronta", caixa.checked); };
    try { caixa.checked = localStorage.getItem(caixa.id) === "1"; } catch (e) {}
    marcar();
    caixa.addEventListener("change", function () {
      marcar();
      try { localStorage.setItem(caixa.id, caixa.checked ? "1" : "0"); } catch (e) {}
    });
  });
})();
