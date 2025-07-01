import os
import traceback
from datetime import datetime

from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   session, url_for)
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///barbearia.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# MODELOS
class Barbeiro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    folga = db.Column(db.Boolean, default=False)

class Servico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)

class AgendamentoServico(db.Model):
    __tablename__ = 'agendamento_servico'
    agendamento_id = db.Column(db.Integer, db.ForeignKey('agendamento.id'), primary_key=True)
    servico_id = db.Column(db.Integer, db.ForeignKey('servico.id'), primary_key=True)

class Agendamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_cliente = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    barbeiro_id = db.Column(db.Integer, db.ForeignKey('barbeiro.id'), nullable=False)
    data = db.Column(db.String(10), nullable=False)
    horario = db.Column(db.String(5), nullable=False)
    atendido = db.Column(db.Boolean, default=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    servicos = db.relationship('Servico', secondary='agendamento_servico', backref='agendamentos')

class AgendaEspecial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10), unique=True, nullable=False)  # AAAA-MM-DD
    status = db.Column(db.String(10), nullable=False)  # "fechado" ou "aberto"

with app.app_context():
    db.create_all()

# PÁGINAS
@app.route("/")
def home():
    return render_template("home.html")

@app.route('/agendamento')
def index():
    return render_template('index.html')

@app.route('/admin_page')
def admin_page():
    return render_template('admin.html')

@app.route('/admin/gerenciar')
def gerenciar_barbeiros_servicos():
    return render_template('gerenciar.html')

# BARBEIROS
@app.route('/barbeiros', methods=['GET', 'POST'])
def barbeiros():
    if request.method == 'GET':
        barbeiros = Barbeiro.query.all()

        resultado = []
        for b in barbeiros:
            agendamentos = Agendamento.query.filter_by(barbeiro_id=b.id, atendido=True).all()
            total = 0
            for ag in agendamentos:
                total += sum(s.preco for s in ag.servicos)
            comissao = round(total * 0.03, 2)

            resultado.append({
                'id': b.id,
                'nome': b.nome,
                'folga': b.folga,
                'comissao': comissao
            })

        return jsonify({'barbeiros': resultado})

    if request.method == 'POST':
        dados = request.get_json()
        nome = dados.get('nome')
        if not nome:
            return jsonify({'erro': 'Nome é obrigatório'}), 400

        novo_barbeiro = Barbeiro(nome=nome)
        db.session.add(novo_barbeiro)
        db.session.commit()
        return jsonify({
            'mensagem': 'Barbeiro criado com sucesso',
            'id': novo_barbeiro.id,
            'nome': novo_barbeiro.nome,
            'folga': novo_barbeiro.folga
        })

# SERVIÇOS
@app.route('/servicos', methods=['GET', 'POST'])
def servicos():
    if request.method == 'GET':
        servicos = Servico.query.all()
        return jsonify({'servicos': [{'id': s.id, 'nome': s.nome, 'preco': s.preco} for s in servicos]})
    
    if request.method == 'POST':
        dados = request.get_json()
        nome = dados.get('nome')
        preco = dados.get('preco')
        if not nome or preco is None:
            return jsonify({'erro': 'Nome e preço são obrigatórios'}), 400
        
        novo_servico = Servico(nome=nome, preco=preco)
        db.session.add(novo_servico)
        db.session.commit()
        return jsonify({'mensagem': 'Serviço criado com sucesso', 'id': novo_servico.id})
    
@app.route('/servicos/<int:id>', methods=['PUT'])
def atualizar_servico(id):
    dados = request.get_json()
    servico = Servico.query.get(id)
    if not servico:
        return jsonify({'erro': 'Serviço não encontrado'}), 404
    nome = dados.get('nome')
    preco = dados.get('preco')
    if nome:
        servico.nome = nome
    if preco is not None:
        try:
            servico.preco = float(preco)
        except ValueError:
            return jsonify({'erro': 'Preço inválido'}), 400
    db.session.commit()
    return jsonify({'mensagem': 'Serviço atualizado com sucesso'})

