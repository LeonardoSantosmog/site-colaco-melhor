from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify
import sqlite3 as sql
import os
from datetime import datetime
from models import Database

app = Flask(__name__)
app.secret_key = 'escola_colaco_secret_key_2024'
app.config['DATABASE'] = 'escola_colaco.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB

# Inicializar banco de dados
db_manager = Database(app.config['DATABASE'])

def get_db():
    return db_manager.get_connection()

# Context processor - disponibiliza variáveis para todos os templates
@app.context_processor
def inject_user():
    return dict(
        current_user=session.get('nome'),
        user_tipo=session.get('tipo'),
        current_year=datetime.now().year
    )

# Filtro personalizado para formatar datas
@app.template_filter('format_date')
def format_date(value, format='%d/%m/%Y'):
    if isinstance(value, str):
        return value
    return value.strftime(format)

# Rotas Públicas
@app.route("/")
def index():
    """Página inicial da escola"""
    conn = get_db()
    
    # Notícias em destaque
    noticias_destaque = conn.execute('''
        SELECT n.*, u.nome as autor_nome 
        FROM noticias n 
        LEFT JOIN users u ON n.autor_id = u.id 
        WHERE n.destaque = 1
        ORDER BY n.data_publicacao DESC 
        LIMIT 3
    ''').fetchall()
    
    # Total de alunos e professores
    total_alunos = conn.execute("SELECT COUNT(*) FROM users WHERE tipo = 'aluno' AND ativo = 1").fetchone()[0]
    total_professores = conn.execute("SELECT COUNT(*) FROM users WHERE tipo = 'professor' AND ativo = 1").fetchone()[0]
    
    conn.close()
    
    return render_template("index.html", 
                         noticias=noticias_destaque,
                         total_alunos=total_alunos,
                         total_professores=total_professores)

@app.route("/sobre")
def sobre():
    """Página sobre a escola"""
    return render_template("sobre.html")

@app.route("/contato", methods=["GET", "POST"])
def contato():
    """Página de contato"""
    if request.method == "POST":
        nome = request.form.get('nome')
        email = request.form.get('email')
        mensagem = request.form.get('mensagem')
        
        # Aqui você pode integrar com um serviço de email
        flash("Mensagem enviada com sucesso! Entraremos em contato em breve.", "success")
        return redirect(url_for('contato'))
    
    return render_template("contato.html")

@app.route("/noticias")
def noticias():
    """Página de notícias"""
    conn = get_db()
    noticias_list = conn.execute('''
        SELECT n.*, u.nome as autor_nome 
        FROM noticias n 
        LEFT JOIN users u ON n.autor_id = u.id 
        ORDER BY n.data_publicacao DESC
    ''').fetchall()
    conn.close()
    
    return render_template("noticias.html", noticias=noticias_list)

@app.route("/noticia/<int:noticia_id>")
def noticia_detalhe(noticia_id):
    """Página de detalhe da notícia"""
    conn = get_db()
    noticia = conn.execute('''
        SELECT n.*, u.nome as autor_nome 
        FROM noticias n 
        LEFT JOIN users u ON n.autor_id = u.id 
        WHERE n.id = ?
    ''', (noticia_id,)).fetchone()
    conn.close()
    
    if not noticia:
        flash("Notícia não encontrada.", "error")
        return redirect(url_for('noticias'))
    
    return render_template("noticia_detalhe.html", noticia=noticia)

# Sistema de Autenticação
@app.route("/login", methods=["GET", "POST"])
def login():
    """Página de login"""
    # Se já está logado, redireciona para a área apropriada
    if 'user_id' in session:
        if session['tipo'] in ['admin', 'professor']:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('area_aluno'))
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if not username or not password:
            flash("Preencha todos os campos.", "error")
        else:
            conn = get_db()
            user = conn.execute(
                "SELECT * FROM users WHERE username = ? AND ativo = 1", (username,)
            ).fetchone()
            conn.close()
            
            if user and user["password"] == password:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['tipo'] = user['tipo']
                session['nome'] = user['nome']
                session['email'] = user['email']
                
                flash(f"Bem-vindo(a), {user['nome']}!", "success")
                
                if user['tipo'] in ['admin', 'professor']:
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('area_aluno'))
            else:
                flash("Usuário ou senha inválidos.", "error")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    """Faz logout do usuário"""
    session.clear()
    flash("Logout realizado com sucesso.", "info")
    return redirect(url_for('index'))

