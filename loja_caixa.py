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
        funcionario_id INTEGER,
        aberto_em TEXT,
        fechado_em TEXT,
        FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id)
    )
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
        FOREIGN KEY (caixa_id) REFERENCES caixa(id),
        FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id)
    )
    """)

    # itens de cada venda (produtos, quantidade, preço unitário)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vendas_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id INTEGER,
        produto_id INTEGER,
        quantidade INTEGER,
        preco_unit REAL,
        FOREIGN KEY (venda_id) REFERENCES vendas(id),
        FOREIGN KEY (produto_id) REFERENCES produtos(id)
    )
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
    senha = getpass.getpass("Senha: ").strip()
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
    nome = input("Digite o nome do produto: ").strip()
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
    cur.execute("SELECT id FROM caixa WHERE fechado_em IS NULL")
    caixa_aberto = cur.fetchone()
    if caixa_aberto:
        print(f"Já existe um caixa aberto (id{caixa_aberto[0]}). Feche antes de abrir outro.\n")
        return caixa_aberto[0] # Retorna o id do caixa existente
    
    aberto_em = datetime.now().isoformat(sep=' ', timespec='seconds')
    cur.execute("INSERT INTO caixa (funcionario_id, aberto_em) VALUES (?, ?)", (funcionario_id, aberto_em))
    conn.commit()
    caixa_id = cur.lastrowid
    print(f"Caixa aberto (id{caixa_id}) às {aberto_em}\n")
    return caixa_id

def fechar_caixa(cur, conn, caixa_id):

    if caixa_id is None:
        print("Nenhum caixa aberto para fechar.\n")
        return
    
    fechado_em = datetime.now().isoformat(sep=' ', timespec='seconds')

    cur.execute("UPDATE caixa SET fechado_em = ? WHERE id = ?", (fechado_em, caixa_id))
    conn.commit()
    print(f"Caixa {caixa_id} fechado em {fechado_em}\n")

    gerar_relatorio_caixa(cur, caixa_id)

    return None

def realizar_vendas(cur, conn, caixa_id, funcionario_id):
    if caixa_id is None:
        print("Abra o caixa antes de realizar as vendas.\n")
        return
    
    
    itens = []
    while True:
         lista_produtos(cur)
         pid = input("Digite o ID do produto (ou ENTER para  finalizar): ").strip()
         if pid == "":
            break
         try:
            pid = int(pid)
         except ValueError:
            print("ID inválido.")
            continue
         
         cur. execute("SELECT nome, preco, estoque FROM  produtos WHERE id = ?", (pid,))
         p = cur.fetchone()
         if not p:
             print("Produto não encontrado.")
             continue
         
         nome_prod, preco_unit, estoque = p
         print(f"Produto selecionado: {nome_prod}")
         
         try:
          qtd = int(input(f"Quantidade (estoque {estoque}: )").strip())
         except ValueError:
          print("Qunatidade inválida. Digite um número.")
          continue
          
         if qtd <= 0 or qtd > estoque:
            print("Quantidade deve ser maior que zero.")
            continue      
         
         itens.append((pid, qtd, preco_unit))

    if not itens:
            print("Venda cancelada (nenhum item).\n")
            return
        
        # calcular totais
    total_bruto = sum(qtd * preco for _, qtd, preco in itens)
    total_sem_imposto = total_bruto / (1 + TAXA_RATE)
    total_imposto = total_bruto - total_sem_imposto
    vendido_em = datetime.now().isoformat(sep=' ', timespec='seconds')

        # Inserir venda
    cur.execute("""
        INSERT INTO vendas (caixa_id, funcionario_id, total_bruto, total_sem_imposto, total_imposto,vendido_em)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (caixa_id, funcionario_id, total_bruto, total_sem_imposto, total_imposto, vendido_em))
    venda_id = cur.lastrowid

        # inserir itens e reduzir estoque
    for (pid, qtd, preco_unit) in itens:
            cur.execute("INSERT INTO vendas_itens (venda_id, produto_id, quantidade, preco_unit) VALUES (?, ?, ?, ?)", (venda_id, pid, qtd, preco_unit))

            # Atualizar estoque
            cur.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", (qtd, pid))
        
    conn.commit()
    print(f"Venda registrada (id{venda_id}) - Total R$ {total_bruto:.2f} (imposto R$ {total_imposto:.2f})\n")

        # Relatorio

