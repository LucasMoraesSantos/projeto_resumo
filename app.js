const STORAGE_KEY = "attendance_memory_v1";

function splitSentences(text) {
  return text
    .split(/(?<=[.!?])\s+|\n+/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function extractClientName(text) {
  const match = text.match(/cliente\s*:\s*([^\n,;.]+)/i);
  return match ? match[1].trim() : "Não identificado";
}

function findProblem(text) {
  const keywords = ["problema", "erro", "não funciona", "nao funciona", "falha"];

  for (const sentence of splitSentences(text)) {
    const lower = sentence.toLowerCase();
    if (keywords.some((keyword) => lower.includes(keyword))) {
      return sentence;
    }
  }

  return "Não informado";
}

function findAction(text) {
  const keywords = ["senha", "suporte", "orientado", "orientação", "reiniciado", "ajustado"];
  const matches = splitSentences(text).filter((sentence) => {
    const lower = sentence.toLowerCase();
    return keywords.some((keyword) => lower.includes(keyword));
  });

  return matches.length ? matches.join(" | ") : "Não informada";
}

function findStatus(text) {
  const lower = text.toLowerCase();
  const resolvedClues = [
    "resolvido",
    "resolvida",
    "funcionou",
    "cliente confirmou",
    "confirmou que deu certo",
    "problema solucionado",
  ];
  const pendingClues = ["pendente", "aguardando", "em análise", "retorno", "sem concluir"];

  if (resolvedClues.some((clue) => lower.includes(clue))) {
    return "Resolvido";
  }
  if (pendingClues.some((clue) => lower.includes(clue))) {
    return "Pendente";
  }
  return "Sem resposta";
}

function detectInactivity(text) {
  const lines = text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  if (!lines.length) {
    return "Não";
  }

  return lines[lines.length - 1].toLowerCase().startsWith("cliente:") ? "Não" : "Sim";
}

function findObservations(text) {
  const keywords = ["observação", "obs", "importante", "nota"];
  const matches = splitSentences(text).filter((sentence) => {
    const lower = sentence.toLowerCase();
    return keywords.some((keyword) => lower.includes(keyword));
  });

  return matches.length ? matches.join(" | ") : "Sem observações";
}

function normalizeProblem(problem) {
  const lower = problem.toLowerCase();
  if (lower.includes("login")) return "Problema de login";
  if (lower.includes("senha")) return "Problema de senha";
  return problem;
}

function inferSubject(problem) {
  const lower = problem.toLowerCase();
  if (problem === "Não informado") return "Não informado";
  if (lower.includes("login") || lower.includes("senha")) return "Acesso/Login";
  if (lower.includes("sistema")) return "Sistema";
  if (lower.includes("pagamento") || lower.includes("cobran")) return "Financeiro";
  return "Atendimento geral";
}

function loadMemory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveMemory(memory) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(memory));
}

function buildPatternBank(memory) {
  const bank = {};

  for (const item of memory) {
    const summary = item.resumo || "";
    const problemMatch = summary.match(/\* Problema:\s*(.+)/);
    const subjectMatch = summary.match(/\* Assunto:\s*(.+)/);

    if (problemMatch && subjectMatch) {
      const key = normalizeProblem(problemMatch[1].trim());
      const value = subjectMatch[1].trim();
      if (key && value && key !== "Não informado") {
        bank[key] = value;
      }
    }
  }

  return bank;
}

function chooseSubjectWithMemory(problem, memory) {
  const key = normalizeProblem(problem);
  const bank = buildPatternBank(memory);
  return bank[key] || inferSubject(problem);
}

function generateSummary(data) {
  return `📌 Resumo do Atendimento:\n\n* Cliente: ${data.cliente}\n* Assunto: ${data.assunto}\n* Problema: ${data.problema}\n* Ação realizada: ${data.acao}\n* Status: ${data.status}\n* Inatividade: ${data.inatividade}\n* Observações: ${data.observacoes}`;
}

function processAttendance(text, memory) {
  const problem = findProblem(text);

  const data = {
    cliente: extractClientName(text),
    assunto: chooseSubjectWithMemory(problem, memory),
    problema: normalizeProblem(problem),
    acao: findAction(text),
    status: findStatus(text),
    inatividade: detectInactivity(text),
    observacoes: findObservations(text),
  };

  return generateSummary(data);
}

function updateHistoryCount() {
  const count = loadMemory().length;
  document.getElementById("historyCount").textContent = `${count} atendimento(s) salvo(s).`;
}

function handleGenerate() {
  const text = document.getElementById("attendanceInput").value.trim();
  if (!text) {
    alert("Informe o texto do atendimento.");
    return;
  }

  const memory = loadMemory();
  const summary = processAttendance(text, memory);
  document.getElementById("summaryOutput").textContent = summary;

  memory.push({ entrada: text, resumo: summary });
  saveMemory(memory);
  updateHistoryCount();
}

function handleClearHistory() {
  localStorage.removeItem(STORAGE_KEY);
  updateHistoryCount();
}

function init() {
  document.getElementById("generateButton").addEventListener("click", handleGenerate);
  document.getElementById("clearHistoryButton").addEventListener("click", handleClearHistory);
  updateHistoryCount();
}

init();