# Middleware para verificar autenticação
def login_required(tipos_permitidos=None):
    if tipos_permitidos is None:
        tipos_permitidos = ['admin', 'professor', 'aluno']
    
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Você precisa fazer login para acessar esta página.", "error")
                return redirect(url_for('login'))
            
            if session['tipo'] not in tipos_permitidos:
                flash("Acesso não autorizado.", "error")
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Área do Aluno
@app.route("/area-aluno")
@login_required(['aluno'])
def area_aluno():
    """Área restrita do aluno"""
    conn = get_db()
    
    # Dados do aluno
    aluno = conn.execute(
        "SELECT * FROM users WHERE id = ?", (session['user_id'],)
    ).fetchone()
    
    # Matrículas do aluno
    matriculas = conn.execute('''
        SELECT d.nome, d.descricao, u.nome as professor_nome, m.data_matricula
        FROM matriculas m
        JOIN disciplinas d ON m.disciplina_id = d.id
        JOIN users u ON d.professor_id = u.id
        WHERE m.aluno_id = ? AND m.status = 'ativo'
    ''', (session['user_id'],)).fetchall()
    
    # Notícias recentes
    noticias_recentes = conn.execute('''
        SELECT n.*, u.nome as autor_nome 
        FROM noticias n 
        LEFT JOIN users u ON n.autor_id = u.id 
        ORDER BY n.data_publicacao DESC 
        LIMIT 5
    ''').fetchall()
    
    conn.close()
    
    return render_template("area_aluno.html", 
                         aluno=aluno, 
                         matriculas=matriculas,
                         noticias=noticias_recentes)

# Área Administrativa
@app.route("/admin")
@login_required(['admin', 'professor'])
def admin_dashboard():
    """Dashboard administrativo"""
    conn = get_db()
    
    # Estatísticas
    total_alunos = conn.execute("SELECT COUNT(*) FROM users WHERE tipo = 'aluno' AND ativo = 1").fetchone()[0]
    total_professores = conn.execute("SELECT COUNT(*) FROM users WHERE tipo = 'professor' AND ativo = 1").fetchone()[0]
    total_disciplinas = conn.execute("SELECT COUNT(*) FROM disciplinas").fetchone()[0]
    total_noticias = conn.execute("SELECT COUNT(*) FROM noticias").fetchone()[0]
    
    # Notícias recentes
    noticias_recentes = conn.execute('''
        SELECT n.*, u.nome as autor_nome 
        FROM noticias n 
        LEFT JOIN users u ON n.autor_id = u.id 
        ORDER BY n.data_publicacao DESC 
        LIMIT 5
    ''').fetchall()
    
    # Últimos alunos cadastrados
    ultimos_alunos = conn.execute('''
        SELECT * FROM users 
        WHERE tipo = 'aluno' 
        ORDER BY created_at DESC 
        LIMIT 5
    ''').fetchall()
    
    conn.close()
    
    return render_template("admin/dashboard.html",
                         total_alunos=total_alunos,
                         total_professores=total_professores,
                         total_disciplinas=total_disciplinas,
                         total_noticias=total_noticias,
                         noticias=noticias_recentes,
                         ultimos_alunos=ultimos_alunos)

# Gerenciamento de Alunos
@app.route("/admin/alunos")
@login_required(['admin', 'professor'])
def admin_alunos():
    """Lista de alunos"""
    conn = get_db()
    alunos = conn.execute('''
        SELECT * FROM users 
        WHERE tipo = 'aluno' 
        ORDER BY nome
    ''').fetchall()
    conn.close()
    
    return render_template("admin/alunos.html", alunos=alunos)

@app.route("/admin/alunos/cadastrar", methods=["GET", "POST"])
@login_required(['admin', 'professor'])
def cadastrar_aluno():
    """Cadastrar novo aluno"""
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        email = request.form.get("email", "").strip()
        telefone = request.form.get("telefone", "").strip()
        endereco = request.form.get("endereco", "").strip()
        data_nascimento = request.form.get("data_nascimento", "")
        
        if not nome or not username or not password:
            flash("Preencha todos os campos obrigatórios.", "error")
        else:
            conn = get_db()
            try:
                conn.execute('''
                    INSERT INTO users (nome, username, password, tipo, email, telefone, endereco, data_nascimento)
                    VALUES (?, ?, ?, 'aluno', ?, ?, ?, ?)
                ''', (nome, username, password, email, telefone, endereco, data_nascimento))
                conn.commit()
                conn.close()
                flash("Aluno cadastrado com sucesso!", "success")
                return redirect(url_for('admin_alunos'))
            except sql.IntegrityError:
                flash("Username já existe.", "error")
                conn.close()
    
    return render_template("admin/cadastrar_aluno.html")

