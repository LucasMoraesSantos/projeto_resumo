import json
import os
import re
from typing import Dict, List, Optional, Tuple

MEMORY_FILE = "memory.json"


def load_memory() -> List[Dict[str, str]]:
    """Carrega histórico local de atendimentos."""
    if not os.path.exists(MEMORY_FILE):
        return []

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, OSError):
        pass

    return []


def save_memory(entry_text: str, summary_text: str) -> None:
    """Salva nova entrada no histórico local."""
    memory = load_memory()
    memory.append({"entrada": entry_text, "resumo": summary_text})

    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memory, file, ensure_ascii=False, indent=2)


def read_multiline_input() -> str:
    """Lê texto multilinha até linha vazia."""
    print("Cole o texto do atendimento (finalize com linha vazia):")
    lines: List[str] = []

    while True:
        line = input()
        if line.strip() == "":
            break
        lines.append(line)

    return "\n".join(lines).strip()


def extract_client_name(text: str) -> str:
    """Extrai o nome do cliente no padrão 'Cliente: Nome'."""
    pattern = re.compile(r"cliente\s*:\s*([^\n,;.]+)", re.IGNORECASE)
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    return "Não identificado"


def split_sentences(text: str) -> List[str]:
    """Quebra texto em frases simples por pontuação ou quebra de linha."""
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [part.strip() for part in parts if part.strip()]


def find_problem(text: str) -> str:
    """Identifica frase com sinais de problema."""
    keywords = ["problema", "erro", "não funciona", "nao funciona", "falha"]
    for sentence in split_sentences(text):
        lower_sentence = sentence.lower()
        if any(keyword in lower_sentence for keyword in keywords):
            return sentence
    return "Não informado"


def find_action(text: str) -> str:
    """Identifica ação executada durante o atendimento."""
    keywords = ["senha", "suporte", "orientado", "orientação", "reiniciado", "ajustado"]
    matches: List[str] = []

    for sentence in split_sentences(text):
        lower_sentence = sentence.lower()
        if any(keyword in lower_sentence for keyword in keywords):
            matches.append(sentence)

    if matches:
        return " | ".join(matches)
    return "Não informada"


def infer_subject(problem: str) -> str:
    """Deriva assunto com base no problema identificado."""
    if problem == "Não informado":
        return "Não informado"

    lower_problem = problem.lower()
    if "login" in lower_problem or "senha" in lower_problem:
        return "Acesso/Login"
    if "sistema" in lower_problem:
        return "Sistema"
    if "pagamento" in lower_problem or "cobran" in lower_problem:
        return "Financeiro"
    return "Atendimento geral"


def find_status(text: str) -> str:
    """Define status por pistas no texto."""
    lower_text = text.lower()

    resolved_clues = [
        "resolvido",
        "resolvida",
        "funcionou",
        "cliente confirmou",
        "confirmou que deu certo",
        "problema solucionado",
    ]
    pending_clues = ["pendente", "aguardando", "em análise", "retorno", "sem concluir"]

    if any(clue in lower_text for clue in resolved_clues):
        return "Resolvido"
    if any(clue in lower_text for clue in pending_clues):
        return "Pendente"
    return "Sem resposta"


def detect_inactivity(text: str) -> str:
    """Inatividade = Sim se última mensagem não for do cliente."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "Não"

    last_line = lines[-1].lower()
    if last_line.startswith("cliente:"):
        return "Não"
    return "Sim"


def find_observations(text: str) -> str:
    """Busca detalhes extras para observações."""
    obs_keywords = ["observação", "obs", "importante", "nota"]
    obs_sentences = []
    for sentence in split_sentences(text):
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in obs_keywords):
            obs_sentences.append(sentence)

    if obs_sentences:
        return " | ".join(obs_sentences)
    return "Sem observações"


def normalize_problem(problem: str) -> str:
    """Normaliza formulações frequentes para manter consistência local."""
    lowered = problem.lower()
    if "login" in lowered:
        return "Problema de login"
    if "senha" in lowered:
        return "Problema de senha"
    return problem


def build_pattern_bank(memory: List[Dict[str, str]]) -> Dict[str, str]:
    """Cria banco simples de padrões problema -> assunto a partir do histórico."""
    pattern_bank: Dict[str, str] = {}

    for item in memory:
        summary = item.get("resumo", "")
        problem_match = re.search(r"\* Problema:\s*(.+)", summary)
        subject_match = re.search(r"\* Assunto:\s*(.+)", summary)

        if problem_match and subject_match:
            key = normalize_problem(problem_match.group(1).strip())
            value = subject_match.group(1).strip()
            if key and value and key != "Não informado":
                pattern_bank[key] = value

    return pattern_bank


def choose_subject_with_memory(problem: str, memory: List[Dict[str, str]]) -> str:
    """Reutiliza assunto prévio para problemas já vistos."""
    normalized_problem = normalize_problem(problem)
    pattern_bank = build_pattern_bank(memory)

    if normalized_problem in pattern_bank:
        return pattern_bank[normalized_problem]

    return infer_subject(problem)


def generate_summary(data: Dict[str, str]) -> str:
    """Gera resumo no formato obrigatório."""
    return (
        "📌 Resumo do Atendimento:\n\n"
        f"* Cliente: {data['cliente']}\n"
        f"* Assunto: {data['assunto']}\n"
        f"* Problema: {data['problema']}\n"
        f"* Ação realizada: {data['acao']}\n"
        f"* Status: {data['status']}\n"
        f"* Inatividade: {data['inatividade']}\n"
        f"* Observações: {data['observacoes']}"
    )


def process_attendance(text: str, memory: List[Dict[str, str]]) -> Tuple[Dict[str, str], str]:
    """Executa pipeline completo de resumo."""
    client = extract_client_name(text)
    problem = find_problem(text)
    action = find_action(text)
    status = find_status(text)
    inactivity = detect_inactivity(text)
    observations = find_observations(text)
    subject = choose_subject_with_memory(problem, memory)

    structured = {
        "cliente": client,
        "assunto": subject,
        "problema": normalize_problem(problem),
        "acao": action,
        "status": status,
        "inatividade": inactivity,
        "observacoes": observations,
    }

    summary = generate_summary(structured)
    return structured, summary


def ensure_memory_file_exists() -> None:
    """Garante existência do arquivo memory.json."""
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w", encoding="utf-8") as file:
            json.dump([], file, ensure_ascii=False, indent=2)


def main() -> None:
    ensure_memory_file_exists()
    memory = load_memory()

    input_text = read_multiline_input()
    if not input_text:
        print("Nenhum texto foi informado.")
        return

    _, summary = process_attendance(input_text, memory)

    print("\n" + summary)
    save_memory(input_text, summary)
    print("\nAtendimento salvo em memory.json")


if __name__ == "__main__":
    main()
