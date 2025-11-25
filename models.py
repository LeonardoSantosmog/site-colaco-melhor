import sqlite3
import os
from datetime import datetime

class Database:
    def __init__(self, db_path='escola_colaco.db'):
        self.db_path = db_path
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Inicializa o banco de dados com todas as tabelas"""
        if not os.path.exists(self.db_path):
            conn = self.get_connection()
            
            # Tabela de usuários
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    tipo TEXT NOT NULL CHECK(tipo IN ('admin', 'professor', 'aluno')),
                    email TEXT,
                    telefone TEXT,
                    endereco TEXT,
                    data_nascimento DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ativo BOOLEAN DEFAULT 1
                )
            ''')
            
            # Tabela de notícias
            conn.execute('''
                CREATE TABLE IF NOT EXISTS noticias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT NOT NULL,
                    conteudo TEXT NOT NULL,
                    imagem TEXT,
                    data_publicacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    autor_id INTEGER,
                    destaque BOOLEAN DEFAULT 0,
                    FOREIGN KEY (autor_id) REFERENCES users (id)
                )
            ''')
            
            # Tabela de disciplinas
            conn.execute('''
                CREATE TABLE IF NOT EXISTS disciplinas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    descricao TEXT,
                    professor_id INTEGER,
                    carga_horaria INTEGER,
                    FOREIGN KEY (professor_id) REFERENCES users (id)
                )
            ''')
            
            # Tabela de matrículas
            conn.execute('''
                CREATE TABLE IF NOT EXISTS matriculas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aluno_id INTEGER,
                    disciplina_id INTEGER,
                    data_matricula TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'ativo',
                    FOREIGN KEY (aluno_id) REFERENCES users (id),
                    FOREIGN KEY (disciplina_id) REFERENCES disciplinas (id),
                    UNIQUE(aluno_id, disciplina_id)
                )
            ''')
            
            # Inserir dados iniciais
            self._insert_initial_data(conn)
            
            conn.commit()
            conn.close()
            print("✅ Banco de dados inicializado com sucesso!")
    
    def _insert_initial_data(self, conn):
        """Insere dados iniciais para teste"""
        # Administrador
        conn.execute(
            "INSERT OR IGNORE INTO users (nome, username, password, tipo, email) VALUES (?, ?, ?, ?, ?)",
            ('Administrador Escola Colaço', 'admin', 'admin123', 'admin', 'admin@escolacolaco.com')
        )
        
        # Professores
        conn.execute(
            "INSERT OR IGNORE INTO users (nome, username, password, tipo, email) VALUES (?, ?, ?, ?, ?)",
            ('Professor João Silva', 'profjoao', 'prof123', 'professor', 'joao.silva@escolacolaco.com')
        )
        
        conn.execute(
            "INSERT OR IGNORE INTO users (nome, username, password, tipo, email) VALUES (?, ?, ?, ?, ?)",
            ('Professora Maria Santos', 'promaria', 'prof123', 'professor', 'maria.santos@escolacolaco.com')
        )
        
        # Alunos de exemplo
        alunos = [
            ('Ana Carolina Oliveira', 'ana2024', 'aluno123', 'aluno', 'ana.oliveira@email.com'),
            ('Bruno Mendes', 'bruno2024', 'aluno123', 'aluno', 'bruno.mendes@email.com'),
            ('Carla Rodrigues', 'carla2024', 'aluno123', 'aluno', 'carla.rodrigues@email.com')
        ]
        
        for nome, username, password, tipo, email in alunos:
            conn.execute(
                "INSERT OR IGNORE INTO users (nome, username, password, tipo, email) VALUES (?, ?, ?, ?, ?)",
                (nome, username, password, tipo, email)
            )
        
        # Disciplinas
        disciplinas = [
            ('Matemática', 'Matemática Básica e Avançada', 2, 80),
            ('Português', 'Língua Portuguesa e Literatura', 3, 60),
            ('História', 'História do Brasil e Geral', 2, 40),
            ('Ciências', 'Ciências Naturais', 3, 60)
        ]
        
        for nome, descricao, professor_id, carga_horaria in disciplinas:
            conn.execute(
                "INSERT OR IGNORE INTO disciplinas (nome, descricao, professor_id, carga_horaria) VALUES (?, ?, ?, ?)",
                (nome, descricao, professor_id, carga_horaria)
            )
        
        # Notícias iniciais
        noticias = [
            ('Início do Ano Letivo 2024', 'Com grande alegria informamos o início do ano letivo de 2024 na Escola Colaço. Sejam todos bem-vindos!', 1),
            ('Olimpíada de Matemática', 'Inscrições abertas para a Olimpíada de Matemática. Participe!', 2),
            ('Reunião de Pais', 'Convocamos todos os pais para reunião importante no próximo sábado.', 1)
        ]
        
        for titulo, conteudo, autor_id in noticias:
            conn.execute(
                "INSERT OR IGNORE INTO noticias (titulo, conteudo, autor_id, destaque) VALUES (?, ?, ?, ?)",
                (titulo, conteudo, autor_id, 1 if titulo == 'Início do Ano Letivo 2024' else 0)
            )