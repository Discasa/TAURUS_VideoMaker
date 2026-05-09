# Histórico de Mudanças

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
