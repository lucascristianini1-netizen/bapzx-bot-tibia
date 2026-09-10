# MEMORIA COMPRA - Regra de calculo de preco de Tibia Coins

Regra oficial de calculo usada no bot e na IA para converter quantidade de
Tibia Coins em valor em Reais.

## Formula base

Sempre que alguem pedir para calcular o valor de uma quantidade de TC com
base na proporcao de que 1.000 TC custam R$ 90, utilizar a seguinte formula:

    valor = quantidade x 90 / 1000

Mostrar o calculo passo a passo e o valor final em Reais.

## Passo a passo (exemplo com 700 TC)

1. Quantidade desejada: 700 TC
2. Multiplicar a quantidade por 90: 700 x 90 = 63.000
3. Dividir por 1.000: 63.000 / 1.000 = 63
4. Valor final: R$ 63,00

Outros exemplos:
- 500 TC = 500 x 90 / 1.000 = R$ 45,00
- 1.000 TC = 1.000 x 90 / 1.000 = R$ 90,00
- 800 TC = 800 x 90 / 1.000 = R$ 72,00
- 1.500 TC = 1.500 x 90 / 1.000 = R$ 135,00

## Regra de prioridade

- Quantidades que existem na Tabela de Precos oficial (bot.py, dicionario
  PRICES: 100, 250, 500, 1.000 e 2.500 TC) usam o valor da tabela.
- Qualquer outra quantidade usa a forma base acima (quantidade x 90 / 1.000).

## Onde esta aplicada

1. Prompt da IA (bot.py -> ask_ai): responde precos fora da tabela com a
   forma, mostrando o calculo passo a passo.
2. Registro do pedido (bot.py -> calc_price, usado em extract_order_details):
   grava o preco calculado mesmo para quantidades fora da tabela.
3. Este arquivo funciona como memoria do projeto junto com o MEMORIA.md.