# Deletar serviço
@app.route('/servicos/<int:id>', methods=['DELETE'])
def deletar_servico(id):
    servico = Servico.query.get(id)
    if not servico:
        return jsonify({'erro': 'Serviço não encontrado'}), 404
    db.session.delete(servico)
    db.session.commit()
    return jsonify({'mensagem': 'Serviço deletado com sucesso'})

# AGENDAR
@app.route('/agendar', methods=['POST'])
def agendar():
    data = request.get_json()
    nome = data.get('nome_cliente')
    telefone = data.get('telefone')
    barbeiro_id = data.get('barbeiro_id')
    data_agendamento = data.get('data')
    horario = data.get('horario')
    servicos_ids = data.get('servicos')

    if not nome or not telefone or not barbeiro_id or not data_agendamento or not horario or not servicos_ids:
        return jsonify({'erro': 'Dados incompletos'}), 400

    agendamento = Agendamento(
        nome_cliente=nome,
        telefone=telefone,
        barbeiro_id=barbeiro_id,
        data=data_agendamento,
        horario=horario
    )
    for sid in servicos_ids:
        servico = Servico.query.get(sid)
        if servico:
            agendamento.servicos.append(servico)

    db.session.add(agendamento)
    db.session.commit()
    return jsonify({'mensagem': 'Agendamento realizado com sucesso'})

# VERIFICAR HORÁRIOS DISPONÍVEIS
@app.route('/verificar', methods=['POST'])
def verificar_horarios():
    try:
        data = request.get_json()
        barbeiro_id = data.get('barbeiro_id')
        data_agendamento = data.get('data')
        servico_ids = data.get('servicos', [])

        if not barbeiro_id or not data_agendamento or not servico_ids:
            return jsonify({'erro': 'Dados incompletos'}), 400

        try:
            dia_semana = datetime.strptime(data_agendamento, "%Y-%m-%d").weekday()
        except ValueError:
            return jsonify({'erro': 'Formato de data inválido. Use AAAA-MM-DD'}), 400

        # Verifica se existe entrada de agenda especial para a data
        especial = AgendaEspecial.query.filter_by(data=data_agendamento).first()
        if especial:
            if especial.status == "fechado":
                return jsonify({'horarios': []})
            elif especial.status == "aberto":
                hora_inicio, hora_fim = 10, 18
        else:
            if dia_semana in [0, 1]:  # Segunda ou terça - fechado
                return jsonify({'horarios': []})
            elif dia_semana in [5, 6]:  # Sábado ou domingo
                hora_inicio, hora_fim = 10, 22
            else:  # Quarta a sexta
                hora_inicio, hora_fim = 9, 19

        # Gera os horários disponíveis em intervalos de 30 minutos
        horarios_possiveis = [
            f"{hora:02d}:{minuto:02d}"
            for hora in range(hora_inicio, hora_fim)
            for minuto in [0, 30]
        ]
        horarios_possiveis.append(f"{hora_fim:02d}:00")

        # Busca agendamentos já feitos para esse barbeiro e data
        agendados = Agendamento.query.filter_by(
            barbeiro_id=barbeiro_id,
            data=data_agendamento
        ).all()

        ocupados = [a.horario for a in agendados]
        disponiveis = [h for h in horarios_possiveis if h not in ocupados]

        return jsonify({'horarios': disponiveis})

    except Exception as e:
        print("Erro ao verificar horários:", str(e))
        traceback.print_exc()
        return jsonify({'erro': 'Erro interno no servidor'}), 500
    
    # agenda especial para feriados, abertura ou fechamento de agenda
@app.route('/agenda_especial', methods=['GET'])
def listar_agenda_especial():
    datas = AgendaEspecial.query.all()
    return jsonify({'datas': [{'id': d.id, 'data': d.data, 'status': d.status} for d in datas]})

@app.route('/agenda_especial', methods=['POST'])
def adicionar_agenda_especial():
    dados = request.get_json()
    data = dados.get('data')
    status = dados.get('status')

    if not data or status not in ['aberto', 'fechado']:
        return jsonify({'erro': 'Dados inválidos'}), 400

    existente = AgendaEspecial.query.filter_by(data=data).first()
    if existente:
        existente.status = status  # Atualiza status se já existir
    else:
        nova = AgendaEspecial(data=data, status=status)
        db.session.add(nova)

    db.session.commit()
    return jsonify({'mensagem': 'Agenda especial salva com sucesso'})

