"""
Loja simples (CLI) com SQLite
Funcionalidades:
- Cadastro/login de funcionários
- Cadastro/lista de produtos (com estoque)
- Abrir/fechar caixa (session)
- Registrar vendas (cada venda tem itens)
- Relatório diário ao fechar caixa: total bruto, total sem imposto, total imposto,
  vendas por funcionário, hora abertura/fechamento
Uso: python loja_caixa.py

""" 

import sqlite3
from datetime import datetime
import getpass

DB_FILE = "Loja.db"
TAXA_RATE = 0.12 # 12% de imposto (Opção Ajustavel)

# Iniciando do DB

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Tabela de funcionarios
    cur.execute("""
    CREATE TABLE IF NOT EXISTS funcionarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cpf TEXT NOT NULL UNIQUE,
        senha TEXT NOT NULL
    )
    """)

    # Tabela de produtos
    cur.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        preco REAL NOT NULL,
        estoque INTEGER NOT NULL
    )
    """)


    # sessões de caixa (quando abriu, quem abriu, quando fechou)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS caixa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        funcionario_id PRIMARY KEY AUTOINCREMENT,
        aberto_em TEXT,
        fechado_em TEXT,
        FOREING KEY (funcionario_id) REFERENCES funcionarios(id))
    """)

    # vendas: cada venda pertence a um caixa e a um funcionario
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        caixa_id INTEGER,
        funcionario_id INTEGER,
        total_bruto REAL,
        total_sem_imposto REAL,
        total_imposto REAL,
        vendido_em TEXT,
        FOREIGN KEY (caixa id) REFERENCES caixa(id),
        FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id))
    """)

    # itens de cada venda (produtos, quantidade, preço unitário)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vendas_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendas_id INTEGER,
        produto_id INTEGER,
        quantidade INTEGER,
        preco_unit REAL,
        FOREING KEY (venda_id) REFERENCES vendas(id),
        FOREINGN KEY (produto_id) REFERENCES produtos(id))
    """)

    conn.commit()
    return conn, cur

# Autenticação

def cadastrar_funcionario(cur, conn):
    print("\n=== Cadastrar Funcionário ===")
    nome = input("Nome:").strip()
    cpf = input("CPF (somente números): ").strip()
    senha = getpass.getpass("Senha (não aparecerá): ").strip()

    try:
        cur.execute("INSERT INTO funcionarios (nome, cpf, senha) VALUES (?, ?, ?)", (nome, cpf, senha)) 
        conn.commit()
        print("Funcionário cadastrado com sucesso.\n")
    except sqlite3.IntegrityError:
        print("CPF já cadastrado. Tente outro.\n")

def login(cur):
    print("\n== Login ==")
    cpf = input("CPF: ").strip()
    senha = getpass.getpass("Senha: ").strip
    cur.execute("SELECT id, nome FROM funcionarios WHERE cpf = ? AND senha = ?", (cpf, senha))
    user = cur.fetchone()
    if user:
        print(f"Login bem-sucedido. Bem vindo, {user[1]}!\n")
        return {"id": user[0], "nome": user[1]}

    else:
        print("CPf ou senha incorretos.\n")
        return None
    
# Produtos

def cadastrar_produtos(cur, conn):
    print("\n=== Cadastrar Produto ===")
    nome = input("Digite o nome do produto: ").strip
    preco = float(input("Preço (Utilize ponto . para decimais: )").strip())
    estoque = int(input("Quantidade em estoque: ").strip())
    cur.execute("INSERT INTO produtos (nome, preco, estoque) VALUES (?, ?, ?)", (nome, preco, estoque))
    conn.commit()
    print("Produto cadastrado.\n")

def lista_produtos(cur):
    cur.execute("SELECT id, nome, preco, estoque FROM produtos")
    rows = cur.fetchall()
    if not rows:
        print("Nenhum produto cadastrado.\n")
        return
    print("\n== Produtos ==")
    for r in rows:
        print(f"ID: {r[0]} --- {r[1]} --- R$ {r[2]:2f} --- Estoque: {r[3]}")
        print("")

# Caixa (abrir / fechar)

def abrir_caixa(cur, conn, funcionario_id):
    # Só é permitido abrir se não houver caixa aberta (sem colsed timestamp)
    cur.execute("SELECT id FROM caixa WHERE fechado_em IS NULL")
    if cur.fetchone():
        print("Já existe um caixa aberto. Feche antes de abrir outro.\n")
        return None
    aberto_em = datetime.now().isoformat(sep=' ', timespec='seconds')
    cur.execute("INSERT INTO caixa (funcionarios_id, aberto_em) VALUES (?, ?)", (funcionario_id, aberto_em))
    conn.commit()
    caixa_id = cur.lastrowid
    print(f"Caixa aberto (id {caixa_id}) às {aberto_em}\n")
    return caixa_id

def fechar_caixa(cur, conn, caixa_id):
    if caixa_id is None:
        print("Nenhum caixa aberto para feichar.\n")
        return
    fechado_em = datetime.now().isoformat(sep=' ', timespec='seconds')
    cur.execute("UPDATE caixas SET fechado_em = ? WHERE id = ?", (fechado_em, caixa_id))
    conn.commit()
    print(f"Caixa {caixa_id} fechado em {fechado_em}\n")
    # Ao fechar, gerar relatório do caixa
    gerar_relatorio_caixa(cur, caixa_id)
    return None


# Vendas

def vendas():
    