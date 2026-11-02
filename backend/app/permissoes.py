"""Matriz de funcionalidades por perfil (RN01..RN05), igual a x-matriz-funcionalidades do contrato do módulo 0."""

ADMINISTRADOR = "Administrador"
FUNCIONARIO = "Funcionário"
CLIENTE_EMPRESA = "Cliente Empresa"
CLIENTE_ONG = "Cliente ONG"
EMPRESA_DOADORA = "Empresa Doadora"

PERFIS = (ADMINISTRADOR, FUNCIONARIO, CLIENTE_EMPRESA, CLIENTE_ONG, EMPRESA_DOADORA)

MATRIZ_FUNCIONALIDADES = {
    ADMINISTRADOR: ["usuarios", "organizacoes", "parceiros", "categorias", "equipamentos",
                    "solicitacoes", "vendas", "notas_fiscais", "relatorios", "solicitacoes_doacao", "meu_perfil"],  # DP-80, DP-101
    FUNCIONARIO: ["organizacoes", "equipamentos", "solicitacoes", "vendas", "relatorios", "solicitacoes_doacao", "meu_perfil"],  # RN03, DP-80, DP-101
    CLIENTE_EMPRESA: ["catalogo", "minhas_compras", "minhas_notas_fiscais", "usuarios_organizacao", "meu_perfil"],  # RN04, DP-99
    CLIENTE_ONG: ["minhas_doacoes", "solicitacoes_doacao", "usuarios_organizacao", "meu_perfil"],  # RN04, DP-80, DP-99
    EMPRESA_DOADORA: ["minhas_solicitacoes", "meu_perfil"],  # RN05, DP-99
}


def funcionalidades_do_perfil(perfil: str) -> list[str]:
    return list(MATRIZ_FUNCIONALIDADES.get(perfil, []))
