document.addEventListener("DOMContentLoaded", () => {
  const formFiltro = document.getElementById("formfiltro");
  if (formFiltro) {
    const searchInput = formFiltro.querySelector("input[type='text']");
    const selectEmpresa = formFiltro.querySelector("select[name='empresas']");
    const cards = document.querySelectorAll("#cartoes .col");

    const aplicarFiltros = () => {
      const query = searchInput.value.toLowerCase().trim();
      const empresa = selectEmpresa.value.toLowerCase();

      cards.forEach(card => {
        const title = card.querySelector(".card-title").textContent.toLowerCase();
        const comp = card.querySelector(".text-muted").textContent.toLowerCase();

        const matchQuery = title.includes(query);
        const matchEmpresa = !empresa || comp.includes(empresa);

        if (matchQuery && matchEmpresa) {
          card.classList.remove("d-none");
        } else {
          card.classList.add("d-none");
        }
      });
    };

    searchInput.addEventListener("input", aplicarFiltros);
    selectEmpresa.addEventListener("change", aplicarFiltros);
  }
});