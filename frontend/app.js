const views = document.querySelectorAll(".view");
const tabs = document.querySelectorAll(".tab");
const sudokuGrid = document.querySelector("#sudokuGrid");
const sudokuPreview = document.querySelector("#sudokuPreview");
const sudokuStatus = document.querySelector("#sudokuStatus");
const sample =
  "530070000600195000098000060800060003400803001700020006060000280000419005000080079";


async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

function showView(id) {
  views.forEach((view) => view.classList.toggle("is-active", view.id === id));
  tabs.forEach((tab) => tab.classList.toggle("is-active", tab.dataset.view === id));
  if (id === "dashboard") drawDashboard();
}

tabs.forEach((tab) => tab.addEventListener("click", () => showView(tab.dataset.view)));

function createSudokuGrid() {
  sudokuGrid.innerHTML = "";
  sudokuPreview.innerHTML = "";
  for (let i = 0; i < 81; i += 1) {
    const input = document.createElement("input");
    input.inputMode = "numeric";
    input.maxLength = 1;
    input.ariaLabel = `Cell ${i + 1}`;
    input.addEventListener("input", () => {
      input.value = input.value.replace(/[^1-9]/g, "").slice(0, 1);
      input.classList.toggle("prefilled", input.value !== "");
      renderPreview(readSudokuGrid());
    });
    sudokuGrid.appendChild(input);

    const cell = document.createElement("div");
    sudokuPreview.appendChild(cell);
  }
}

function readSudokuGrid() {
  const values = [...sudokuGrid.querySelectorAll("input")].map((input) =>
    input.value ? Number(input.value) : 0,
  );
  return Array.from({ length: 9 }, (_, row) => values.slice(row * 9, row * 9 + 9));
}

function gridToDigits(grid) {
  return grid.flat().join("");
}

function writeSudokuGrid(raw) {
  [...sudokuGrid.querySelectorAll("input")].forEach((input, index) => {
    input.value = raw[index] === "0" ? "" : raw[index] || "";
    input.classList.toggle("prefilled", input.value !== "");
  });
  renderPreview(readSudokuGrid());
}

function renderPreview(grid, original = null) {
  [...sudokuPreview.children].forEach((cell, index) => {
    const row = Math.floor(index / 9);
    const col = index % 9;
    const value = grid[row][col];
    cell.textContent = value || "";
    cell.classList.toggle("prefilled", original ? original[row][col] !== 0 : value !== 0);
  });
}

document.querySelector("#loadSample").addEventListener("click", () => {
  writeSudokuGrid(sample);
  sudokuStatus.textContent = "Sample loaded. Press Solve Sudoku.";
});

document.querySelector("#clearSudoku").addEventListener("click", () => {
  writeSudokuGrid("0".repeat(81));
  sudokuStatus.textContent = "Enter digits from 1 to 9. Leave blanks empty.";
});

document.querySelector("#solveSudoku").addEventListener("click", async () => {
  const original = readSudokuGrid();
  sudokuStatus.textContent = "Solving with Python...";
  try {
    const result = await api("/api/sudoku/solve", {
      method: "POST",
      body: JSON.stringify({ digits: gridToDigits(original) }),
    });
    renderPreview(result.grid, original);
    sudokuStatus.textContent = `Solved by Python in ${result.time_taken_seconds.toFixed(3)} seconds.`;
  } catch (error) {
    sudokuStatus.textContent = error.message;
  }
});

document.querySelector("#uploadSudokuBtn").addEventListener("click", () => {
  const fileInput = document.querySelector("#sudokuImageUpload");
  fileInput.value = "";
  fileInput.click();
});

document.querySelector("#sudokuImageUpload").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async (event) => {
    sudokuStatus.textContent = "Uploading and solving with Python OCR...";
    const imgElement = document.querySelector("#sudokuFlattenedImage");
    imgElement.style.display = "none";
    try {
      const response = await fetch("/api/sudoku/upload_and_solve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: event.target.result }),
      });
      const result = await response.json();
      
      if (result.digits) {
        writeSudokuGrid(result.digits);
        renderPreview(result.grid, readSudokuGrid());
      }
      if (result.image) {
        imgElement.src = result.image;
        imgElement.style.display = "block";
      }
      
      if (!response.ok) {
        throw new Error(result.error || "Request failed");
      }
      
      sudokuStatus.textContent = `Solved by OCR and Python in ${result.time_taken_seconds.toFixed(3)} seconds.`;
    } catch (error) {
      sudokuStatus.textContent = error.message;
    }
  };
  reader.readAsDataURL(file);
});

async function loadHistory() {
  const result = await api("/api/history");
  return result.history.map((row) => ({
    type: row.puzzle_type,
    seconds: row.time_taken_seconds,
    date: row.date,
  }));
}

async function drawDashboard() {
  try {
    const history = await loadHistory();
    drawLineChart(document.querySelector("#timeChart"), history);
  } catch (error) {
    const ctx = clearCanvas(document.querySelector("#timeChart"), "Solves over time");
    drawMessage(ctx, error.message);
  }
}

function clearCanvas(canvas, title) {
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#172027";
  ctx.font = "18px Segoe UI, Arial";
  ctx.fillText(title, 22, 34);
  return ctx;
}

function drawLineChart(canvas, history) {
  const ctx = clearCanvas(canvas, "Solves over time");
  if (!history.length) return drawEmpty(ctx);
  const counts = history.reduce((acc, item) => {
    const day = item.date.slice(0, 10);
    acc[day] = (acc[day] || 0) + 1;
    return acc;
  }, {});
  const entries = Object.entries(counts);
  const max = Math.max(...entries.map(([, count]) => count), 1);
  ctx.strokeStyle = "#1f7a6d";
  ctx.lineWidth = 3;
  ctx.beginPath();
  entries.forEach(([, count], index) => {
    const x = 40 + (index * 430) / Math.max(entries.length - 1, 1);
    const y = 220 - (count / max) * 150;
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
    ctx.fillStyle = "#1f7a6d";
    ctx.fillRect(x - 4, y - 4, 8, 8);
  });
  ctx.stroke();
}



function drawEmpty(ctx) {
  drawMessage(ctx, "No history yet. Solve a puzzle first.");
}

function drawMessage(ctx, message) {
  ctx.fillStyle = "#687682";
  ctx.font = "15px Segoe UI, Arial";
  ctx.fillText(message, 22, 72);
}

document.querySelector("#clearHistory").addEventListener("click", async () => {
  await api("/api/history/clear", { method: "POST", body: "{}" });
  drawDashboard();
});

createSudokuGrid();
writeSudokuGrid("0".repeat(81));

drawDashboard();
