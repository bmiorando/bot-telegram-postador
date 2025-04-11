from telethon import TelegramClient
from telethon.tl.types import Message
import asyncio
import json
import os
from datetime import datetime, timedelta

# === CONFIGURAÇÕES DO TELEGRAM ===
api_id = 26158822
api_hash = '3a68d73a35c113ae6e5a4a01cd6c3b52'

# === LINKS DOS CANAIS ===
canal_estoque = 'https://t.me/+HRd8kJ8Pw3ViODAx'
canal_destino = 'https://t.me/principaldalala'

# === CONFIGURAÇÕES DE POSTAGEM ===
horarios_postagem = ['22:10', '22:12', '22:14', '22:16', '22:18']
qtd_por_dia = len(horarios_postagem)
arquivo_ids = 'publicados.json'
arquivo_fila = 'fila_postagens.json'

client = TelegramClient('sessao_postador', api_id, api_hash)

# === UTILITÁRIOS ===
def carregar_json(caminho):
    if os.path.exists(caminho):
        with open(caminho, 'r') as f:
            return json.load(f)
    return []

def salvar_json(caminho, dados):
    with open(caminho, 'w') as f:
        json.dump(dados, f)

# === PREPARAÇÃO DA FILA DIÁRIA ===
async def preparar_fila_do_dia():
    publicados = carregar_json(arquivo_ids)
    fila_atual = carregar_json(arquivo_fila)

    if len(fila_atual) >= qtd_por_dia:
        return  # Fila já pronta

    fila_nova = []
    grupos = {}
    mensagens = []

    async for msg in client.iter_messages(canal_estoque):
        mensagens.append(msg)

    mensagens = sorted(mensagens, key=lambda m: m.id)

    for msg in mensagens:
        if msg.id in publicados:
            continue
        gid = getattr(msg, 'grouped_id', None)
        if gid:
            if gid not in grupos:
                grupos[gid] = []
            grupos[gid].append(msg)
        else:
            fila_nova.append([msg])

        if len(fila_nova) + len(grupos) >= qtd_por_dia:
            break

    fila_final = fila_nova + list(grupos.values())
    fila_final = fila_final[:qtd_por_dia]

    fila_ids = [[m.id for m in grupo] for grupo in fila_final]
    salvar_json(arquivo_fila, fila_ids)

# === POSTAGEM INDIVIDUAL — AGORA COM ENCAMINHAMENTO ===
async def postar_mensagem_do_horario(horario_atual):
    fila = carregar_json(arquivo_fila)
    publicados = carregar_json(arquivo_ids)

    idx = horarios_postagem.index(horario_atual) if horario_atual in horarios_postagem else -1
    if idx == -1 or idx >= len(fila):
        print(f"[{horario_atual}] Nenhuma mensagem programada.")
        return

    grupo_ids = fila[idx]

    # Verifica se todos os IDs da fila existem
    mensagens_validas = []
    for mid in grupo_ids:
        try:
            msg = await client.get_messages(canal_estoque, ids=mid)
            if msg:
                mensagens_validas.append(mid)
        except:
            continue

    if not mensagens_validas:
        print(f"⚠️ [{horario_atual}] Nenhuma mensagem válida encontrada para encaminhar.")
        return

    try:
        await client.forward_messages(
            canal_destino,
            messages=mensagens_validas,
            from_peer=canal_estoque
        )
        print(f"✅ [{horario_atual}] Postado via encaminhamento!")
        publicados.extend(mensagens_validas)
        salvar_json(arquivo_ids, publicados)
    except Exception as e:
        print(f"❌ [{horario_atual}] Erro ao encaminhar: {e}")

# === AGENDAMENTO ===
async def agendador():
    await preparar_fila_do_dia()
    print("🤖 Fila do dia preparada.")

    while True:
        # Ajusta o horário para UTC-3 (Brasil)
        hora_brasil = (datetime.utcnow() - timedelta(hours=3)).strftime('%H:%M')
        if hora_brasil in horarios_postagem:
            await postar_mensagem_do_horario(hora_brasil)
            await asyncio.sleep(60)
        await asyncio.sleep(10)

# === EXECUÇÃO ===
async def main():
    await client.start()
    print("🤖 Bot iniciado e aguardando horários programados...")
    await agendador()

client.loop.run_until_complete(main())