@app.route('/agenda_especial/<int:id>', methods=['DELETE'])
def deletar_agenda_especial(id):
    entrada = AgendaEspecial.query.get(id)
    if not entrada:
        return jsonify({'erro': 'Registro não encontrado'}), 404
    db.session.delete(entrada)
    db.session.commit()
    return jsonify({'mensagem': 'Removido com sucesso'})

@app.route("/admin/agendamentos")
def listar_todos_agendamentos():
    agendamentos = Agendamento.query.order_by(Agendamento.data.desc(), Agendamento.horario.desc()).all()
    resultado = []
    for ag in agendamentos:
        barbeiro = Barbeiro.query.get(ag.barbeiro_id)
        resultado.append({
            "id": ag.id,
            "nome_cliente": ag.nome_cliente,
            "telefone": ag.telefone,
            "barbeiro_id": ag.barbeiro_id,
            "barbeiro_nome": barbeiro.nome if barbeiro else "Barbeiro excluído",
            "servicos": [{"id": s.id, "nome": s.nome} for s in ag.servicos],
            "data": ag.data,
            "horario": ag.horario,
            "atendido": ag.atendido,
        })
    return jsonify(resultado)

@app.route("/admin/editar/<int:id>", methods=["PUT"])
def editar_agendamento(id):
    ag = Agendamento.query.get_or_404(id)
    dados = request.get_json()

    campo = dados.get("campo")
    valor = dados.get("valor")

    try:
        if campo == "barbeiro_id":
            ag.barbeiro_id = int(valor)
        elif campo == "servicos":
            # valor esperado: lista de ids (string no fetch virá JSON.parse)
            ag.servicos.clear()
            for sid in valor:
                servico = Servico.query.get(int(sid))
                if servico:
                    ag.servicos.append(servico)
        elif campo == "data":
            ag.data = valor
        elif campo == "horario":
            ag.horario = valor
        elif campo == "atendido":
             ag.atendido = bool(valor)
        else:
            return jsonify({"erro": "Campo inválido"}), 400


        db.session.commit()
        return jsonify({"mensagem": "Agendamento atualizado com sucesso"})
    except Exception as e:
        print(e)
        return jsonify({"erro": "Erro ao atualizar"}), 500

@app.route("/cliente/agendamentos/<int:id>", methods=["DELETE"])
def cancelar_agendamento(id):
    ag = Agendamento.query.get_or_404(id)
    db.session.delete(ag)
    db.session.commit()
    return jsonify({"mensagem": "Agendamento cancelado com sucesso"})

@app.route('/barbeiros/<int:id>', methods=['PUT'])
def atualizar_barbeiro(id):
    dados = request.get_json()
    barbeiro = Barbeiro.query.get(id)
    if not barbeiro:
        return jsonify({'erro': 'Barbeiro não encontrado'}), 404
    nome = dados.get('nome')
    if not nome:
        return jsonify({'erro': 'Nome é obrigatório'}), 400
    barbeiro.nome = nome
    db.session.commit()
    return jsonify({'mensagem': 'Barbeiro atualizado com sucesso'})

# Deletar barbeiro
@app.route('/barbeiros/<int:id>', methods=['DELETE'])
def deletar_barbeiro(id):
    barbeiro = Barbeiro.query.get(id)
    if not barbeiro:
        return jsonify({'erro': 'Barbeiro não encontrado'}), 404
    db.session.delete(barbeiro)
    db.session.commit()
    return jsonify({'mensagem': 'Barbeiro deletado com sucesso'})
    
@app.route('/barbeiros/<int:id>/folga', methods=['PUT'])
def marcar_folga(id):
    dados = request.get_json()
    barbeiro = Barbeiro.query.get(id)
    if not barbeiro:
        return jsonify({'erro': 'Barbeiro não encontrado'}), 404

    barbeiro.folga = dados.get('folga', False)
    db.session.commit()
    return jsonify({'mensagem': 'Folga atualizada com sucesso'})

if __name__ == '__main__':
    app.run(debug=True)
