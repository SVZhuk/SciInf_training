(() => {
  const API_BASE = "/api/v1/samples";

  const layout = document.querySelector(".layout");
  const sidebar = document.querySelector(".sidebar");
  const tableContainer = document.getElementById("table-container");
  const formPanel = document.getElementById("form-panel");
  const formTitle = document.getElementById("form-title");
  const sampleForm = document.getElementById("sample-form");
  const fieldName = document.getElementById("field-name");
  const fieldOrganism = document.getElementById("field-organism");
  const fieldSequence = document.getElementById("field-sequence");
  const sequenceWrapper = document.getElementById("field-sequence-wrapper");
  const formError = document.getElementById("form-error");
  const formCancel = document.getElementById("form-cancel");
  const btnAdd = document.getElementById("btn-add");
  const btnEdit = document.getElementById("btn-edit");
  const btnDelete = document.getElementById("btn-delete");

  let currentSamples = [];
  let selectedId = null;
  let formMode = "add";

  function pad(value) {
    return String(value).padStart(2, "0");
  }

  function formatCreatedAt(iso) {
    const d = new Date(iso);
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
  }

  function alignSidebar() {
    const firstRow = tableContainer.querySelector("tbody tr");
    if (!firstRow) {
      sidebar.style.marginTop = "0";
      return;
    }
    sidebar.style.marginTop = `${firstRow.getBoundingClientRect().top - layout.getBoundingClientRect().top}px`;
  }

  function renderTable(samples, total) {
    const countLabel = `${total} sample${total === 1 ? "" : "s"}`;
    if (samples.length === 0) {
      tableContainer.innerHTML = `<p class="subtitle">${countLabel}</p><p class="empty">No samples yet.</p>`;
      alignSidebar();
      return;
    }
    const rows = samples
      .map(
        (s) => `
        <tr data-id="${s.id}">
          <td>${escapeHtml(s.name)}</td>
          <td>${s.organism}</td>
          <td>${s.length}</td>
          <td>${(s.gc_content * 100).toFixed(1)}%</td>
          <td>${formatCreatedAt(s.created_at)}</td>
        </tr>`
      )
      .join("");
    tableContainer.innerHTML = `
      <p class="subtitle">${countLabel}</p>
      <table>
        <thead>
          <tr><th>Name</th><th>Organism</th><th>Length</th><th>GC Content</th><th>Created At</th></tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>`;
    for (const row of tableContainer.querySelectorAll("tbody tr")) {
      row.addEventListener("click", () => selectRow(row.dataset.id));
    }
    if (selectedId) {
      const row = tableContainer.querySelector(`tr[data-id="${selectedId}"]`);
      if (row) {
        row.classList.add("selected");
      } else {
        clearSelection();
      }
    }
    alignSidebar();
  }

  async function fetchAndRender() {
    const response = await fetch(`${API_BASE}?limit=50&offset=0`);
    const page = await response.json();
    currentSamples = [...page.items].reverse();
    renderTable(currentSamples, page.total);
  }

  function selectRow(id) {
    selectedId = id;
    for (const row of tableContainer.querySelectorAll("tbody tr")) {
      row.classList.toggle("selected", row.dataset.id === id);
    }
    btnEdit.disabled = false;
    btnDelete.disabled = false;
  }

  function clearSelection() {
    selectedId = null;
    btnEdit.disabled = true;
    btnDelete.disabled = true;
  }

  function showFormError(detail) {
    const message = Array.isArray(detail)
      ? detail.map((e) => e.msg).join(", ")
      : String(detail);
    formError.textContent = message;
    formError.hidden = false;
  }

  function openPanel(mode) {
    formMode = mode;
    formError.hidden = true;
    sampleForm.reset();
    if (mode === "add") {
      formTitle.textContent = "Add Sample";
      sequenceWrapper.hidden = false;
      fieldSequence.required = true;
    } else {
      const sample = currentSamples.find((s) => s.id === selectedId);
      if (!sample) {
        return;
      }
      formTitle.textContent = "Edit Sample";
      sequenceWrapper.hidden = true;
      fieldSequence.required = false;
      fieldName.value = sample.name;
      fieldOrganism.value = sample.organism;
    }
    formPanel.hidden = false;
  }

  function closePanel() {
    formPanel.hidden = true;
    sampleForm.reset();
    formError.hidden = true;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const payload =
      formMode === "add"
        ? { name: fieldName.value, organism: fieldOrganism.value, sequence: fieldSequence.value }
        : { name: fieldName.value, organism: fieldOrganism.value };
    const url = formMode === "add" ? API_BASE : `${API_BASE}/${selectedId}`;
    const method = formMode === "add" ? "POST" : "PATCH";
    const response = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const body = await response.json();
      showFormError(body.detail);
      return;
    }
    closePanel();
    clearSelection();
    await fetchAndRender();
  }

  async function handleDelete() {
    if (!selectedId) {
      return;
    }
    if (!window.confirm("Delete the selected sample?")) {
      return;
    }
    await fetch(`${API_BASE}/${selectedId}`, { method: "DELETE" });
    clearSelection();
    await fetchAndRender();
  }

  btnAdd.addEventListener("click", () => openPanel("add"));
  btnEdit.addEventListener("click", () => openPanel("edit"));
  btnDelete.addEventListener("click", handleDelete);
  formCancel.addEventListener("click", closePanel);
  sampleForm.addEventListener("submit", handleSubmit);

  document.addEventListener("DOMContentLoaded", fetchAndRender);
})();