def gerar_relatorio_caixa(cur, caixa_id):
    # Informação do caixa
    cur.execute("SELECT funcionario_id, aberto_em, fechado_em FROM caixa WHERE id = ?", (caixa_id,))
    caixa = cur.fetchone()
    if not caixa:
        print("Caixa não encontrado.\n")
        return
    
    funcionario_id, aberto_em, fechado_em = caixa

    print(f"Funcionaro que icerrou o caixa: {funcionario_id}")

    # Total do caixa (vendas)
    cur.execute("""
        SELECT SUM(total_bruto), SUM(total_sem_imposto), SUM(total_imposto)
        FROM vendas
        WHERE caixa_id = ?
    """, (caixa_id,))
    sums = cur.fetchone() 
    total_bruto, total_sem_imposto, total_imposto = sums if sums and sums[0] is not None else (0.0, 0.0, 0.0)

    # Vedas por funcionario no caixa
    cur.execute("""
        SELECT f.nome, COUNT(v.id), SUM(v.total_bruto) FROM vendas v JOIN funcionarios f ON v.funcionario_id = f.id
        WHERE v.caixa_id = ?
        GROUp BY f.id
    """, (caixa_id,))
    por_func = cur.fetchall()

    print("=== RELATÓRIO DO CAIXA ===")
    print(f"Caixa id: {caixa_id}")
    print(f"Aberto em: {aberto_em}")
    print(f"Fechado em: {fechado_em}")
    print(f"Total bruto: R${total_bruto:.2f}")
    print(f"Total sem imposto: R${total_sem_imposto:.2f}")
    print(f"Total imposto: R${total_imposto:.2f}")
    print("\nVendas por funcionário: ")
    for nome, cnt, soma in por_func:
            print(f"- {nome}: {cnt} vendas -- totalR$ {soma:.2f}")
    print("=" * 30)

    # Menu pricipal

def main_menu():
 
        conn, cur = init_db()
        caixa_id = None
        current_user = None

        while True:
            print("-" * 30)
            print("=== Lojá - Sistema de Caixa ===")
            print("1- Cadastrar funcionario")
            print("2- Login")
            print("3- Cadastra produto")
            print("4- Listar produtos")
            print("5- Abrir Caixa")
            print("6- Realizar venda")
            print("7- Fechar caixa")
            print("8- Sair")
            choice = input("Escolher: ").strip()

            if choice == "1":
                cadastrar_funcionario(cur, conn)
            elif choice == "2":
                user = login(cur)
                if user:
                    current_user = user
            elif choice == "3":
                if current_user:
                    cadastrar_produtos(cur, conn)
                else:
                    print("Faça login como funcionario antes.\n")
            elif choice == "4":
                lista_produtos(cur)
            elif choice == "5":
                if current_user:
                    caixa_id = abrir_caixa(cur, conn, current_user["id"])
                else:
                    print("Faça login para abrir o caixa.\n")
            elif choice == "6":
                if current_user:
                    realizar_vendas(cur , conn, caixa_id, current_user["id"])
                else:
                    print("Faça login para realizar venda.\n")
            elif choice == "7":
                if current_user: # Qual quer um funcionario pode fechar o caixa
                    caixa_id = fechar_caixa(cur, conn, caixa_id)
                else:
                    print("Faça login para feichar o caixa.\n")
            elif choice == "8":
                print("Saindo...")
                conn.close()
                break
            else: 
                print("Opção invalida. Tente novamente.")
            

if __name__ == "__main__":  
 main_menu()  