from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(150), nullable=False)
    endereco = db.Column(db.String(200))
    telefone = db.Column(db.String(20))
    senha_hash = db.Column(db.String(128))
    email = db.Column(db.String(120), unique=True, nullable=False)
    # Aqui você pode adicionar campo para login via Google, se quiser

class Barbeiro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)

class Servico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)

class Agendamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # pode ser agendamento avulso
    barbeiro_id = db.Column(db.Integer, db.ForeignKey('barbeiro.id'), nullable=False)
    servicos = db.Column(db.String(300), nullable=False)  # lista de serviços separados por vírgula, por simplicidade
    data = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)
    atendido = db.Column(db.Boolean, default=False)

    user = db.relationship('User')
    barbeiro = db.relationship('Barbeiro')

class AgendaEspecial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10), unique=True, nullable=False)  # formato: AAAA-MM-DD
    status = db.Column(db.String(10), nullable=False)  # "aberto" ou "fechado"

class FolgaBarbeiro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barbeiro_id = db.Column(db.Integer, db.ForeignKey('barbeiro.id'))
    data = db.Column(db.Date)

    barbeiro = db.relationship('Barbeiro', backref='folgas')

