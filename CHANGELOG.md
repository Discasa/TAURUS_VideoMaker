# Histórico de Mudanças

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
