# Histórico de Mudanças

## 8.0.53 - 2026-05-09

- Melhorado o aproveitamento horizontal dos formulários na coluna de ajustes.
- Mantido o conteúdo centralizado, com campos mais largos e espaçamento mais equilibrado.

## 8.0.52 - 2026-05-09

- Atualizada a documentação para apontar para o repositório `Discasa/TAURUS_VideoMaker`.

## 8.0.51 - 2026-05-09

- A tabela da aba Músicas agora ocupa a altura disponível da aba.
- A área da scrollbar vertical fica reservada desde o início para listas longas de músicas.

## 8.0.50 - 2026-05-09

- Promovida a tela Músicas para aba principal antes de Títulos.
- A aba Títulos agora exibe diretamente as configurações de fonte, sem subabas internas.

## 8.0.49 - 2026-05-09

- Simplificada a descrição da opção de renderização para uma linha.

## 8.0.48 - 2026-05-09

- Reduzida a altura visual da barra de progresso.

## 8.0.47 - 2026-05-09

- Alinhado o controle de volume do preview com a borda real do vídeo.

## 8.0.46 - 2026-05-09

- Corrigido o fundo da barra de volume do preview para combinar com o painel.
- Ajustado o alinhamento direito do volume para manter a porcentagem dentro da largura do preview.

## 8.0.45 - 2026-05-09

- O slider de volume agora acompanha a largura e posição do preview ao abrir ou fechar o log.

## 8.0.44 - 2026-05-09

- Ajustado o layout quando o log é aberto para evitar truncamento e sobreposição no preview.
- O preview reduz altura enquanto o log está visível e volta ao tamanho normal quando o log é ocultado.

## 8.0.43 - 2026-05-09

- Centralizado verticalmente o conjunto de preview e controle de volume no painel central.

## 8.0.42 - 2026-05-09

- Removido o fundo próprio dos sliders para combinar com o painel onde estão inseridos.
- Aproximado o controle de volume do preview da área de vídeo.

## 8.0.41 - 2026-05-09

- Ajustada a descrição da opção de renderização para ocupar duas linhas sem cortar texto.

## 8.0.40 - 2026-05-09

- Corrigido o estilo do log aberto, que herdava altura máxima dos campos compactos.
- Aumentada a área do log aberto para facilitar leitura durante renders.

## 8.0.39 - 2026-05-09

- Ajustada a cor de fundo do trilho dos sliders para combinar com os painéis da interface.

## 8.0.38 - 2026-05-09

- Corrigido artefato visual no knob dos sliders.
- Aumentada a altura do log quando ele está aberto.

## 8.0.37 - 2026-05-09

- O botão Render/Parar agora controla apenas o preview vivo.
- Após gerar o preview, o vídeo toca em loop até o usuário clicar em Parar.
- Durante o render final, o botão de preview fica desabilitado e não cancela exportações.

## 8.0.36 - 2026-05-09

- O preview central agora pode reproduzir o vídeo real gerado pelo render de teste.
- O botão de teste passou a ser Render/Parar para iniciar ou cancelar o render do preview.
- Adicionado controle de volume do preview no canto inferior direito da área central.
- Ajustado o texto da opção de GPU para indicar que, se desabilitada, a renderização usa CPU.

## 8.0.35 - 2026-05-09

- Adicionado seletor de cor para a sombra dos títulos, intro e marca d'água.
- Ajustados os sliders da interface para trabalhar em incrementos de 5 pontos.
- O render agora aplica a cor de sombra escolhida nos textos gerados pelo FFmpeg.

## 8.0.34 - 2026-05-09

- Trocados os controles de opacidade por sliders em toda a interface.
- Trocados os controles de sombra por sliders, mantendo escala decimal compatível com o engine.

## 8.0.33 - 2026-05-09

- Removido o botão redundante de carregar músicas da subaba Músicas.
- Removida a descrição inferior da subaba Músicas para deixar a área mais limpa.

## 8.0.32 - 2026-05-09

- A aba Títulos agora tem subabas para separar configurações de fonte e títulos das músicas.
- Adicionada tabela de músicas para gerar títulos automáticos e editar manualmente o título exibido de cada faixa.
- O engine passa a respeitar títulos personalizados por arquivo, mantendo o título automático quando não houver edição manual.

## 8.0.31 - 2026-05-09

- Removido código legado de legendas ASS/subtitles que não era mais usado pelo render atual.
- Removidos helpers sem uso ligados ao fluxo antigo de prévia da intro e filtros antigos.
- Removidos imports não utilizados na UI e no backend.

