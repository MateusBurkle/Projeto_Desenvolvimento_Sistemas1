# Identidade visual LEAF TI

Fonte: prancha "LEAFTI Brand Identity Guidelines" do grupo. Esta é a referência oficial para o agente `frontend`.

## Cores (tokens)
| Token CSS | Nome | Código | Uso |
|---|---|---|---|
| `--leaf-green` | Folha Green | `#76D356` | Cor principal da marca: ícones, detalhes, destaques, fundos escuros |
| `--leaf-green-dark` | Verde escuro (amostrado da prancha, confirmar) | `#31573F` | Texto de destaque, botões, cabeçalhos, rodapé, painéis |
| `--leaf-blue` | Sereno Blue | `#4A90E2` | Links e informação, em fundos que dêem contraste |
| `--leaf-gray` | Cinza Rocha | `#505050` | Texto de corpo e elementos neutros |
| `--leaf-white` | Branco Puro | `#FFFFFF` | Fundos e texto sobre escuro |
| `--leaf-yellow` | Sol Amarelo (acento) | `#FFC300` | Alertas, selos e chamadas pontuais |

## Regras de contraste (RNF01)
- Verde claro `#76D356` sobre branco: cerca de 1,8:1. Azul `#4A90E2` sobre branco: cerca de 3,3:1. Amarelo `#FFC300`: pior ainda. Nenhum desses serve para texto sobre fundo branco.
- Texto, botões e cabeçalhos: verde escuro `#31573F` (cerca de 8:1 sobre branco) ou cinza `#505050`.
- Verde claro e amarelo sobre fundo verde escuro funcionam bem (ícones, realces, botão com texto escuro).
- Fonte principal de no mínimo 16 px.

## Tipografia
- Títulos e logotipo: serifada elegante ("Leaf Serif" Bold na prancha). Equivalente web adotado: **Playfair Display** (Google Fonts), peso 600 a 700.
- Textos e interface: sem serifa ("Leaf Sans Regular"). Equivalente web adotado: **Source Sans 3** (Google Fonts), peso 400 e 600.
- As fontes da prancha são fictícias; trocar os equivalentes só com decisão do grupo.

## Marca
- Logotipo: folha com um traço interno, em três variações (verde claro, cinza, branco) sobre fundo verde escuro; assinatura "Informação Sustentável".
- Arquivos já existentes em `frontend/images/`: `logofolha.png`, `logosemfundo.png`, `logo vertical.png`, `logo vertical letra branca.png`, `Leaf TI.png`. Usar a versão de maior contraste com o fundo. Se o grupo tiver o logotipo em SVG, preferir.
- Padrão: repetição da folha em verde muito claro, para fundos de seções e capas, sempre discreto (não pode competir com o texto).
- Aplicações da prancha: cartões, pasta, caderno, celular, apresentação acadêmica. Em telas: cabeçalho claro com logotipo, rodapé e faixas em verde escuro, cartões brancos.

## Mensagens de erro: exceção aprovada pelo usuário
- O vermelho não faz parte da paleta da marca, mas o usuário aprovou seu uso **somente para mensagens de erro** (DP-06 revista, 2026-10-30).
- Token único: `--leaf-erro: #9B1C1C` (texto) sobre `--leaf-erro-tint: #FDF0F0` (fundo): contraste 7,3:1 (mínimo 4,5:1).
- `.alert-danger`: fundo `#FDF0F0`, borda de 2 px `#9B1C1C`, texto `#9B1C1C`, ícone e prefixo "Erro:". `.invalid-feedback`/`.text-danger`: texto `#9B1C1C` com ícone ✖. Campo `.is-invalid`: borda de 3 px `#9B1C1C`.
- Nunca só cor: sempre ícone e texto (RNF06). Não usar o vermelho para nada além de erros.
- Avisos não críticos (ex.: sessão expirada) usam `.alert-warning` (amarelo `#FFC300`, texto verde escuro).

## Logotipo para fundo escuro
- `frontend/images/logosemfundo-claro.png`: gerado de `logosemfundo.png` (original intacto), com transparência mantida, folha `#76D356` e traço interno branco. Usar em cabeçalhos e rodapés de fundo verde escuro `#31573F` (traço 8,2:1, folha 4,4:1; mínimo 3:1 para gráficos). Em fundo claro (cartão de login) usar `logosemfundo.png`.

## Estado do front-end atual
O CSS existente usa verdes próprios (`#2ecc71`, `#7ED957`, `#12FF46`) e várias fontes. Migrar para os tokens acima, página a página, a partir de `css/identidade.css` (ver `docs/FRONTEND_EXISTENTE.md`).
