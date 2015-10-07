Trabalho de Simande
===================

Objetivo: simular o funcionamento de um supermercado a fim de se obter medidas
de desempenho do sistema.  Ao encerrar a simulação, informar a fila média e
máxima em cada caixa, o tempo médio de permanência no supermercado, o número
mínimo de caixas para que as filas não ultrapassem 5 pessoas.

Dados:

- o supermercado funciona 8 horas por dia e tem `n > 2` caixas
- chegada dos clientes é Poisson de média 10 por minuto
- tempo de atendimento no caixa é Uniforme entre 2 e 6 minutos
- tempo de compra de cada cliente é Uniforme entre 30 e 90 minutos

Entregar:

- código fonte
- programa executável
- linha de comando: `./<nome_do_programa> <nr_caixas>`
- saída: medidas solicitadas
- mostrar resultados para: `nr_caixas < n*`, `nr_caixas = n*` e `nr_caixas > n*`
- arguição individual sobre a simulação
