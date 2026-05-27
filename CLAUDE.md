# Extraindo Informações da Fatura de Cartão de Crédito do Itaú

O banco Itaú disponibiliza faturas de cartão de crédito em formato PDF. Esse formato é complexo, e extratores de PDF tradicionais não conseguem extrair as informações de forma estruturada. Este projeto tem como objetivo extrair as informações de uma fatura de cartão de crédito do Itaú e transformá-las em um formato estruturado, como CSV.

## Tarefa

Você vai olhar a fatura em ./examples/fatura-02.pdf e construir um extrator determinístico, em Python. O objetivo é extrair o que foi gasto em cada cartão, quando, e qual o valor. Olhando a fatura em `fatura-02`, por exemplo, eu esperaria obter, para as três primeiras despesas:

```csv
cartão,data,descrição,categoria,valor,moeda
9690,HS PLAZA SUL 03/05,VESTUÁRIO .SAO PAULO,"119,95",BRL
9690,SAN MARINO PANIFICACA,ALIMENTAÇÃO .SAO PAULO,"8,50",BRL
9690,DELICIAS DO MOINHO,ALIMENTAÇÃo .SAO PAULO,"8,20",BRL
```

e assim por diante. Eu coloquei uma imagem de parte da fatura em `./examples/fatura-02-imagem.png` para te ajudar a entender a estrutura do documento - note que as despesas são colocadas em 2 colunas. No PDF você provavelmente não vai ver as três primeiras despesas aparecendo em sequência. Não tem problema se o extrator mudar a ordem das despesas, contanto que os dados de cada despesa esteja correto.

Na fatura exemplo temos dois cartões: 9690 e 1017. A fatura tem também seções separadas para lançamentos nacionais e internacionais, que são dados em dólar.

Você não precisa transcrever as seções após os detalhamentos de despesa; i.e., os "Compras parceladas - próximas faturas", ou "Simulação de Compras parc. c/ juros e Crediário (próximo período)", ou "Simulação Saque Cash", ou "Demais Taxas de Juros próximo período", ou "Encargos cobrados nesta fatura". Tudo o que vier depois da última compra pode ser ignorado.

## Método de Desenvolvimento

Use TDD (Test-Driven Development) para desenvolver o extrator. Crie testes que validem a extração de dados de uma fatura de cartão de crédito do Itaú. Os testes devem ser escritos em Python e usar a biblioteca `pytest`. O extrator deve ser determinístico, ou seja, deve sempre retornar os mesmos resultados para a mesma fatura.

## Virtualenv

Eu criei um ambiente conda para você usar, chamado extrator. Se precisar criar um shell, sempre ative o venv com `conda activate extrator`.