## 8.0.30 - 2026-05-09

- Substituído o campo de texto por um preview da imagem quando a marca d'água está no modo imagem.
- O preview da marca d'água atualiza automaticamente ao escolher ou trocar a imagem.

## 8.0.29 - 2026-05-09

- Corrigidos campos e seletores que ainda apareciam com cantos quadrados na aba Marca.
- Ajustado o subcontrole da seta dos seletores para preservar o formato pílula.

## 8.0.28 - 2026-05-09

- Corrigidos defeitos visuais nos cantos da tabela de frases da intro.
- Centralizados os botões da aba de frases da intro.
- Centralizado o conteúdo das abas da coluna direita e ajustadas larguras para leitura mais harmônica.

## 8.0.27 - 2026-05-09

- Padronizada a altura de campos de texto, seletores, campos numéricos e botões.
- Ajustado o botão `Abrir pasta` para preencher a largura do card de saída.

## 8.0.26 - 2026-05-09

- Definida a normalização de loudness como ativa por padrão.
- Aplicados os valores padrão do YouTube: `-14 LUFS` e `-1 dBTP`.
- Adicionada migração para corrigir configurações antigas salvas com normalização desligada e valores zerados.

## 8.0.25 - 2026-05-09

- Corrigido artefato visual no topo dos botões em formato pílula.
- Ajustadas as abas da coluna direita para remover a borda azul clara e escurecer abas inativas.
- Igualado o fundo interno das abas à cor da interface.

## 8.0.24 - 2026-05-09

- Corrigido o teste de 30 segundos para aceitar imagem estática como mídia visual base.
- Corrigida a opção do FFmpeg para carregar o filtro complexo por arquivo.

## 8.0.23 - 2026-05-09

- Corrigido o desenho dos botões para garantir formato pílula em toda a interface.

## 8.0.22 - 2026-05-09

- Simplificado o título da área central para `Preview`.
- Ajustado o preview de vídeo para usar fundo preto e bordas retas.
- Igualada a cor da área interna do preview ao card da interface.

## 8.0.21 - 2026-05-09

- Renomeado o aplicativo e a documentação para `TAURUS Video Maker`.
- Aplicado visual mais arredondado em botões, campos, abas, cards e barra de progresso.
- Movido o som ambiente opcional para a aba Áudio.
- Movida a opção de GPU NVIDIA/NVENC para a coluna esquerda e removida a aba Render.
- Removido o rótulo de status da área inferior; a barra de progresso agora ocupa a largura disponível.

## 8.0.20 - 2026-05-09

- Removido o botão `Exemplo` da aba de frases da intro e a lógica associada.

## 8.0.19 - 2026-05-09

- Removida a numeração da coluna esquerda para adequar a UI ao modelo de editor, não mais a passos sequenciais.

## 8.0.18 - 2026-05-09

- Aumentada a largura da coluna de ajustes para evitar truncamento em abas e controles.
- Reduzida a largura dos botões pequenos da aba Intro para acomodar ações lado a lado sem cortar texto.

## 8.0.17 - 2026-05-09

- Corrigido o preview central para não cobrir textos e marca d'água ao redesenhar a borda da área do vídeo.

## 8.0.16 - 2026-05-09

- Aumentada a largura inicial e mínima da janela para priorizar a área central.
- Reduzidas levemente as colunas laterais e os botões de ação para evitar truncamento nos controles centrais.

## 8.0.15 - 2026-05-09

- Refeita a interface como editor em três colunas: fluxo de arquivos, preview central e ajustes em abas.
- Removidas páginas com rolagem; opções densas foram divididas em abas internas, principalmente na Intro.
- Adicionado preview em tempo real usando o primeiro frame da mídia visual e sobreposições de títulos, intro e marca d'água.
- Padronizados botões, campos, seletores, toggles e espaçamentos com paleta azul noite, azul claro e cinza.

## 8.0.14 - 2026-05-09

- Restaurados na página Intro os controles avançados que já existiam no backend para frases iniciais.
- Organizadas as opções da intro em grupos próprios para evitar mistura com Títulos, Watermark e Avançado.
- Ligados os novos campos da intro ao salvamento e carregamento da configuração.
- Restaurados os botões de salvar e carregar presets da intro.

## 8.0.13 - 2026-05-09

- Substituído o seletor visual de fontes por uma lista compacta com nomes das fontes do sistema.
- Limitada a quantidade de itens visíveis no seletor de fontes para evitar que a lista saia da interface.
- O campo hexadecimal de cor agora exibe o texto na própria cor selecionada e atualiza ao editar ou escolher uma nova cor.

