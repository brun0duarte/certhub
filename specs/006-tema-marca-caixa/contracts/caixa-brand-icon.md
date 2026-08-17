# Contract: Ícone de marca (elemento-síntese "X") do Modo CAIXA

## Gatilho

Mesmo de `caixa-accent-tokens.md`: `document.documentElement.dataset.accent === "caixa"`.

## Contrato de comportamento

1. Quando `data-accent === "caixa"`, o conteúdo de `.brand-icon` (hoje o emoji `🔐`) DEVE ser substituído por um SVG inline representando o elemento-síntese "X" da CAIXA.
2. Quando `data-accent` for qualquer outro valor, `.brand-icon` DEVE conter o emoji `🔐` (comportamento atual, sem regressão).
3. A troca acontece em `applyAccent(a)` (`app/static/app.js`), no mesmo ponto que já seta `data-accent` e grava em `localStorage` — sem novo listener ou ciclo de vida.
4. A troca também DEVE ser aplicada na carga inicial da página (quando `applyAccent(localStorage.getItem("certhub-accent") || "blue")` roda no boot), não só em cliques subsequentes.

## Especificação do asset (SVG inline)

- `viewBox="0 0 100 100"`, sem `width`/`height` fixos no SVG em si (dimensionado por CSS via `.brand-icon`, herdando o `font-size: 26px` atual como referência de área, ou uma regra CSS equivalente `.brand-icon svg { width: 26px; height: 26px; }`).
- Duas formas geométricas (paralelogramos) sobrepostas formando um "X", replicando a proporção da versão chapada positiva do manual (seção 1.2.1):
  - Uma faixa diagonal do canto superior-esquerdo ao inferior-direito, preenchimento `#0066B3` (Azul CAIXA).
  - Uma faixa diagonal do canto superior-direito ao inferior-esquerdo, preenchimento `#F7941E` (Laranja CAIXA).
- Cores DEVEM ser fixas (`fill="#0066B3"` / `fill="#F7941E"`), não herdadas de `currentColor` nem de variável CSS — o manual proíbe alterar as cores da marca (seção 1.2.4, "não alterar cores do X"), então o ícone não deve reagir a temas/paletas.
- Nenhuma rotação, distorção de proporção (`preserveAspectRatio` default `xMidYMid meet`) ou efeito (sombra/gradiente) aplicado — regra do manual seção 1.2.4.
- Tamanho renderizado NUNCA deve ficar abaixo de 26px de largura na sidebar (acima do mínimo de 50px "on-line" do manual não se aplica literalmente a um ícone de 26px de UI, mas o SVG vetorial garante nitidez em qualquer tamanho, então o requisito de "não pixelizar" é satisfeito por construção — ver `research.md` §5).

## Não-regressão

- `<link rel="icon">` (favicon, `app/static/index.html:9`, já um SVG de emoji) não é alterado por esta feature.
- O emoji `🔐` continua sendo o ícone padrão para `blue`/`green`/`purple`/`teal`/`amber`/`red`.