@app.route("/admin/alunos/editar/<int:aluno_id>", methods=["GET", "POST"])
@login_required(['admin', 'professor'])
def editar_aluno(aluno_id):
    """Editar aluno existente"""
    conn = get_db()
    aluno = conn.execute(
        "SELECT * FROM users WHERE id = ? AND tipo = 'aluno'", (aluno_id,)
    ).fetchone()
    
    if not aluno:
        conn.close()
        flash("Aluno não encontrado.", "error")
        return redirect(url_for('admin_alunos'))
    
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        email = request.form.get("email", "").strip()
        telefone = request.form.get("telefone", "").strip()
        endereco = request.form.get("endereco", "").strip()
        data_nascimento = request.form.get("data_nascimento", "")
        ativo = request.form.get("ativo", "off") == "on"
        
        if not nome or not username:
            flash("Nome e usuário são obrigatórios.", "error")
        else:
            try:
                if password:
                    conn.execute('''
                        UPDATE users 
                        SET nome = ?, username = ?, password = ?, email = ?, telefone = ?, endereco = ?, data_nascimento = ?, ativo = ?
                        WHERE id = ?
                    ''', (nome, username, password, email, telefone, endereco, data_nascimento, ativo, aluno_id))
                else:
                    conn.execute('''
                        UPDATE users 
                        SET nome = ?, username = ?, email = ?, telefone = ?, endereco = ?, data_nascimento = ?, ativo = ?
                        WHERE id = ?
                    ''', (nome, username, email, telefone, endereco, data_nascimento, ativo, aluno_id))
                
                conn.commit()
                conn.close()
                flash("Aluno atualizado com sucesso!", "success")
                return redirect(url_for('admin_alunos'))
            except sql.IntegrityError:
                flash("Username já usado por outro usuário.", "error")
    
    conn.close()
    return render_template("admin/editar_aluno.html", aluno=aluno)

@app.route("/admin/alunos/deletar/<int:aluno_id>", methods=["POST"])
@login_required(['admin'])
def deletar_aluno(aluno_id):
    """Deletar aluno (apenas admin)"""
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id = ? AND tipo = 'aluno'", (aluno_id,))
    conn.commit()
    conn.close()
    flash("Aluno removido com sucesso!", "success")
    return redirect(url_for('admin_alunos'))

# Gerenciamento de Professores
@app.route("/admin/professores")
@login_required(['admin'])
def admin_professores():
    """Lista de professores (apenas admin)"""
    conn = get_db()
    professores = conn.execute('''
        SELECT * FROM users 
        WHERE tipo = 'professor' 
        ORDER BY nome
    ''').fetchall()
    conn.close()
    
    return render_template("admin/professores.html", professores=professores)

# Gerenciamento de Notícias
@app.route("/admin/noticias")
@login_required(['admin', 'professor'])
def admin_noticias():
    """Gerenciamento de notícias"""
    conn = get_db()
    noticias = conn.execute('''
        SELECT n.*, u.nome as autor_nome 
        FROM noticias n 
        LEFT JOIN users u ON n.autor_id = u.id 
        ORDER BY n.data_publicacao DESC
    ''').fetchall()
    conn.close()
    
    return render_template("admin/noticias_admin.html", noticias=noticias)

@app.route("/admin/noticias/cadastrar", methods=["GET", "POST"])
@login_required(['admin', 'professor'])
def cadastrar_noticia():
    """Cadastrar nova notícia"""
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        conteudo = request.form.get("conteudo", "").strip()
        destaque = request.form.get("destaque", "off") == "on"
        
        if not titulo or not conteudo:
            flash("Preencha todos os campos obrigatórios.", "error")
        else:
            conn = get_db()
            try:
                conn.execute('''
                    INSERT INTO noticias (titulo, conteudo, autor_id, destaque)
                    VALUES (?, ?, ?, ?)
                ''', (titulo, conteudo, session['user_id'], destaque))
                conn.commit()
                conn.close()
                flash("Notícia publicada com sucesso!", "success")
                return redirect(url_for('admin_noticias'))
            except Exception as e:
                flash(f"Erro ao publicar notícia: {str(e)}", "error")
                conn.close()
    
    return render_template("admin/cadastrar_noticia.html")

# API para estatísticas (opcional)
@app.route("/api/estatisticas")
@login_required(['admin', 'professor'])
def api_estatisticas():
    """API para obter estatísticas"""
    conn = get_db()
    
    total_alunos = conn.execute("SELECT COUNT(*) FROM users WHERE tipo = 'aluno' AND ativo = 1").fetchone()[0]
    total_professores = conn.execute("SELECT COUNT(*) FROM users WHERE tipo = 'professor' AND ativo = 1").fetchone()[0]
    total_disciplinas = conn.execute("SELECT COUNT(*) FROM disciplinas").fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'alunos': total_alunos,
        'professores': total_professores,
        'disciplinas': total_disciplinas
    })

# Handlers de erro
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500

if __name__ == "__main__":
    # Criar pasta de uploads se não existir
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    # Inicializar banco de dados
    db_manager.init_db()
    
    print("🚀 Servidor da Escola Colaço iniciando...")
    print("📧 Acesse: http://127.0.0.1:5000")
    print("👤 Admin: usuario 'admin', senha 'admin123'")
    print("🎓 Aluno: usuario 'ana2024', senha 'aluno123'")
    
    app.run(debug=True, host='0.0.0.0', port=5000)