## 8.0.12 - 2026-05-09

- Renomeado o campo da intro para `Música começa após`, deixando claro que ele atrasa a entrada da música principal.
- Adicionada indicação visual de seta azul nos seletores, incluindo o seletor de fontes.

## 8.0.11 - 2026-05-09

- Ajustado o carregamento de fontes da interface para usar a lista nativa do Qt quando disponível.
- Mantida a varredura manual de fontes apenas como fallback, evitando avisos de DirectWrite com arquivos de fonte não suportados.

## 8.0.10 - 2026-05-09

- Renomeado `LoFi_VideoMaker.py` para `engine.py`.
- Renomeado `VM.py` para `VideoMaker.py`.
- Separada a arquitetura para manter o backend de renderização em `engine.py` e a interface em `VideoMaker.py`.
- Atualizado o empacotamento para usar `VideoMaker.py` como ponto de entrada.
- Atualizada a documentação para refletir a nova estrutura.

## 8.0.9 - 2026-05-09

- Criados subcards no passo 3 para separar edição e testes antes de renderizar.
- Removido o antigo card 4 de andamento.
- Movida a barra de andamento para baixo do log.
- Reorganizados os controles inferiores: opções de log/configuração à esquerda e ações de render à direita.
- Transformado o botão principal em controle único de iniciar, pausar e retomar.
- Movido o botão de abrir pasta de saída para o passo 1.

## 8.0.8 - 2026-05-09

- Criados subcards no passo 2 para agrupar as opções de fade in e fade out.

## 8.0.7 - 2026-05-09

- Reduzida a margem superior dos cards para aproximar os títulos do topo.
- Criado um subcard mais escuro no passo 1 para agrupar as opções de som de fundo.
- Reorganizado o som de fundo em duas linhas: título e volume na primeira; caminho, escolher e limpar na segunda.

## 8.0.6 - 2026-05-09

- Alinhados os campos de caminho do passo 1 com largura consistente.
- Reposicionados o slider de volume e o botão de limpar som de fundo como controles secundários à direita do som de fundo.
- Refinado o slider de volume para usar o mesmo azul dos toggles, com bolinha circular menor.
- Removido o botão "Usar pasta do script".
- Alterado o padrão de saída vazia para criar uma subpasta `render_AAAA-MM-DD_HH-MM-SS` ao lado do script.
- Ajustado "Abrir pasta de saída" para abrir a pasta do último vídeo gerado quando a saída automática estiver em uso.

## 8.0.5 - 2026-05-09

- Refeito o visual do slider de volume do som de fundo em estilo pílula.
- Alterada a bolinha do slider para azul.
- Mantido o slider sempre clicável, mesmo antes de selecionar o arquivo de som de fundo.

## 8.0.4 - 2026-05-09

- Ajustado o slider de volume do som de fundo para aceitar apenas múltiplos de 10%.

## 8.0.3 - 2026-05-09

- Aumentada a altura dos cards dos passos 1 e 2 para acomodar melhor os controles lado a lado.
- Movido o volume do som de fundo para o passo 1.
- Substituído o controle numérico de volume do som de fundo por um slider percentual.
- Adicionado botão para mostrar ou esconder o log.

## 8.0.2 - 2026-05-09

- Reorganizado o layout principal para mostrar os passos 1 e 2 lado a lado.
- Mantida a ordem vertical dos passos 3 e 4, log e controles.

## 8.0.1 - 2026-05-09

- Ocultadas as janelas de console abertas por chamadas internas ao FFmpeg e FFprobe.
- Mantido o controle de processo usado para pausa, cancelamento e encerramento de renderizações.
- Documentado o comportamento esperado para execução como `.pyw` e para o executável futuro.

## 2026-05-09

- Registrada a versão atual do script como `8.0.0`.
- Renomeado o ponto de entrada de `lofi_videomaker_v8.py` para `LoFi_VideoMaker.py`.
- Documentada a política de avanço de versão para `8.0.1`, `8.0.2` e versões futuras.
- Criada a estrutura inicial do repositório.
- Adicionados README, documentação detalhada, histórico de mudanças, licença, dependências, avisos de terceiros e arquivos de preparação para empacotamento.
- Copiada uma versão local do FFmpeg para `ffmpeg/bin/`.
- Ajustado o aplicativo para usar `ffmpeg.exe` e `ffprobe.exe` locais.
- Removido o `start.bat`; o ponto de entrada passa a ser o script Python.
- Preparado o código para funcionar futuramente como executável empacotado.
- Passado o rastreamento dos binários do FFmpeg para Git LFS.
